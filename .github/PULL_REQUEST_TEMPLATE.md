## Summary
<!-- Brief description of the feature or bug fix -->

Closes #<!-- Issue number if applicable -->
Task: `T<id>: <title>`

## Changes
- 

## Verification & Acceptance Criteria
<!-- Paste the verification command and results proving acceptance -->
- Command: `uv run pytest` / `cd control-room && npm run test && npm run build`
- Output:
```text
<!-- paste test output here -->
```

## Definition of Done Checklist
- [ ] Tests written from acceptance criteria before code and passing
- [ ] Lint check clean (`uv run ruff check src tests`)
- [ ] Static type check clean (`uv run mypy`)
- [ ] Frontend builds cleanly (`npm run build` in `control-room`)
- [ ] Fail-closed path verified (errors yield rejection or no-op)
- [ ] No undocumented assumptions (new decisions logged in `docs/DECISIONS.md`)
- [ ] [docs/TODO.md](docs/TODO.md) updated with commit reference
