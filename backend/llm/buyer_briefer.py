"""Scoped buyer summarizer (read-only LLM periphery).

Pulls existing interactions, promises, and audit rows logged by DueBot.
Never makes decisions — only summarizes already-computed facts for the merchant.
"""

from __future__ import annotations

from dataclasses import dataclass

from anthropic.types import ToolParam

from backend.exceptions import ConfigurationError, IntegrationError
from backend.llm.client import AnthropicClient

SUBMIT_BUYER_BRIEF_TOOL: ToolParam = {
    "name": "submit_buyer_brief",
    "description": "Submit structured buyer brief.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "2-3 sentence markdown summary for dashboard",
            },
            "spoken_summary": {
                "type": "string",
                "description": "Natural text for browser text-to-speech audio readout",
            },
            "risk_assessment": {
                "type": "string",
                "description": "1-sentence buyer risk assessment",
            },
            "recommended_action": {
                "type": "string",
                "description": "1-sentence recommended next step",
            },
        },
        "required": [
            "summary",
            "spoken_summary",
            "risk_assessment",
            "recommended_action",
        ],
    },
}


@dataclass(frozen=True)
class BuyerBriefRequest:
    """Read-only buyer context to summarize."""

    buyer_id: str
    company_name: str
    contact_name: str
    reliability_tier: str
    on_time_rate_pct: float
    relationship_years: float
    total_invoices_count: int
    open_invoices_count: int
    total_outstanding_inr: str
    recent_interactions: list[str]
    active_promises: list[str]
    recent_audits: list[str]


@dataclass(frozen=True)
class BuyerBriefResult:
    """Structured brief for merchant and voice readout."""

    summary: str
    spoken_summary: str
    risk_assessment: str
    recommended_action: str
    model: str


FALLBACK_TEMPLATE = (
    "{company_name} ({contact_name}) is classified as {reliability_tier} with an on-time "
    "payment rate of {on_time_rate_pct:.0f}%. Currently holding {open_invoices_count} open "
    "invoice(s) totaling INR {total_outstanding_inr} across a "
    "{relationship_years:.1f}-year relationship. {recent_activity_note}"
)


def render_fallback_brief(req: BuyerBriefRequest) -> BuyerBriefResult:
    """Deterministic fallback brief without calling external LLM."""
    if req.active_promises:
        activity = f"Active promise: {req.active_promises[0]}."
    elif req.recent_interactions:
        activity = f"Latest contact: {req.recent_interactions[0]}."
    else:
        activity = "No recent communication recorded."

    text = FALLBACK_TEMPLATE.format(
        company_name=req.company_name,
        contact_name=req.contact_name,
        reliability_tier=req.reliability_tier.replace("_", " ").title(),
        on_time_rate_pct=req.on_time_rate_pct,
        open_invoices_count=req.open_invoices_count,
        total_outstanding_inr=req.total_outstanding_inr,
        relationship_years=req.relationship_years,
        recent_activity_note=activity,
    )

    action = (
        "Send scheduled WhatsApp nudge with Razorpay link"
        if req.reliability_tier != "chronic_late"
        else "Escalate to account manager for formal call"
    )

    risk = f"Tier: {req.reliability_tier.title()} ({req.on_time_rate_pct:.0f}% on-time rate)"

    return BuyerBriefResult(
        summary=text,
        spoken_summary=text,
        risk_assessment=risk,
        recommended_action=action,
        model="template",
    )


class BuyerBriefer:
    """Summarize buyer history; strictly read-only."""

    def __init__(self, client: AnthropicClient) -> None:
        self._client = client

    async def brief(self, req: BuyerBriefRequest) -> BuyerBriefResult:
        """Return executive summary brief."""
        fallback = render_fallback_brief(req)
        if not self._client.configured:
            return fallback

        system = (
            "You are DueBot's executive merchant briefing assistant. "
            "Your role is strictly to summarize the provided factual buyer history "
            "into a crisp, professional 2-3 sentence executive briefing. "
            "Do NOT hallucinate invoice amounts or make binding policy decisions. "
            "Return JSON matching the schema."
        )

        user_prompt = (
            f"Buyer: {req.company_name} (Contact: {req.contact_name})\n"
            f"Reliability Tier: {req.reliability_tier}\n"
            f"On-time Payment Rate: {req.on_time_rate_pct:.1f}%\n"
            f"Relationship Length: {req.relationship_years:.1f} years\n"
            f"Open Invoices: {req.open_invoices_count} "
            f"(Total Outstanding: INR {req.total_outstanding_inr})\n"
            "Recent Interactions:\n"
            + "\n".join(f"- {i}" for i in req.recent_interactions[:3])
            + "\nActive Promises:\n"
            + "\n".join(f"- {p}" for p in req.active_promises[:2])
            + "\nAudit Trail:\n"
            + "\n".join(f"- {a}" for a in req.recent_audits[:3])
            + "\nSummarize this buyer concisely."
        )

        try:
            payload, _, _ = await self._client.complete_tool(
                system=system,
                user=user_prompt,
                tools=[SUBMIT_BUYER_BRIEF_TOOL],
                tool_choice_name="submit_buyer_brief",
            )
            return BuyerBriefResult(
                summary=str(payload.get("summary") or fallback.summary),
                spoken_summary=str(payload.get("spoken_summary") or fallback.spoken_summary),
                risk_assessment=str(payload.get("risk_assessment") or fallback.risk_assessment),
                recommended_action=str(
                    payload.get("recommended_action") or fallback.recommended_action
                ),
                model="claude",
            )
        except (ConfigurationError, IntegrationError):
            return fallback
