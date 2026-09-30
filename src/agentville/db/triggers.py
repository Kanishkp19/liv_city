"""SQLite trigger DDL from BACKEND_SCHEMA.md S2 (port to Postgres rules in Phase 8).

Statements are idempotent (IF NOT EXISTS) so both alembic 0006 and make_engine can apply them.
"""

TRIGGER_SQL: list[str] = [
    """
    CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger_entries
    BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger_entries
    BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
    BEGIN SELECT RAISE(ABORT, 'events are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
    BEGIN SELECT RAISE(ABORT, 'events are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS payment_requires_verification BEFORE INSERT ON ledger_entries
    WHEN NEW.reason = 'job_payment' AND NOT EXISTS (
      SELECT 1 FROM verifications v
      WHERE v.job_id = NEW.ref_id AND v.stage = 'programmatic' AND v.passed = 1)
    BEGIN SELECT RAISE(ABORT, 'payment without passing verification'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS export_requires_approval BEFORE UPDATE OF status ON graduates
    WHEN NEW.status = 'exported' AND (OLD.status != 'approved' OR NEW.reviewed_by IS NULL)
    BEGIN SELECT RAISE(ABORT, 'export requires approval'); END
    """,
]
