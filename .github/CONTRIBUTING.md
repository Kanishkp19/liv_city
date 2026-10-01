# Contributing to liv_city (AgentVille)

Thank you for contributing! To maintain production-grade quality, determinism, and clear engineering audit trails, follow this guide for every contribution.

---

## 1. Branch Strategy & Naming Conventions

Never commit directly to `main`. Every contribution should have a dedicated branch.

Format: `<type>/T<id>-<short-description>`

### Standard Prefixes
- `feat/T<id>-...`: New feature or roadmap subtask from `docs/TODO.md` (e.g. `feat/T6.26-inspector-timeline-tab`).
- `fix/T<id>-...`: Bug fix or test regression (e.g. `fix/T6.3-vite-proxy-ws`).
- `test/T<id>-...`: Adding property, golden, or integration test suites.
- `docs/T<id>-...`: Updating specifications or architecture diagrams.

### Fast Branch Creation
You can generate a branch automatically from any task in `docs/TODO.md`:
```bash
# Using make:
make branch TASK=6.26

# Or using the helper script:
./scripts/new_task_branch.sh 6.26
```

---

## 2. Commit Message Standards

Use Conventional Commits with task IDs:
```text
T<id>: <imperative summary>

- bullet point describing non-obvious decision
- reference to docs or invariant checked
```

Examples:
- `feat(control-room): add Inspector Timeline tab with raw JSON expansion (T6.26)`
- `fix(api): honor AV_WS_URL in Vite dev proxy configuration (T6.3-fix)`
- `test(engine): add double-entry ledger invariant conservation property test`

---

## 3. Definition of Done (DoD)

Before opening or merging a PR:
1. **Tests Pass**: `uv run pytest` (all 116+ unit, property, and golden tests green).
2. **Lint & Formatting**: `uv run ruff check src tests` (0 warnings).
3. **Type Checking**: `uv run mypy` (mypy strict clean).
4. **Frontend Builds**: `cd control-room && npm run build` (0 TypeScript / bundle errors).
5. **Fail-Closed Checked**: Invariants and error paths reject or no-op safely.
6. **Documentation**: Any new assumption is logged in `docs/DECISIONS.md`, and `docs/TODO.md` is updated.

---

## 4. Pull Request Workflow

1. Push your branch:
   ```bash
   git push -u origin feat/T6.26-inspector-timeline-tab
   ```
2. Open a Pull Request on GitHub against `main`.
3. Complete the PR template with verification command results.
4. Ensure the GitHub Actions CI workflow passes.
5. Merge using **Squash and merge** or **Rebase and merge**.
