"""Double-entry integer-coin ledger (TRD S3.1, invariants I1/I2).

Only code holding a LedgerWriter instance may post entries; nothing is importable
as a global writer. Debit = money leaves; credit = money arrives.
"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from agentville.db.models import LedgerEntry


class LedgerError(Exception):
    """Raised for non-positive amounts and negative agent-account balances."""


AGENT_ACCOUNTS = "agent:"


class LedgerWriter:
    """Append-only double-entry postings scoped to one world."""

    def __init__(self, session: Session, *, world_id: str) -> None:
        self._s = session
        self._world = world_id

    def post(
        self,
        *,
        tick: int,
        debit: str,
        credit: str,
        amount: int,
        reason: str,
        ref_type: str | None = None,
        ref_id: str | None = None,
        event_id: int | None = None,
    ) -> int:
        """Post amount from debit to credit; raises LedgerError on bad amount or negative agent balance."""
        if amount <= 0:
            raise LedgerError(f"amount must be positive, got {amount}")
        if debit.startswith(AGENT_ACCOUNTS) and self.balance(debit) < amount:
            raise LedgerError(f"debit would make {debit} negative (balance {self.balance(debit)}, need {amount})")
        row = LedgerEntry(
            world_id=self._world,
            tick=tick,
            debit_account=debit,
            credit_account=credit,
            amount=amount,
            reason=reason,
            ref_type=ref_type,
            ref_id=ref_id,
            event_id=event_id,
        )
        self._s.add(row)
        self._s.flush()
        return int(row.id)

    def balance(self, account: str) -> int:
        """credits - debits for account."""
        res = self._s.execute(
            select(
                func.sum(
                    case((LedgerEntry.credit_account == account, LedgerEntry.amount), else_=0)
                    - case((LedgerEntry.debit_account == account, LedgerEntry.amount), else_=0)
                )
            ).where(LedgerEntry.world_id == self._world)
        ).scalar_one_or_none()
        return int(res or 0)

    def reconcile(self, world_id: str) -> None:
        """Structural check: no non-positive rows slipped in (conservation holds by construction)."""
        n_bad = self._s.execute(
            select(func.count())
            .select_from(LedgerEntry)
            .where(
                LedgerEntry.world_id == world_id,
                (LedgerEntry.amount <= 0),
            )
        ).scalar_one()
        if n_bad:
            msg = f"reconcile failed: {n_bad} non-positive rows"
            raise LedgerError(msg)

    def entries_for(self, account: str) -> list[LedgerEntry]:
        """All entries touching account, in id order."""
        return list(
            self._s.execute(
                select(LedgerEntry)
                .where(
                    LedgerEntry.world_id == self._world,
                    (LedgerEntry.debit_account == account) | (LedgerEntry.credit_account == account),
                )
                .order_by(LedgerEntry.id)
            ).scalars()
        )
