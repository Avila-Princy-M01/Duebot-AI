"""Draft a nudge inside a locked template envelope.

Amounts, invoice numbers, due dates, and payment links are injected
verbatim from the database — the model only chooses phrasing.
"""

from __future__ import annotations

from backend.exceptions import ConfigurationError, IntegrationError
from backend.llm.client import AnthropicClient
from backend.llm.prompts import message_drafting
from backend.llm.types import DraftedMessage, DraftRequest

TEMPLATE = (
    "Hi {buyer_first_name}, this is a reminder that invoice {invoice_number} "
    "for INR {amount_inr} was due on {due_date} ({days_overdue} days overdue). "
    "Please pay using {payment_link}"
)


def render_template(request: DraftRequest) -> str:
    """Deterministic fallback body with locked facts."""
    return TEMPLATE.format(
        buyer_first_name=request.buyer_first_name,
        invoice_number=request.invoice_number,
        amount_inr=request.amount_inr,
        due_date=request.due_date,
        days_overdue=request.days_overdue,
        payment_link=request.payment_link,
    )


class MessageDrafter:
    """Personalize tone; never invent facts."""

    def __init__(self, client: AnthropicClient) -> None:
        self._client = client

    async def draft(self, request: DraftRequest) -> DraftedMessage:
        """Return a drafted body. Falls back to the template if Claude is unset."""
        fallback = render_template(request)
        if not self._client.configured:
            return DraftedMessage(
                body=fallback,
                model="template",
                input_tokens=0,
                output_tokens=0,
            )

        user = (
            f"Tone: {request.tone}\n"
            f"Buyer first name: {request.buyer_first_name}\n"
            f"Invoice number (verbatim): {request.invoice_number}\n"
            f"Amount INR (verbatim): {request.amount_inr}\n"
            f"Due date (verbatim): {request.due_date}\n"
            f"Days overdue (verbatim): {request.days_overdue}\n"
            f"Payment link (verbatim): {request.payment_link}\n"
            f"Template to stay faithful to:\n{fallback}\n"
            "Rewrite tone only. Keep every fact identical."
        )
        try:
            payload, in_tok, out_tok = await self._client.complete_tool(
                system=message_drafting.SYSTEM_PROMPT,
                user=user,
                tools=[
                    {
                        "name": "submit_draft",
                        "description": "Submit the personalized message.",
                        "input_schema": {
                            "type": "object",
                            "properties": {"body": {"type": "string"}},
                            "required": ["body"],
                        },
                    }
                ],
                tool_choice_name="submit_draft",
            )
        except (ConfigurationError, IntegrationError):
            return DraftedMessage(body=fallback, model="template", input_tokens=0, output_tokens=0)

        body = str(payload.get("body") or fallback)
        for fact in (
            request.invoice_number,
            request.amount_inr,
            request.due_date,
            request.payment_link,
        ):
            if fact not in body:
                body = fallback
                break
        return DraftedMessage(
            body=body,
            model="claude",
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
