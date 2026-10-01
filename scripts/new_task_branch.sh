#!/usr/bin/env bash
set -euo pipefail

# Helper to look up a task in docs/TODO.md and create a feature branch
if [ $# -lt 1 ]; then
  echo "Usage: $0 <task_id> (e.g. $0 6.26 or $0 T6.26)"
  exit 1
fi

RAW_TASK="$1"
TASK_NUM="${RAW_TASK#T}"
TASK_NUM="${TASK_NUM#t}"

TODO_FILE="docs/TODO.md"
if [ ! -f "$TODO_FILE" ]; then
  echo "Error: $TODO_FILE not found."
  exit 1
fi

LINE=$(grep -E "^- \[[ x]\] ${TASK_NUM} " "$TODO_FILE" | head -n 1 || true)

if [ -z "$LINE" ]; then
  echo "Error: Task $RAW_TASK not found in $TODO_FILE."
  echo "Available remaining tasks in Phase 6 & Phase 8:"
  grep -E "^- \[ \] (6\.|8\.)" "$TODO_FILE"
  exit 1
fi

# Clean description for branch name
# Example line: - [ ] 6.26 Inspector Timeline tab - Src: UIUX S4.2 - Verify: rows expand to raw JSON
TITLE=$(echo "$LINE" | sed -E "s/^- \[[ x]\] ${TASK_NUM} //" | cut -d'-' -f1 | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
BRANCH_NAME="feat/T${TASK_NUM}-${TITLE}"

echo "=========================================================="
echo "Task Found: $LINE"
echo "Target Branch: $BRANCH_NAME"
echo "=========================================================="

if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
  echo "Switching to existing branch $BRANCH_NAME..."
  git checkout "$BRANCH_NAME"
else
  echo "Creating and switching to new branch $BRANCH_NAME from main..."
  git checkout -b "$BRANCH_NAME" main
fi

echo ""
echo "Branch ready! When finished with implementation:"
echo "1. Run tests:  uv run pytest"
echo "2. Check lint: uv run ruff check src tests && uv run mypy"
echo "3. Commit:     git commit -m \"T${TASK_NUM}: <title>\""
echo "4. Push & PR:  git push -u origin $BRANCH_NAME"
