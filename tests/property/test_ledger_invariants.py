"""T0.7: Ledger invariants I1/I2 (property + 10k ops), LedgerWriter capability."""

from __future__ import annotations

import pytest

from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agentville.db.models import LedgerEntry, World
from agentville.engine.ledger import LedgerError, LedgerWriter

pytestmark = pytest.mark.phase0


def _world(s: Session) -> None:
    s.add(World(id="w1", name="t", seed=1, preset="p", config_json="{}", created_at="2026"))
    s.flush()


def test_post_and_balance(session: Session) -> None:
    _world(session)
    led = LedgerWriter(session, world_id="w1")
    led.post(tick=0, debit="treasury_mint", credit="treasury", amount=10_000, reason="seed")
    led.post(tick=0, debit="treasury", credit="agent:agent_000001", amount=500, reason="starting_funds")
    assert led.balance("treasury") == 9_500
    assert led.balance("agent:agent_000001") == 500
    led.reconcile("w1")


def test_rejects_nonpositive_amount(session: Session) -> None:
    _world(session)
    led = LedgerWriter(session, world_id="w1")
    import pytest

    with pytest.raises(LedgerError, match="positive"):
        led.post(tick=1, debit="treasury", credit="agent:a", amount=0, reason="x")


def test_rejects_negative_agent_balance(session: Session) -> None:
    _world(session)
    led = LedgerWriter(session, world_id="w1")
    led.post(tick=1, debit="treasury_mint", credit="agent:a1", amount=100, reason="seed")
    import pytest

    with pytest.raises(LedgerError, match="negative"):
        led.post(tick=1, debit="agent:a1", credit="landlord", amount=101, reason="rent")


def test_non_agent_accounts_may_go_negative(session: Session) -> None:
    """Buyers/landlord etc. can be drawn down; engine tops them up by rule."""
    _world(session)
    led = LedgerWriter(session, world_id="w1")
    led.post(tick=1, debit="treasury_mint", credit="landlord", amount=10, reason="seed")
    led.post(tick=1, debit="landlord", credit="agent:a1", amount=25, reason="rent")
    assert led.balance("landlord") == -15


def test_double_entry_conservation(session: Session) -> None:
    _world(session)
    led = LedgerWriter(session, world_id="w1")
    led.post(tick=0, debit="treasury_mint", credit="treasury", amount=1_000, reason="seed")
    led.post(tick=1, debit="treasury", credit="agent:a1", amount=300, reason="funds")
    led.post(tick=1, debit="agent:a1", credit="landlord", amount=120, reason="rent")
    total = sum(led.balance(a) for a in ("treasury", "agent:a1", "landlord"))
    assert total == 1_000  # constant except mint
    led.reconcile("w1")


@given(
    ops=st.lists(
        st.tuples(st.sampled_from(["agent:a1", "agent:a2", "landlord"]), st.integers(min_value=1, max_value=50)),
        min_size=1,
        max_size=40,
    ),
    seed_amount=st.integers(min_value=200, max_value=5_000),
)
def test_property_no_negative_agent_balances(ops: list[tuple[str, int]], seed_amount: int) -> None:
    """Fresh engine per hypothesis example (no shared fixture state)."""
    from sqlalchemy.orm import Session as SasSession

    from agentville.db.session import make_engine

    eng = make_engine("sqlite://", apply_triggers=False)
    with SasSession(eng) as session:
        _world(session)
        led = LedgerWriter(session, world_id="w1")
        led.post(tick=0, debit="treasury_mint", credit="treasury", amount=seed_amount, reason="seed")
        led.post(tick=0, debit="treasury", credit="agent:a1", amount=seed_amount // 2, reason="funds")
        led.post(tick=0, debit="treasury", credit="agent:a2", amount=seed_amount // 2, reason="funds")
        for account, amount in ops:
            if account.startswith("agent"):
                if led.balance(account) >= amount:
                    led.post(tick=1, debit=account, credit="landlord", amount=amount, reason="cost")
            else:
                led.post(tick=1, debit="treasury", credit=account, amount=amount, reason="topup")
        assert led.balance("agent:a1") >= 0
        assert led.balance("agent:a2") >= 0
        total = sum(led.balance(a) for a in ("treasury", "agent:a1", "agent:a2", "landlord"))
        assert total == seed_amount
        led.reconcile("w1")


def test_ten_thousand_ops_conservation(session: Session) -> None:
    """I1 stress: 10k mixed ops stay conserved and reconcile."""
    _world(session)
    led = LedgerWriter(session, world_id="w1")
    supply = 1_000_000
    led.post(tick=0, debit="treasury_mint", credit="treasury", amount=supply, reason="seed")
    from agentville.rng import derive_rng

    rng = derive_rng(11, 0, "ledger-test")
    accounts = ["agent:a1", "agent:a2", "landlord", "market", "buyer:b1"]
    for _ in range(10_000):
        debit, credit = rng.choice(accounts), rng.choice(accounts)
        if debit == credit:
            continue
        amount = rng.randint(1, 30)
        if debit.startswith("agent") and led.balance(debit) < amount:
            continue
        led.post(tick=1, debit=debit, credit=credit, amount=amount, reason="sim")
    total = sum(led.balance(a) for a in accounts) + led.balance("treasury")
    assert total == supply
    led.reconcile("w1")
    n = session.scalar(select(func.count()).select_from(LedgerEntry))
    # ~20% of random pairs are debit==credit and skipped; 10k draws yield ~8k postings
    assert n is not None and n > 5_000
