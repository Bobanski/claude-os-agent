#!/usr/bin/env python3
"""
Google Sheets CLI — callable by Claude Code via Bash tool.

Usage:
  python sheets_cli.py read --id <spreadsheet_id> --sheet <sheet_name>
  python sheets_cli.py append --id <spreadsheet_id> --sheet <sheet_name> --rows '[["val1","val2"],...]'
  python sheets_cli.py clear --id <spreadsheet_id> --sheet <sheet_name>
  python sheets_cli.py create --title <title>
  python sheets_cli.py list-sheets --id <spreadsheet_id>

Auth (one of):
  - GOOGLE_SERVICE_ACCOUNT_JSON env var (JSON string of service account key)
  - GOOGLE_SERVICE_ACCOUNT_FILE env var (path to JSON key file)
"""

import os
import sys
import json
import argparse
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client():
    json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    file_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")

    if json_str:
        info = json.loads(json_str)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    elif file_path:
        creds = Credentials.from_service_account_file(file_path, scopes=SCOPES)
    else:
        print(json.dumps({"error": "Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE"}))
        sys.exit(1)

    return gspread.authorize(creds)


def read_sheet(spreadsheet_id, sheet_name):
    gc = get_client()
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(sheet_name)
    rows = ws.get_all_values()
    if not rows:
        return {"rows": [], "count": 0}
    headers = rows[0]
    data = [dict(zip(headers, row)) for row in rows[1:]]
    return {"headers": headers, "rows": data, "count": len(data)}


def append_rows(spreadsheet_id, sheet_name, rows):
    gc = get_client()
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(sheet_name)
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return {"success": True, "appended": len(rows)}


def clear_sheet(spreadsheet_id, sheet_name):
    gc = get_client()
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(sheet_name)
    ws.clear()
    return {"success": True}


def create_spreadsheet(title):
    gc = get_client()
    sh = gc.create(title)
    return {"success": True, "spreadsheet_id": sh.id, "url": sh.url}


def list_sheets(spreadsheet_id):
    gc = get_client()
    sh = gc.open_by_key(spreadsheet_id)
    sheets = [{"title": ws.title, "id": ws.id, "row_count": ws.row_count} for ws in sh.worksheets()]
    return {"sheets": sheets, "count": len(sheets)}


def main():
    parser = argparse.ArgumentParser(description="Google Sheets CLI for Claude Code sessions")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("read")
    p.add_argument("--id", required=True, help="Spreadsheet ID")
    p.add_argument("--sheet", required=True, help="Sheet/tab name")

    p = sub.add_parser("append")
    p.add_argument("--id", required=True)
    p.add_argument("--sheet", required=True)
    p.add_argument("--rows", required=True, help='JSON array of rows e.g. [["a","b"],["c","d"]]')

    p = sub.add_parser("clear")
    p.add_argument("--id", required=True)
    p.add_argument("--sheet", required=True)

    p = sub.add_parser("create")
    p.add_argument("--title", required=True)

    p = sub.add_parser("list-sheets")
    p.add_argument("--id", required=True)

    args = parser.parse_args()

    if args.command == "read":
        result = read_sheet(args.id, args.sheet)
    elif args.command == "append":
        rows = json.loads(args.rows)
        result = append_rows(args.id, args.sheet, rows)
    elif args.command == "clear":
        result = clear_sheet(args.id, args.sheet)
    elif args.command == "create":
        result = create_spreadsheet(args.title)
    elif args.command == "list-sheets":
        result = list_sheets(args.id)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
