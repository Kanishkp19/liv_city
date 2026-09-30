"""0003_mind: memory_notes, playbooks, skills, autopsies, market_items

Revision ID: 0003_mind
Revises: 0002_verify
Create Date: 2026-09-30
"""

from __future__ import annotations

from alembic import op

revision: str = "0003_mind"
down_revision: str | None = "0002_verify"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    import agentville.db.models  # noqa: F401
    from agentville.db.base import Base

    target = {"memory_notes", "playbooks", "skills", "autopsies", "market_items"}
    for name, table in Base.metadata.tables.items():
        if name in target:
            table.create(bind=op.get_bind())


def downgrade() -> None:
    for name in ("market_items", "autopsies", "skills", "playbooks", "memory_notes"):
        op.execute(f'DROP TABLE IF EXISTS "{name}"')
