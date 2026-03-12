"""
Claude-OS Async Agent Server
Telegram → FastAPI (Render) → Claude API → Notion + other tools → Telegram reply
"""

import os
import json
import httpx
import anthropic
from fastapi import FastAPI, Request, Response
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="Claude-OS Agent Server")

# --- Config ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Notion DB IDs (from Claude-OS build)
PROJECTS_DB_ID = "debc1e5a-cf00-4be1-81e5-ac92dd6b06ae"
TASKS_DB_ID = "a3bb6ec1-a44f-439b-8dc9-1cba05779a4d"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- System Prompt ---
SYSTEM_PROMPT = """You are Jarvis, Eitan's async AI OS partner. You run 24/7 on a server and respond to Eitan's messages via Telegram.

About Eitan:
- Based in NYC area, Eastern Time
- Has ADHD — prefers structured, concrete, actionable responses
- Works on: Earthbar (BI/data), CellarSnap/Clinq/Cluster (wine app), Habit Hero (gamified habit tracker), Jarvis-Beta (smart home)
- Stack: Python, SQL, JS/TS, React, FastAPI, Supabase, Vercel, Render, GitHub, Notion
- Notion is his task/project management system

Your job:
- Help Eitan capture tasks, check on projects, and manage his work from his phone
- Be concise — this is a mobile chat interface, not a desk session
- Use tools to take real actions in Notion when asked
- Today's date: {date}

When Eitan says things like "add a task", "remind me to", "log this", "what's on my plate" — use the available tools.
If NOTION_TOKEN is not configured, tell Eitan clearly so he can fix it."""


# --- Notion Tools ---
async def notion_create_task(name: str, priority: str = "P2", context: str = "To Do", notes: str = "") -> dict:
    """Create a task in the Notion Tasks DB."""
    if not NOTION_TOKEN:
        return {"error": "NOTION_TOKEN not set — ask Eitan to add it to Render env vars"}

    payload = {
        "parent": {"database_id": TASKS_DB_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": name}}]},
            "Status": {"select": {"name": "To Do"}},
            "Priority": {"select": {"name": priority}},
            "Context": {"select": {"name": context}},
        }
    }
    if notes:
        payload["properties"]["Notes"] = {"rich_text": [{"text": {"content": notes}}]}

    async with httpx.AsyncClient() as http:
        r = await http.post(
            "https://api.notion.com/v1/pages",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28"},
            json=payload,
            timeout=10
        )
    if r.status_code == 200:
        data = r.json()
        return {"success": True, "task_id": data["id"], "url": data.get("url", "")}
    return {"error": r.text}


async def notion_list_tasks(status_filter: Optional[str] = None, limit: int = 10) -> dict:
    """List tasks from the Notion Tasks DB."""
    if not NOTION_TOKEN:
        return {"error": "NOTION_TOKEN not set"}

    filter_body = {}
    if status_filter:
        filter_body = {"filter": {"property": "Status", "select": {"equals": status_filter}}}

    payload = {
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": limit,
        **filter_body
    }

    async with httpx.AsyncClient() as http:
        r = await http.post(
            f"https://api.notion.com/v1/databases/{TASKS_DB_ID}/query",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28"},
            json=payload,
            timeout=10
        )
    if r.status_code != 200:
        return {"error": r.text}

    results = r.json().get("results", [])
    tasks = []
    for page in results:
        props = page["properties"]
        name = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled")
        status = props.get("Status", {}).get("select", {})
        status = status.get("name", "?") if status else "?"
        priority = props.get("Priority", {}).get("select", {})
        priority = priority.get("name", "?") if priority else "?"
        tasks.append({"name": name, "status": status, "priority": priority, "id": page["id"]})

    return {"tasks": tasks, "count": len(tasks)}


async def notion_update_task_status(task_id: str, status: str) -> dict:
    """Update a task's status in Notion."""
    if not NOTION_TOKEN:
        return {"error": "NOTION_TOKEN not set"}

    valid_statuses = ["Backlog", "To Do", "In Progress", "Done", "Blocked", "Cancelled"]
    if status not in valid_statuses:
        return {"error": f"Invalid status. Use one of: {valid_statuses}"}

    async with httpx.AsyncClient() as http:
        r = await http.patch(
            f"https://api.notion.com/v1/pages/{task_id}",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28"},
            json={"properties": {"Status": {"select": {"name": status}}}},
            timeout=10
        )
    if r.status_code == 200:
        return {"success": True}
    return {"error": r.text}


async def notion_list_projects(status_filter: Optional[str] = None) -> dict:
    """List projects from the Notion Projects DB."""
    if not NOTION_TOKEN:
        return {"error": "NOTION_TOKEN not set"}

    filter_body = {}
    if status_filter:
        filter_body = {"filter": {"property": "Status", "select": {"equals": status_filter}}}

    payload = {
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": 20,
        **filter_body
    }

    async with httpx.AsyncClient() as http:
        r = await http.post(
            f"https://api.notion.com/v1/databases/{PROJECTS_DB_ID}/query",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28"},
            json=payload,
            timeout=10
        )
    if r.status_code != 200:
        return {"error": r.text}

    results = r.json().get("results", [])
    projects = []
    for page in results:
        props = page["properties"]
        name = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled")
        status = props.get("Status", {}).get("select", {})
        status = status.get("name", "?") if status else "?"
        priority = props.get("Priority", {}).get("select", {})
        priority = priority.get("name", "?") if priority else "?"
        next_action = props.get("Next Action", {}).get("rich_text", [{}])
        next_action = next_action[0].get("text", {}).get("content", "") if next_action else ""
        projects.append({"name": name, "status": status, "priority": priority, "next_action": next_action})

    return {"projects": projects, "count": len(projects)}


# --- Tool Definitions for Claude API ---
TOOLS = [
    {
        "name": "create_task",
        "description": "Create a new task in Eitan's Notion Tasks database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Task name"},
                "priority": {"type": "string", "enum": ["P1", "P2", "P3"], "description": "Priority level. Default P2."},
                "context": {"type": "string", "enum": ["Deep Work", "Quick Win", "Waiting", "Admin"], "description": "Task context type"},
                "notes": {"type": "string", "description": "Optional notes for the task"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "list_tasks",
        "description": "List tasks from Eitan's Notion Tasks database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status_filter": {"type": "string", "enum": ["Backlog", "To Do", "In Progress", "Done", "Blocked", "Cancelled"], "description": "Filter by status. Omit to show all active tasks."},
                "limit": {"type": "integer", "description": "Max tasks to return (default 10)"}
            }
        }
    },
    {
        "name": "update_task_status",
        "description": "Update the status of a task in Notion. Use after listing tasks to get the task ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Notion page ID of the task"},
                "status": {"type": "string", "enum": ["Backlog", "To Do", "In Progress", "Done", "Blocked", "Cancelled"]}
            },
            "required": ["task_id", "status"]
        }
    },
    {
        "name": "list_projects",
        "description": "List projects from Eitan's Notion Projects database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status_filter": {"type": "string", "enum": ["Concept", "Active", "Paused", "Done", "Abandoned"], "description": "Filter by project status. Omit for all."}
            }
        }
    }
]


# --- Tool Dispatcher ---
async def run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "create_task":
        result = await notion_create_task(**tool_input)
    elif tool_name == "list_tasks":
        result = await notion_list_tasks(**tool_input)
    elif tool_name == "update_task_status":
        result = await notion_update_task_status(**tool_input)
    elif tool_name == "list_projects":
        result = await notion_list_projects(**tool_input)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    return json.dumps(result)


# --- Telegram Helpers ---
async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as http:
        await http.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10
        )


async def send_typing(chat_id: int):
    async with httpx.AsyncClient() as http:
        await http.post(
            f"{TELEGRAM_API}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=5
        )


# --- Core Agent Loop ---
async def process_message(chat_id: int, user_message: str):
    await send_typing(chat_id)

    system = SYSTEM_PROMPT.format(date=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    messages = [{"role": "user", "content": user_message}]

    # Agentic loop — runs until Claude stops calling tools
    for _ in range(10):  # max 10 tool rounds
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            # Extract text and send
            text = next((b.text for b in response.content if hasattr(b, "text")), "Done.")
            await send_message(chat_id, text)
            return

        if response.stop_reason == "tool_use":
            # Add assistant turn
            messages.append({"role": "assistant", "content": response.content})

            # Process all tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        break

    await send_message(chat_id, "Something went wrong. Try again.")


# --- Routes ---
@app.get("/")
async def root():
    return {"status": "Claude-OS agent server running", "bot": "Bobanski_ClaudeMCP_Bot"}


@app.get("/health")
async def health():
    return {"ok": True, "notion_configured": bool(NOTION_TOKEN), "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    message = body.get("message") or body.get("edited_message")
    if not message:
        return Response(status_code=200)

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Log incoming chat ID (useful for first-time setup)
    print(f"[webhook] chat_id={chat_id} text={text!r}")

    # Security: only respond to allowed chat ID
    if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID:
        print(f"[webhook] Blocked unauthorized chat_id={chat_id}")
        return Response(status_code=200)

    # If ALLOWED_CHAT_ID not set, accept from anyone but log clearly
    if not ALLOWED_CHAT_ID:
        print(f"[webhook] WARNING: ALLOWED_CHAT_ID not set. Responding to chat_id={chat_id}")

    if text == "/start":
        await send_message(chat_id, f"Jarvis online. Your chat ID is `{chat_id}` — add this as `ALLOWED_CHAT_ID` in Render env vars to lock access. What do you need?")
        return Response(status_code=200)

    if not text:
        return Response(status_code=200)

    await process_message(chat_id, text)
    return Response(status_code=200)
