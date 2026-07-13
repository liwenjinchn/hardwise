#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

NETLIST="tests/fixtures/allegro/mixed_controller_power_stage.net"
BOM="tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"
DOC_INDEX="data/document_indexes/mixed_controller_power_stage_docs.csv"

port_is_available() {
  ! lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

if [[ -n "${HARDWISE_PORT:-}" ]]; then
  if [[ ! "$HARDWISE_PORT" =~ ^[0-9]+$ ]] || (( HARDWISE_PORT < 1 || HARDWISE_PORT > 65535 )); then
    echo "HARDWISE_PORT must be an integer between 1 and 65535 (received: $HARDWISE_PORT)."
    read -r -p "Press Enter to close..."
    exit 1
  fi
  PORT="$HARDWISE_PORT"
  if ! port_is_available "$PORT"; then
    echo "HARDWISE_PORT=$PORT is already in use. Stop that service or choose another port."
    read -r -p "Press Enter to close..."
    exit 1
  fi
else
  PORT=8765
  while ! port_is_available "$PORT"; do
    PORT=$((PORT + 1))
    if (( PORT > 8785 )); then
      echo "Hardwise could not find a free port in 8765-8785. Set HARDWISE_PORT to another free port."
      read -r -p "Press Enter to close..."
      exit 1
    fi
  done
  if (( PORT != 8765 )); then
    echo "Port 8765 is already in use; using port $PORT instead."
  fi
fi

URL="http://127.0.0.1:$PORT/"

if ! command -v uv >/dev/null 2>&1; then
  echo "Hardwise needs uv on PATH. Install it from https://docs.astral.sh/uv/"
  read -r -p "Press Enter to close..."
  exit 1
fi

echo "Preparing Hardwise dependencies..."
uv sync

echo "The browser will open when Hardwise is ready at $URL"
(
  for ((attempt = 0; attempt < 120; attempt++)); do
    if curl --fail --silent --show-error "$URL" >/dev/null 2>&1; then
      open "$URL" >/dev/null 2>&1
      exit 0
    fi
    sleep 0.25
  done
  echo "Hardwise did not become ready at $URL within 30 seconds." >&2
) &

echo "Starting Hardwise Workbench with the built-in demo project."
echo "Close this terminal window or press Ctrl+C to stop the server."
uv run hardwise serve-workbench "$NETLIST" "$BOM" --document-index "$DOC_INDEX" --port "$PORT"
