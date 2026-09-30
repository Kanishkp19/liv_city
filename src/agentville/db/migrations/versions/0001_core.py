"""0001_core: worlds, agents, agent_vitals, ledger_entries, events, jobs, artifacts

Revision ID: 0001_core
Revises:
Create Date: 2026-09-30
"""

from __future__ import annotations

from alembic import op

revision: str = "0001_core"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    import agentville.db.models  # noqa: F401
    from agentville.db.base import Base

    target = {
        "worlds", "agents", "agent_vitals", "ledger_entries", "events", "jobs", "artifacts",
    }
    for name, table in Base.metadata.tables.items():
        if name in target:
            table.create(bind=op.get_bind())


def downgrade() -> None:
    for name in ("artifacts", "jobs", "events", "ledger_entries", "agent_vitals", "agents", "worlds"):
        op.execute(f'DROP TABLE IF EXISTS "{name}"')
