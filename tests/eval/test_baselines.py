"""Eval harness uses the real generator, never fixture stubs."""

from __future__ import annotations

from datetime import date

from backend.data.baselines import (
    report_for,
    simulate_duebot,
    simulate_naive_cadence,
    simulate_no_agent,
    snapshots_from_generator,
)
from backend.data.generator import DueBotDataGenerator


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
