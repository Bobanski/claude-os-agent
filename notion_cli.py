#!/usr/bin/env python3
"""
Notion CLI — callable by Claude Code via Bash tool.

Usage:
  python notion_cli.py list-tasks [--status <status>] [--limit <n>]
  python notion_cli.py create-task --name <name> [--priority P1|P2|P3] [--context <ctx>] [--notes <notes>]
  python notion_cli.py update-task --id <task_id> --status <status>
  python notion_cli.py list-projects [--status <status>]

Requires: NOTION_TOKEN env var
"""

import os
import sys
import json
import argparse
import httpx

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_VERSION = "2022-06-28"
PROJECTS_DB_ID = "debc1e5a-cf00-4be1-81e5-ac92dd6b06ae"
TASKS_DB_ID = "a3bb6ec1-a44f-439b-8dc9-1cba05779a4d"


def headers():
    if not NOTION_TOKEN:
        print(json.dumps({"error": "NOTION_TOKEN env var is not set"}))
        sys.exit(1)
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }


def list_tasks(status_filter=None, limit=10):
    payload = {
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": limit,
    }
    if status_filter:
        payload["filter"] = {"property": "Status", "select": {"equals": status_filter}}

    r = httpx.post(
        f"https://api.notion.com/v1/databases/{TASKS_DB_ID}/query",
        headers=headers(),
        json=payload,
        timeout=10,
    )
    if r.status_code != 200:
        return {"error": r.text}

    tasks = []
    for page in r.json().get("results", []):
        props = page["properties"]
        name = (props.get("Name", {}).get("title") or [{}])[0].get("text", {}).get("content", "Untitled")
        status = (props.get("Status", {}).get("select") or {}).get("name", "?")
        priority = (props.get("Priority", {}).get("select") or {}).get("name", "?")
        tasks.append({"id": page["id"], "name": name, "status": status, "priority": priority})
    return {"tasks": tasks, "count": len(tasks)}


def create_task(name, priority="P2", context="To Do", notes=""):
    payload = {
        "parent": {"database_id": TASKS_DB_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": name}}]},
            "Status": {"select": {"name": "To Do"}},
            "Priority": {"select": {"name": priority}},
            "Context": {"select": {"name": context}},
        },
    }
    if notes:
        payload["properties"]["Notes"] = {"rich_text": [{"text": {"content": notes}}]}

    r = httpx.post(
        "https://api.notion.com/v1/pages",
        headers=headers(),
        json=payload,
        timeout=10,
    )
    if r.status_code == 200:
        data = r.json()
        return {"success": True, "task_id": data["id"], "url": data.get("url", "")}
    return {"error": r.text}


def update_task(task_id, status):
    valid = ["Backlog", "To Do", "In Progress", "Done", "Blocked", "Cancelled"]
    if status not in valid:
        return {"error": f"Invalid status. Use one of: {valid}"}

    r = httpx.patch(
        f"https://api.notion.com/v1/pages/{task_id}",
        headers=headers(),
        json={"properties": {"Status": {"select": {"name": status}}}},
        timeout=10,
    )
    if r.status_code == 200:
        return {"success": True}
    return {"error": r.text}


def list_projects(status_filter=None):
    payload = {
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": 20,
    }
    if status_filter:
        payload["filter"] = {"property": "Status", "select": {"equals": status_filter}}

    r = httpx.post(
        f"https://api.notion.com/v1/databases/{PROJECTS_DB_ID}/query",
        headers=headers(),
        json=payload,
        timeout=10,
    )
    if r.status_code != 200:
        return {"error": r.text}

    projects = []
    for page in r.json().get("results", []):
        props = page["properties"]
        name = (props.get("Name", {}).get("title") or [{}])[0].get("text", {}).get("content", "Untitled")
        status = (props.get("Status", {}).get("select") or {}).get("name", "?")
        priority = (props.get("Priority", {}).get("select") or {}).get("name", "?")
        next_action_list = props.get("Next Action", {}).get("rich_text") or []
        next_action = next_action_list[0].get("text", {}).get("content", "") if next_action_list else ""
        projects.append({"id": page["id"], "name": name, "status": status, "priority": priority, "next_action": next_action})
    return {"projects": projects, "count": len(projects)}


def main():
    parser = argparse.ArgumentParser(description="Notion CLI for Claude Code sessions")
    sub = parser.add_subparsers(dest="command", required=True)

    # list-tasks
    p = sub.add_parser("list-tasks")
    p.add_argument("--status", choices=["Backlog", "To Do", "In Progress", "Done", "Blocked", "Cancelled"])
    p.add_argument("--limit", type=int, default=10)

    # create-task
    p = sub.add_parser("create-task")
    p.add_argument("--name", required=True)
    p.add_argument("--priority", choices=["P1", "P2", "P3"], default="P2")
    p.add_argument("--context", choices=["Deep Work", "Quick Win", "Waiting", "Admin"], default="To Do")
    p.add_argument("--notes", default="")

    # update-task
    p = sub.add_parser("update-task")
    p.add_argument("--id", required=True)
    p.add_argument("--status", required=True)

    # list-projects
    p = sub.add_parser("list-projects")
    p.add_argument("--status", choices=["Concept", "Active", "Paused", "Done", "Abandoned"])

    args = parser.parse_args()

    if args.command == "list-tasks":
        result = list_tasks(status_filter=args.status, limit=args.limit)
    elif args.command == "create-task":
        result = create_task(name=args.name, priority=args.priority, context=args.context, notes=args.notes)
    elif args.command == "update-task":
        result = update_task(task_id=args.id, status=args.status)
    elif args.command == "list-projects":
        result = list_projects(status_filter=args.status)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
