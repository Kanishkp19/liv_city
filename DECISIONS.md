# DECISIONS.md

Log of assumptions and deviations. Format: `D<n> | date | context | decision | reason`.

| ID | Context | Decision | Reason |
|---|---|---|---|
| D1 | Top-10 roles absent from blueprint excerpt | Use roster in AGENT_ROLES_AND_ECONOMY.md | Roles are data; easily swapped |
| D2 | DB choice | SQLite (WAL) for dev/experiments; Postgres via same SQLAlchemy models | Zero-setup, single-writer engine fits |
| D3 | Currency | Integer "coins" | Avoid float drift |
| D4 | Queue | In-process asyncio priority queue in v1 | Free-tier rates make throughput low; Redis later |
| D5 | Judge panel | 3 distinct models, median score | Reduce single-model bias |
| D6 | Docs live flat at repo root; agent references say `docs/...` | Keep files at root; MCP selection recorded in SKILLS.md §M + mcp_servers.json | Avoid churn; paths documented here |
| D7 | MCP servers chosen: context7, sqlite, memory, github | Excludes Playwright/git/filesystem/fetch (native tools cover them); docker entry reserved until Docker Desktop installed | Fill real gaps only; see SKILLS.md §M |
