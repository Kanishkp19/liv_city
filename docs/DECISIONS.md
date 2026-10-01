# DECISIONS.md

Log of assumptions and deviations. Format: `D<n> | date | context | decision | reason`.

| ID | Context | Decision | Reason |
|---|---|---|---|
| D1 | Top-10 roles absent from blueprint excerpt | Use roster in AGENT_ROLES_AND_ECONOMY.md | Roles are data; easily swapped |
| D2 | DB choice | SQLite (WAL) for dev/experiments; Postgres via same SQLAlchemy models | Zero-setup, single-writer engine fits |
| D3 | Currency | Integer "coins" | Avoid float drift |
| D4 | Queue | In-process asyncio priority queue in v1 | Free-tier rates make throughput low; Redis later |
| D5 | Judge panel | 3 distinct models, median score | Reduce single-model bias |
| D6 | Docs reorganized to docs/ folder | Move all project documentation files from root into `docs/` | Consolidate docs per project standard and user request |
| D7 | MCP servers chosen: context7, sqlite, memory, github | Excludes Playwright/git/filesystem/fetch (native tools cover them); docker entry reserved until Docker Desktop installed | Fill real gaps only; see SKILLS.md §M |
| D8 | TRD S5 id examples conflict: agent_0007 (4-digit) vs job_000123 (6-digit) | Standardize all IdGen kinds to 6-digit zero-pad | Uniform, supports 999,999 ids per kind; docs' examples inconsistent |
