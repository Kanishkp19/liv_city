"""0005_lifecycle: exams, exam_attempts, graduates, experiments, snapshots

Revision ID: 0005_lifecycle
Revises: 0004_gateway
Create Date: 2026-09-30
"""

from __future__ import annotations

from alembic import op

revision: str = "0005_lifecycle"
down_revision: str | None = "0004_gateway"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    import agentville.db.models  # noqa: F401
    from agentville.db.base import Base

    target = {"exams", "exam_attempts", "graduates", "experiments", "snapshots"}
    for name, table in Base.metadata.tables.items():
        if name in target:
            table.create(bind=op.get_bind())


def downgrade() -> None:
    for name in ("snapshots", "experiments", "graduates", "exam_attempts", "exams"):
        op.execute(f'DROP TABLE IF EXISTS "{name}"')
