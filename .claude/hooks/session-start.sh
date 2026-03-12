#!/bin/bash
set -euo pipefail

# Only run in remote/cloud sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "[session-start] Installing Python dependencies..."
pip install --quiet -r "${CLAUDE_PROJECT_DIR}/requirements.txt"

echo "[session-start] Installing ruff (linter)..."
pip install --quiet ruff

echo "[session-start] Dependencies installed successfully."
