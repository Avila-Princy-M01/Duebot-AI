"""Run the three-way eval on the real generator test split and print a report."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

from backend.data.baselines import (
    report_for,
    simulate_duebot,
    simulate_naive_cadence,
    simulate_no_agent,
    snapshots_from_generator,
)
from backend.data.generator import SIM_TODAY, DueBotDataGenerator


def run_eval(*, seed: int = 42, num_invoices: int = 260) -> dict[str, object]:
    """Execute no-agent / naive-cadence / DueBot on the held-out split.

    Returns:
        JSON-serializable report keyed by strategy.
    """
    gen = DueBotDataGenerator(seed=seed)
    gen.run(num_invoices=num_invoices)
    held_out = [inv for inv in gen.invoices if inv.split == "test"]
    as_of: date = SIM_TODAY
    snaps = snapshots_from_generator(held_out)
    run_id = str(uuid4())
    strategies = {
        "no_agent": simulate_no_agent(snaps, as_of),
        "naive_cadence": simulate_naive_cadence(snaps, as_of),
        "duebot": simulate_duebot(snaps, as_of),
    }
    report: dict[str, object] = {
        "run_id": run_id,
        "as_of": as_of.isoformat(),
        "n_test": len(held_out),
    }
    rows: dict[str, object] = {}
    for name, simulated in strategies.items():
        rec = report_for(simulated, as_of=as_of)
        rows[name] = {
            "eval_set_size": rec.eval_set_size,
            "recovered_count": rec.recovered_count,
            "recovered_value": str(rec.recovered_value),
            "total_value": str(rec.total_value),
            "recovery_rate": rec.recovery_rate,
            "recovery_30d": rec.recovery_30d,
            "recovery_60d": rec.recovery_60d,
            "recovery_90d": rec.recovery_90d,
            "avg_days_to_recovery": rec.avg_days_to_recovery,
            "promise_kept_rate": rec.promise_kept_rate,
            "false_escalation_rate": rec.false_escalation_rate,
            "total_contacts_sent": rec.total_contacts_sent,
            "recovery_per_contact": rec.recovery_per_contact,
        }
    report["strategies"] = rows
    return report


def main() -> None:
    """CLI entry: write report JSON next to this file."""
    payload = run_eval()
    out = Path(__file__).with_name("last_report.json")
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
