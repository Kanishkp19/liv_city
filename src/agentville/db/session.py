"""DB engine/session plumbing (SQLite dev; Postgres profile in Phase 8)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from agentville.db.base import Base
from agentville.db.triggers import TRIGGER_SQL


def make_engine(db_url: str | None = None, *, apply_triggers: bool = True) -> Engine:
    """Create an engine, create schema, and install invariant triggers."""
    from agentville.config import load_settings

    url = db_url or load_settings().db_url
    if url.startswith("sqlite:///data") :
        Path("data").mkdir(exist_ok=True)
    eng = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    from sqlalchemy import event

    @event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn: object, _rec: object) -> None:
        import sqlite3

        if isinstance(dbapi_conn, sqlite3.Connection):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    Base.metadata.create_all(eng)
    if apply_triggers:
        with eng.begin() as conn:
            for stmt in TRIGGER_SQL:
                conn.exec_driver_sql(stmt)
    return eng


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Session factory bound to engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def transaction(engine: Engine) -> Iterator[Session]:
    """One atomic tick transaction; commit on success, rollback on exception."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
