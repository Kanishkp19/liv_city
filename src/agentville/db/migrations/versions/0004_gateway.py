"""0004_gateway: llm_calls, web_fetches, provider_health, actions, system_events

Revision ID: 0004_gateway
Revises: 0003_mind
Create Date: 2026-09-30
"""

from __future__ import annotations

from alembic import op

revision: str = "0004_gateway"
down_revision: str | None = "0003_mind"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    import agentville.db.models  # noqa: F401
    from agentville.db.base import Base

    target = {"llm_calls", "web_fetches", "provider_health", "actions", "system_events"}
    for name, table in Base.metadata.tables.items():
        if name in target:
            table.create(bind=op.get_bind())


def downgrade() -> None:
    for name in ("actions", "provider_health", "web_fetches", "llm_calls", "system_events"):
        op.execute(f'DROP TABLE IF EXISTS "{name}"')
