"""Market: companies, buyers, funding from treasury, top-up rule (T1.2, TRD S7)."""

from __future__ import annotations

from typing import Any

from agentville.engine.events import EventLog
from agentville.engine.ledger import LedgerWriter
from agentville.engine.world import World


def _persist_buyers(session: Any, world: World, buyer_specs: list[tuple[str, str]]) -> None:
    """Insert companies/buyers rows (FK targets for jobs)."""
    from sqlalchemy import text as sql_text

    seen: set[str] = set()
    for bid, cid in buyer_specs:
        if cid not in seen:
            seen.add(cid)
            session.execute(
                sql_text("INSERT OR IGNORE INTO companies (id, world_id, name, sector, budget) VALUES (:i, :w, :n, :s, :b)"),
                {"i": cid, "w": world.id, "n": f"Company {cid}", "s": "media", "b": 0},
            )
        session.execute(
            sql_text(
                "INSERT OR IGNORE INTO buyers (id, world_id, company_id, name, persona_json, quality_bar, roles_json) "
                "VALUES (:i, :w, :c, :n, '{}', 0.7, '[\"content_creator\"]')"
            ),
            {"i": bid, "w": world.id, "c": cid, "n": f"Buyer {bid}"},
        )
    session.flush()


def seed_companies_and_buyers(world: World, ledger: LedgerWriter, events: EventLog, session: Any = None) -> None:
    """Create companies+buyers from preset config, funded from treasury (buyer:<id> accounts)."""
    cfg = world.config.get("buyers", {})
    n_companies = int(cfg.get("companies", 4))
    per_company = int(cfg.get("buyers_per_company", 2))
    initial = int(cfg.get("initial_budget", 5_000))
    buyer_specs: list[tuple[str, str]] = []
    # ensure treasury is funded (mint logged once)
    if ledger.balance("treasury") < n_companies * per_company * initial:
        mint = n_companies * per_company * initial
        ledger.post(tick=world.tick, debit="treasury_mint", credit="treasury", amount=mint, reason="treasury_mint")
        events.emit(world.id, tick=world.tick, type_="treasury_minted", agent_id=None, payload={"amount": mint})

    for _c in range(n_companies):
        cid = world.ids.next("company")
        for _b in range(per_company):
            bid = world.ids.next("buyer")
            ledger.post(
                tick=world.tick, debit="treasury", credit=f"buyer:{bid}",
                amount=initial, reason="buyer_funding", ref_type="buyer", ref_id=bid,
            )
            world.accounts[f"buyer:{bid}"] = initial
            buyer_specs.append((bid, cid))
            events.emit(
                world.id, tick=world.tick, type_="buyer_funded", agent_id=None,
                payload={"buyer_id": bid, "company_id": cid, "amount": initial},
            )
    if session is not None:
        _persist_buyers(session, world, buyer_specs)


def buyer_can_fund(world: World, buyer_id: str, reward: int) -> bool:
    """A buyer cannot overpay: job posting requires full reward on hand."""
    return world.accounts.get(f"buyer:{buyer_id}", 0) >= reward


def topup_buyers_if_needed(world: World, ledger: LedgerWriter, events: EventLog) -> None:
    """Money-supply floor rule from economy.buyer_topup (runs end of tick)."""
    eco = world.economy
    if eco is None:
        return
    buyer_accounts = [a for a in world.accounts if a.startswith("buyer:")]
    if not buyer_accounts:
        return
    total_supply = sum(world.accounts.values())
    floor = eco.buyer_topup.floor_money_supply_ratio * total_supply
    buyer_total = sum(world.accounts[a] for a in buyer_accounts)
    if buyer_total >= floor:
        return
    per = eco.buyer_topup.amount_per_buyer
    for acct in sorted(buyer_accounts):
        ledger.post(
            tick=world.tick, debit="treasury", credit=acct, amount=per,
            reason="buyer_topup", ref_type="buyer", ref_id=acct.split(":", 1)[1],
        )
        world.accounts[acct] = world.accounts.get(acct, 0) + per
        events.emit(
            world.id, tick=world.tick, type_="buyer_topup", agent_id=None,
            payload={"account": acct, "amount": per},
        )


def apply_payment(world: World, ledger: LedgerWriter, *, job_id: str, buyer_id: str, agent_id: str, payout: int, event_id: int) -> None:
    """Move verified payout from buyer to agent; mirrors into world.accounts."""
    ledger.post(
        tick=world.tick, debit=f"buyer:{buyer_id}", credit=f"agent:{agent_id}",
        amount=payout, reason="job_payment", ref_type="job", ref_id=job_id, event_id=event_id,
    )
    world.accounts[f"buyer:{buyer_id}"] = world.accounts.get(f"buyer:{buyer_id}", 0) - payout
    world.accounts[f"agent:{agent_id}"] = world.accounts.get(f"agent:{agent_id}", 0) + payout
