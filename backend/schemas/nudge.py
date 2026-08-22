"""Nudge preview/trigger schemas."""

from __future__ import annotations

from pydantic import BaseModel


class NudgeTriggerRequest(BaseModel):
    """POST /api/nudge/trigger body."""

    invoice_id: str


class NudgePreview(BaseModel):
    """What would be sent — never sends."""

    invoice_id: str
    allowed: bool
    policy_reason: str
    approaching_cap: bool
    contacts_this_week: int
    drafted_message: str
    channel: str
    next_action_at: str | None
    current_state: str
    target_event: str


class NudgeTriggerResult(BaseModel):
    """Result of a manual nudge cycle."""

    invoice_id: str
    dry_run: bool
    sent: bool
    preview: NudgePreview
    new_state: str | None = None
