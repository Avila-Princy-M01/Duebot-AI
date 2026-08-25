"""Eval harness uses the real generator, never fixture stubs."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from backend.data.baselines import (
    report_for,
    simulate_duebot,
    simulate_naive_cadence,
    simulate_no_agent,
    snapshots_from_generator,
)
from backend.data.generator import DueBotDataGenerator
from backend.engine.policy import can_contact


def test_three_way_eval_on_generator_test_split() -> None:
    """All three strategies run on the same held-out generator invoices."""
    gen = DueBotDataGenerator(seed=42)
    gen.run(num_invoices=80)
    held_out = [inv for inv in gen.invoices if inv.split == "test"]
    assert len(held_out) > 0
    snaps = snapshots_from_generator(held_out, gen.messages)
    as_of = date(2026, 8, 21)
    none = report_for(simulate_no_agent(snaps, as_of), as_of=as_of)
    naive = report_for(simulate_naive_cadence(snaps, as_of), as_of=as_of)
    duebot = report_for(simulate_duebot(snaps, as_of), as_of=as_of)

    # Invariant 1: Same cohort size evaluated across all 3 arms
    assert none.eval_set_size == naive.eval_set_size == duebot.eval_set_size

    # Invariant 2: DueBot achieves >= recovery rate of no-agent baseline
    assert duebot.recovery_rate >= none.recovery_rate

    # Invariant 3: DueBot recovers faster with lower or equal average days to recovery
    assert duebot.avg_days_to_recovery <= naive.avg_days_to_recovery

    # Invariant 4: Naive sends contacts on disputed items; DueBot's policy gate halts contacts
    sim_due = simulate_duebot(snaps, as_of)
    sim_naive = simulate_naive_cadence(snaps, as_of)
    disputed_due = [inv for inv in sim_due if inv.status == "disputed"]
    disputed_naive = [inv for inv in sim_naive if inv.status == "disputed"]

    if disputed_due:
        # DueBot sends 0 touches on disputed invoices due to can_contact gate
        assert all(inv.contacts == 0 for inv in disputed_due)
    if disputed_naive:
        # Naive lacks policy gate, so it contacts disputed invoices
        assert any(inv.contacts > 0 for inv in disputed_naive)


def test_multi_seed_evaluation_stability() -> None:
    """Verify that DueBot's contact reduction and dispute protection hold across multiple seeds."""
    as_of = date(2026, 8, 21)
    for seed in (42, 101, 202):
        gen = DueBotDataGenerator(seed=seed)
        gen.run(num_invoices=100)
        held_out = [inv for inv in gen.invoices if inv.split == "test"]
        snaps = snapshots_from_generator(held_out, gen.messages)

        rep_naive = report_for(simulate_naive_cadence(snaps, as_of), as_of=as_of)
        rep_due = report_for(simulate_duebot(snaps, as_of), as_of=as_of)

        # Invariant: DueBot sends significantly fewer contacts than blind naive loop
        assert rep_due.total_contacts_sent < rep_naive.total_contacts_sent
        # Invariant: DueBot capital efficiency (recovery per contact) strictly exceeds naive
        assert rep_due.recovery_per_contact > rep_naive.recovery_per_contact


def test_dispute_policy_gate_blocks_contacts_mid_timeline_and_pre_existing() -> None:
    """Verify that can_contact() policy gate actively blocks touches on disputed invoices."""
    as_of = date(2026, 8, 21)
    gen = DueBotDataGenerator(seed=42)
    gen.run(num_invoices=150)
    test_invoices = [inv for inv in gen.invoices if inv.split == "test"]
    snaps = snapshots_from_generator(test_invoices, gen.messages)

    sim_due = simulate_duebot(snaps, as_of)
    disputed = [
        inv
        for inv in sim_due
        if inv.status == "disputed" or inv.state.value in ("disputed", "human_review")
    ]
    assert len(disputed) > 0

    # 1. Zero touches on disputed invoices across entire day-stepping run
    for inv in disputed:
        assert inv.contacts == 0
        # 2. Verify that can_contact() explicitly returns allowed=False on this invoice
        clock_dt = datetime.combine(as_of, time(10, 0), tzinfo=UTC)
        decision = can_contact(inv, inv.history, as_of=clock_dt)
        assert not decision.allowed
        assert (
            "disputed" in decision.reason.lower()
            or "human review" in decision.reason.lower()
        )
