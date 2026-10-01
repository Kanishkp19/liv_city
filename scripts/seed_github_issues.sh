#!/usr/bin/env bash
set -euo pipefail

# Automated seeding of GitHub Issues for remaining roadmap tasks in docs/TODO.md

if ! command -v gh &> /dev/null; then
  echo "Error: GitHub CLI (gh) is not installed. Install via: brew install gh"
  exit 1
fi

if ! gh auth status &> /dev/null; then
  echo "GitHub CLI is not logged in."
  echo "Please authenticate first by running:"
  echo "    gh auth login"
  echo "Then re-run this script to automatically create the roadmap issues."
  exit 1
fi

REPO="Kanishkp19/liv_city"

echo "Creating roadmap issues on $REPO..."

tasks=(
  "T6.22|PixiJS tilemap districts rendering|Phase 6|Implement district visual tiles with district labels and active borders.|Src: docs/UIUX_BRIEF.md §4.1|cd control-room && npm run build"
  "T6.23|Agent sprites with dynamic vitals rings|Phase 6|Render agent avatars with color-coded energy, health, and strike rings.|Src: docs/UIUX_BRIEF.md §4.1|cd control-room && npm run build"
  "T6.24|Agent movement tween engine (>=50fps @100 agents)|Phase 6|Smooth coordinate interpolation between ticks with 50+ FPS performance target.|Src: docs/UIUX_BRIEF.md §9|cd control-room && npm run test"
  "T6.25|Death tombstone markers and notification toasts|Phase 6|Display tombstone sprite upon agent death and trigger toast notifications for major events.|Src: docs/UIUX_BRIEF.md §4.1|cd control-room && npm run build"
  "T6.26|Inspector Timeline tab with raw JSON expansion|Phase 6|Add agent inspector timeline showing chronological state transitions with expandable raw JSON events.|Src: docs/UIUX_BRIEF.md §4.2|cd control-room && npm run build"
  "T6.27|Inspector Decisions tab (Briefing + LLM reasoning + Verdict)|Phase 6|One-click inspection showing full briefing prompt, raw LLM reasoning, and verifier decision.|Src: docs/UIUX_BRIEF.md §4.2|cd control-room && npm run build"
  "T6.28|Inspector Work and Money tabs with ledger balance chart|Phase 6|Interactive time-series chart showing agent cumulative coin earnings, rent drains, and job payouts matching API.|Src: docs/UIUX_BRIEF.md §4.2|cd control-room && npm run build"
  "T6.29|Memory, Playbook diff, and Skills inspection tabs|Phase 6|Visual side-by-side diff viewer for playbook updates and executable skill scripts inspection.|Src: docs/UIUX_BRIEF.md §4.2|cd control-room && npm run build"
  "T6.30|Job Board, Verification Lab, and Economy analytics screens|Phase 6|Full screens for job pipeline status, verifier audit stats, and macro-economic charts.|Src: docs/UIUX_BRIEF.md §4.3-4.5|cd control-room && npm run build"
  "T6.31|Replay scrubber with branch comparison and ARIA accessibility|Phase 6|Time scrubber allowing stepping forward/backward through ticks, fork world from tick, and keyboard shortcuts.|Src: docs/UIUX_BRIEF.md §4.6, §9|cd control-room && npm run build"
  "T8.6|Docker Compose Postgres profile boot verification|Phase 8|Verify compose profile boots cleanly with Postgres 16, typed JSON columns, and triggers.|Src: docs/BACKEND_SCHEMA.md, docs/TRD.md|docker compose --profile postgres config"
  "T8.7|LLM cost accounting dashboard and multi-run comparison view|Phase 8|Dashboard visualizing token consumption by model/tier and split-view comparison across seeds.|Src: docs/CONFIG_REFERENCE.md, docs/UIUX_BRIEF.md|uv run pytest tests/unit/test_phase456.py"
)

for item in "${tasks[@]}"; do
  IFS="|" read -r tid title phase desc spec verify <<< "$item"
  issue_title="[Task]: $tid - $title"
  echo "Creating issue: $issue_title"
  
  body=$(cat <<EOF
### Phase
$phase

### Task ID
$tid

### Specification & Source Docs
$spec

### Scope & Description
$desc

### Verification Command
\`\`\`bash
$verify
\`\`\`

### Definition of Done Checklist
- [ ] Tests written from acceptance criteria before code and passing
- [ ] Typechecks and linting clean (\`ruff\`, \`mypy --strict\`, or \`tsc\`)
- [ ] Fail-closed path tested
- [ ] Updated \`docs/TODO.md\` with commit hash
EOF
)

  gh issue create \
    --repo "$REPO" \
    --title "$issue_title" \
    --body "$body" \
    --label "enhancement,roadmap" || true
done

echo "Done! All roadmap issues created on $REPO."
