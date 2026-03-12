#!/bin/bash
set -euo pipefail

# Only run in remote/cloud sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "[session-start] Installing Python dependencies..."
pip install --quiet --break-system-packages -r "${CLAUDE_PROJECT_DIR}/requirements.txt"

echo "[session-start] Installing ruff (linter)..."
pip install --quiet --break-system-packages ruff

echo "[session-start] Installing GitHub CLI..."
if ! command -v gh &>/dev/null; then
  apt-get install -y -qq gh
else
  echo "[session-start] gh already installed, skipping."
fi

echo "[session-start] Dependencies installed successfully."
