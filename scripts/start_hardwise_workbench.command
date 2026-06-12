#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

URL="http://127.0.0.1:8765/"
NETLIST="tests/fixtures/allegro/mixed_controller_power_stage.net"
BOM="tests/fixtures/allegro/mixed_controller_power_stage_bom.csv"
DOC_INDEX="data/document_indexes/mixed_controller_power_stage_docs.csv"

if ! command -v uv >/dev/null 2>&1; then
  echo "Hardwise needs uv on PATH. Install it from https://docs.astral.sh/uv/"
  read -r -p "Press Enter to close..."
  exit 1
fi

echo "Preparing Hardwise dependencies..."
uv sync

echo "Opening $URL"
(sleep 2 && open "$URL") >/dev/null 2>&1 &

echo "Starting Hardwise Workbench with the built-in demo project."
echo "Close this terminal window or press Ctrl+C to stop the server."
uv run hardwise serve-workbench "$NETLIST" "$BOM" --document-index "$DOC_INDEX" --port 8765
