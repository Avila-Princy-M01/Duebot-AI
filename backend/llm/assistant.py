"""Interactive DueBot Executive Assistant (read-only LLM periphery).

Answers arbitrary natural language and voice queries about buyers, invoices,
promises, risk tiers, and receivables status grounded in live database facts.
"""

from __future__ import annotations

from dataclasses import dataclass

from anthropic.types import ToolParam

from backend.exceptions import ConfigurationError, IntegrationError
from backend.llm.client import AnthropicClient

SUBMIT_ASSISTANT_RESPONSE_TOOL: ToolParam = {
    "name": "submit_assistant_response",
    "description": "Submit structured answer to the merchant query.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "Concise markdown answer with factual metrics and bullets",
            },
            "spoken_answer": {
                "type": "string",
                "description": "Natural text for browser Web Speech audio readout",
            },
            "category": {
                "type": "string",
                "description": "Query category e.g. Buyer Status, Risk Analysis, Overview",
            },
            "suggested_action": {
                "type": ["string", "null"],
                "description": "Recommended merchant action if applicable",
            },
        },
        "required": ["answer", "spoken_answer", "category"],
    },
}


@dataclass(frozen=True)
class AssistantContext:
    """Live database context grounded for the assistant."""

    query: str
    total_invoices_count: int
    overdue_count: int
    amount_at_risk_inr: str
    aging_summary: str
    buyers_summary: list[str]
    active_promises: list[str]
    recent_audits: list[str]
    specific_buyer_context: str | None = None
    specific_invoice_context: str | None = None


@dataclass(frozen=True)
class AssistantAnswer:
    """Structured response for UI and voice readout."""

    answer: str
    spoken_answer: str
    category: str
    suggested_action: str | None
    model: str


def render_fallback_answer(ctx: AssistantContext) -> AssistantAnswer:
    """Deterministic fallback answer if model is offline."""
    q_lower = ctx.query.lower()
    if any(k in q_lower for k in ("risk", "overdue", "total", "at risk")):
        ans = (
            f"Currently, there are **{ctx.overdue_count} overdue invoices** totaling "
            f"**INR {ctx.amount_at_risk_inr}** at risk. {ctx.aging_summary}"
        )
        spoken = (
            f"There are {ctx.overdue_count} overdue invoices totaling "
            f"{ctx.amount_at_risk_inr} rupees at risk."
        )
        cat = "Receivables Overview"
        action = "Review high-risk invoices on the receivables ledger."
    elif ctx.specific_buyer_context:
        ans = f"Buyer details:\n{ctx.specific_buyer_context}"
        spoken = "Here is the summary for the selected buyer based on our receivables ledger."
        cat = "Buyer Status"
        action = "Send scheduled nudge via Razorpay WhatsApp link."
    else:
        ans = (
            f"DueBot is currently tracking {ctx.total_invoices_count} invoices. "
            f"Amount at risk is INR {ctx.amount_at_risk_inr}. "
            f"Top active buyers include: {', '.join(ctx.buyers_summary[:4])}."
        )
        spoken = (
            f"DueBot is tracking {ctx.total_invoices_count} invoices with "
            f"{ctx.amount_at_risk_inr} rupees at risk."
        )
        cat = "Portfolio Status"
        action = "Check the live dashboard for aging distribution."

    return AssistantAnswer(
        answer=ans,
        spoken_answer=spoken,
        category=cat,
        suggested_action=action,
        model="template",
    )


class DueBotAssistant:
    """Answer natural language and voice queries about the receivables portfolio."""

    def __init__(self, client: AnthropicClient) -> None:
        self._client = client

    async def answer(self, ctx: AssistantContext) -> AssistantAnswer:
        """Answer merchant query grounded in live DB context."""
        fallback = render_fallback_answer(ctx)
        if not self._client.configured:
            return fallback

        system = (
            "You are DueBot's interactive executive voice & finance assistant. "
            "You answer merchant questions about buyers, invoices, promises, risk tiers, "
            "and receivables status grounded strictly in the provided database context. "
            "Never invent facts or make policy state transitions. "
            "Provide both a clean markdown `answer` and a natural, conversational `spoken_answer` "
            "suitable for browser text-to-speech."
        )

        user_prompt = (
            f'Merchant Question: "{ctx.query}"\n\n'
            f"LIVE DATABASE FACTS:\n"
            f"- Total Invoices: {ctx.total_invoices_count} ({ctx.overdue_count} overdue)\n"
            f"- Amount At Risk: INR {ctx.amount_at_risk_inr}\n"
            f"- Aging Distribution: {ctx.aging_summary}\n"
            "- Active Promises:\n"
            + "\n".join(f"  * {p}" for p in ctx.active_promises[:4])
            + "\n- Recent Audit Trail:\n"
            + "\n".join(f"  * {a}" for a in ctx.recent_audits[:4])
            + "\n- Key Buyers Directory:\n"
            + "\n".join(f"  * {b}" for b in ctx.buyers_summary[:10])
            + "\n"
        )

        if ctx.specific_buyer_context:
            user_prompt += f"\nSPECIFIC BUYER CONTEXT:\n{ctx.specific_buyer_context}\n"
        if ctx.specific_invoice_context:
            user_prompt += f"\nSPECIFIC INVOICE CONTEXT:\n{ctx.specific_invoice_context}\n"

        user_prompt += "\nAnswer the question directly and concisely."

        try:
            payload, _, _ = await self._client.complete_tool(
                system=system,
                user=user_prompt,
                tools=[SUBMIT_ASSISTANT_RESPONSE_TOOL],
                tool_choice_name="submit_assistant_response",
            )
            return AssistantAnswer(
                answer=str(payload.get("answer") or fallback.answer),
                spoken_answer=str(payload.get("spoken_answer") or fallback.spoken_answer),
                category=str(payload.get("category") or fallback.category),
                suggested_action=payload.get("suggested_action") or fallback.suggested_action,
                model="claude",
            )
        except (ConfigurationError, IntegrationError):
            return fallback
