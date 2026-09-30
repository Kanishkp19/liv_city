"""EventLog: append-only hash-chained event source of truth (TRD S3.2, invariant I8)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentville.db.models import Event


def canonical_json(obj: Any) -> str:
    """Stable JSON: sorted keys, compact separators (TRD S5)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def event_hash(prev_hash: str, event_dict: dict[str, Any]) -> str:
    """hash = sha256(prev_hash || canonical_json(event fields))."""
    h = hashlib.sha256()
    h.update(prev_hash.encode("utf-8"))
    h.update(canonical_json(event_dict).encode("utf-8"))
    return h.hexdigest()


class EventLog:
    """Emits and verifies the per-world event chain."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def emit(
        self,
        world_id: str,
        *,
        tick: int,
        type_: str,
        agent_id: str | None,
        payload: dict[str, Any],
        cause_event_id: int | None = None,
    ) -> int:
        """Append one event, chaining from the current head; returns event id."""
        prev = self.head(world_id)
        seq = self._next_seq(world_id, tick)
        body = {
            "world_id": world_id,
            "tick": tick,
            "seq": seq,
            "type": type_,
            "agent_id": agent_id,
            "payload": payload,
            "cause_event_id": cause_event_id,
        }
        row = Event(
            world_id=world_id,
            tick=tick,
            seq=seq,
            type=type_,
            agent_id=agent_id,
            payload_json=canonical_json(payload),
            cause_event_id=cause_event_id,
            prev_hash=prev,
            hash=event_hash(prev, body),
        )
        self._s.add(row)
        self._s.flush()
        return int(row.id)

    def head(self, world_id: str) -> str:
        """Latest event hash for world ("" when none)."""
        row = self._s.execute(
            select(Event).where(Event.world_id == world_id).order_by(Event.id.desc()).limit(1)
        ).scalar_one_or_none()
        return row.hash if row else ""

    def rows(self, world_id: str) -> list[Event]:
        """All events for a world in id order."""
        return list(
            self._s.execute(select(Event).where(Event.world_id == world_id).order_by(Event.id)).scalars()
        )

    def verify_chain(self, world_id: str) -> bool:
        """True iff every event's stored hash matches recomputation from genesis."""
        prev = ""
        for row in self.rows(world_id):
            body = {
                "world_id": row.world_id,
                "tick": row.tick,
                "seq": row.seq,
                "type": row.type,
                "agent_id": row.agent_id,
                "payload": json.loads(row.payload_json),
                "cause_event_id": row.cause_event_id,
            }
            if row.prev_hash != prev or row.hash != event_hash(prev, body):
                return False
            prev = row.hash
        return True

    def _next_seq(self, world_id: str, tick: int) -> int:
        row = self._s.execute(
            select(Event.seq)
            .where(Event.world_id == world_id, Event.tick == tick)
            .order_by(Event.seq.desc())
            .limit(1)
        ).scalar_one_or_none()
        return 0 if row is None else row + 1
