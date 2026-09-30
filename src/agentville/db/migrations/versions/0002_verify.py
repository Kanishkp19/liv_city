"""0002_verify: companies, buyers, verifications, judge_votes, sandbox_runs

Revision ID: 0002_verify
Revises: 0001_core
Create Date: 2026-09-30
"""

from __future__ import annotations

from alembic import op

revision: str = "0002_verify"
down_revision: str | None = "0001_core"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    import agentville.db.models  # noqa: F401
    from agentville.db.base import Base

    target = {"companies", "buyers", "verifications", "judge_votes", "sandbox_runs"}
    for name, table in Base.metadata.tables.items():
        if name in target:
            table.create(bind=op.get_bind())


def downgrade() -> None:
    for name in ("sandbox_runs", "judge_votes", "verifications", "buyers", "companies"):
        op.execute(f'DROP TABLE IF EXISTS "{name}"')
