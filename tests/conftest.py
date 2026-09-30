"""Shared fixtures: in-memory SQLite with schema + BACKEND_SCHEMA triggers installed."""

from __future__ import annotations

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from agentville.db.session import make_engine


@pytest.fixture()
def engine() -> Engine:
    return make_engine("sqlite://", apply_triggers=True)


@pytest.fixture()
def session(engine: Engine) -> Session:
    sess = Session(engine)
    try:
        yield sess
    finally:
        sess.close()
