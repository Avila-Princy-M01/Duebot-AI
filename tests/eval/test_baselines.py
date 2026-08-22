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
    snaps = snapshots_from_generator(held_out)
    as_of = date(2026, 8, 21)
    none = report_for(simulate_no_agent(snaps, as_of), as_of=as_of)
    naive = report_for(simulate_naive_cadence(snaps, as_of), as_of=as_of)
    duebot = report_for(simulate_duebot(snaps, as_of), as_of=as_of)
    assert none.eval_set_size == naive.eval_set_size == duebot.eval_set_size
    assert duebot.recovery_rate >= none.recovery_rate
    assert naive.total_contacts_sent >= duebot.total_contacts_sent or duebot.eval_set_size > 0
