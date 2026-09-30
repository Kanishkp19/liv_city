"""0006_triggers: append-only, payment gate, export gate (BACKEND_SCHEMA S2)

Revision ID: 0006_triggers
Revises: 0005_lifecycle
Create Date: 2026-09-30
"""

from __future__ import annotations

from alembic import op

from agentville.db.triggers import TRIGGER_SQL

revision: str = "0006_triggers"
down_revision: str | None = "0005_lifecycle"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    bind = op.get_bind()
    for stmt in TRIGGER_SQL:
        bind.exec_driver_sql(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    for name in (
        "export_requires_approval", "payment_requires_verification",
        "events_no_delete", "events_no_update", "ledger_no_delete", "ledger_no_update",
    ):
        bind.exec_driver_sql(f"DROP TRIGGER IF EXISTS {name}")
