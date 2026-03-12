# Claude OS Agent — Session Context

This repo is a personal AI toolbelt. It contains a FastAPI Telegram bot (Jarvis)
plus CLI tools that give Claude direct access to external services during sessions.

## Available Tools

### Notion (`notion_cli.py`)
Read and write Eitan's Notion workspace.
```bash
python notion_cli.py list-tasks [--status "In Progress"] [--limit 10]
python notion_cli.py create-task --name "..." [--priority P1|P2|P3] [--context "Deep Work|Quick Win|Waiting|Admin"] [--notes "..."]
python notion_cli.py update-task --id <page_id> --status "Done"
python notion_cli.py list-projects [--status "Active|Concept|Paused|Done|Abandoned"]
```
Requires: `NOTION_TOKEN` env var

### Google Sheets (`sheets_cli.py`)
Read and write Google Sheets for data collection and organization.
```bash
python sheets_cli.py list-sheets --id <spreadsheet_id>
python sheets_cli.py read --id <spreadsheet_id> --sheet <tab_name>
python sheets_cli.py append --id <spreadsheet_id> --sheet <tab_name> --rows '[["val1","val2"]]'
python sheets_cli.py clear --id <spreadsheet_id> --sheet <tab_name>
python sheets_cli.py create --title "New Sheet Title"
```
Requires: `GOOGLE_SERVICE_ACCOUNT_JSON` env var (full JSON contents of service account key)
Sheets must be shared with: `ector@helical-bonsai-456603-i1.iam.gserviceaccount.com`

### GitHub CLI (`gh`)
Installed via session-start hook. Auth is handled via the GitHub MCP built into
Claude Code on the web — no token setup needed.
```bash
gh issue list --repo Bobanski/<repo>
gh pr list --repo Bobanski/<repo>
gh issue view <number> --repo Bobanski/<repo>
```

## Session Start Hook
`.claude/hooks/session-start.sh` runs automatically on remote sessions and installs:
- Python dependencies from `requirements.txt` (fastapi, uvicorn, httpx, anthropic, gspread, google-auth)
- `ruff` (linter)
- `gh` CLI

## First Thing to Do in a New Session
1. Verify env vars are available:
```bash
echo "NOTION: ${NOTION_TOKEN:+set}" && echo "SHEETS: ${GOOGLE_SERVICE_ACCOUNT_JSON:+set}"
```
2. Test Sheets access with a known spreadsheet ID:
```bash
python sheets_cli.py list-sheets --id <spreadsheet_id>
```

## Eitan's Stack & Context
- Based in NYC, Eastern Time, has ADHD — prefers concrete and actionable
- Projects: Earthbar (BI/data), CellarSnap/Clinq/Cluster (wine app), Habit Hero, Jarvis-Beta
- Stack: Python, SQL, JS/TS, React, FastAPI, Supabase, Vercel, Render, GitHub, Notion
- Notion DBs: Tasks (`a3bb6ec1-a44f-439b-8dc9-1cba05779a4d`), Projects (`debc1e5a-cf00-4be1-81e5-ac92dd6b06ae`)

## Pending / Next Steps
- Validate Google Sheets connection in a fresh session (env vars now set in Claude.ai project)
- Define data collection workflow (research → Sheets → data model)
- Consider adding rclone for Google Drive file access if needed
