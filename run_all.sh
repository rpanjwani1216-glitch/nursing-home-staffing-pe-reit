#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
STATA_CMD="${STATA_CMD:-stata-mp}"
LOG_DIR="$ROOT/outputs/generated/logs"
COMPLETE_MARKER="$ROOT/outputs/generated/.analysis_complete"

mkdir -p "$LOG_DIR"
cd "$ROOT"
rm -f "$COMPLETE_MARKER"

if ! command -v "$STATA_CMD" >/dev/null 2>&1 && [[ ! -x "$STATA_CMD" ]]; then
  echo "Stata executable not found: $STATA_CMD" >&2
  echo "Set STATA_CMD to your Stata executable and run again." >&2
  exit 127
fi

echo "Running analysis-only replication workflow"
echo "Repository: $ROOT"
echo "Stata:      $STATA_CMD"

"$STATA_CMD" -b do "$ROOT/stata/run_all_stata.do"

if [[ -f "$ROOT/run_all_stata.log" ]]; then
  mv "$ROOT/run_all_stata.log" "$LOG_DIR/run_all_stata.log"
fi

if [[ ! -f "$COMPLETE_MARKER" ]]; then
  echo "Analysis did not complete; inspect outputs/generated/logs/run_all_stata.log." >&2
  exit 1
fi

echo "Analysis complete. Generated results: outputs/generated/"
echo "Published reference results: outputs/reference/"
