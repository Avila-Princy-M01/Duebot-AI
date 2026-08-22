"""Turn a three-way eval dict into a markdown table for the pitch README."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def markdown_table(report: Mapping[str, Any]) -> str:
    """Render strategy rows as a GitHub-flavored markdown table."""
    strategies = report.get("strategies")
    if not isinstance(strategies, dict):
        return "_no strategies_"
    lines = [
        "| Strategy | N | Recovery rate | 30d | 60d | 90d | Contacts | False escalation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, raw in strategies.items():
        if not isinstance(raw, dict):
            continue
        lines.append(
            "| {name} | {n} | {rr:.1%} | {d30:.1%} | {d60:.1%} | {d90:.1%} | {c} | {fe:.1%} |".format(
                name=name,
                n=raw.get("eval_set_size", 0),
                rr=float(raw.get("recovery_rate", 0)),
                d30=float(raw.get("recovery_30d", 0)),
                d60=float(raw.get("recovery_60d", 0)),
                d90=float(raw.get("recovery_90d", 0)),
                c=raw.get("total_contacts_sent", 0),
                fe=float(raw.get("false_escalation_rate", 0)),
            )
        )
    return "\n".join(lines)
