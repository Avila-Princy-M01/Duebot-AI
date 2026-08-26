"""Cryptographic SHA-256 hash chaining and tamper-evidence verification for audit_log."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.models.audit_log import AuditLog

GENESIS_HASH = "0" * 64


def compute_row_hash(
    *,
    invoice_id: str,
    from_state: str,
    to_state: str,
    actor: str,
    occurred_at: str | datetime,
    reasoning_summary: str,
    prev_hash: str,
) -> str:
    """Compute deterministic canonical SHA-256 hash over an audit transition block."""
    if isinstance(occurred_at, datetime):
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        iso_time = occurred_at.isoformat()
    else:
        iso_time = str(occurred_at)

    canonical_dict: dict[str, Any] = {
        "actor": str(actor),
        "from_state": str(from_state),
        "invoice_id": str(invoice_id),
        "occurred_at": iso_time,
        "prev_hash": str(prev_hash or GENESIS_HASH),
        "reasoning_summary": str(reasoning_summary),
        "to_state": str(to_state),
    }
    serialized = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def verify_chain(rows: list[AuditLog]) -> tuple[bool, int, str, str | None]:
    """Verify cryptographic integrity of an audit log chain.

    Returns:
        (is_valid, count_verified, latest_hash, error_message)
    """
    if not rows:
        return True, 0, GENESIS_HASH, None

    expected_prev = GENESIS_HASH
    for idx, row in enumerate(rows):
        if row.prev_hash != expected_prev:
            return (
                False,
                idx,
                row.row_hash,
                (
                    f"Broken chain at block {idx} (invoice {row.invoice_id}): "
                    f"expected prev_hash {expected_prev}, got {row.prev_hash}"
                ),
            )
        computed = compute_row_hash(
            invoice_id=row.invoice_id,
            from_state=row.from_state,
            to_state=row.to_state,
            actor=row.actor,
            occurred_at=row.occurred_at,
            reasoning_summary=row.reasoning_summary,
            prev_hash=row.prev_hash,
        )
        if computed != row.row_hash:
            return (
                False,
                idx,
                row.row_hash,
                (
                    f"Tampered row at block {idx} (invoice {row.invoice_id}): "
                    f"expected hash {computed}, stored {row.row_hash}"
                ),
            )
        expected_prev = row.row_hash

    return True, len(rows), rows[-1].row_hash, None
