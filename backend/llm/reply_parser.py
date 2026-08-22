"""Parse buyer free text into a structured intent via Claude tool-use.

Never regex-parse model output. Confidence below threshold is the caller's
problem (``engine.policy.event_for_parsed_intent``).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from anthropic.types import ToolParam

from backend.engine.policy import ReplyIntent
from backend.exceptions import ConfigurationError, IntegrationError
from backend.llm.client import AnthropicClient
from backend.llm.prompts import reply_parsing
from backend.llm.types import ParsedIntent

EXTRACT_REPLY_INTENT_TOOL: ToolParam = {
    "name": "extract_reply_intent",
    "description": "Classify a buyer's reply to a payment nudge.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["promise", "ambiguous", "dispute", "opt_out", "objection"],
            },
            "promised_date": {
                "type": ["string", "null"],
                "description": "ISO date, if intent=promise",
            },
            "promised_amount": {
                "type": ["number", "null"],
                "description": "if partial payment promised",
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {
                "type": "string",
                "description": "one sentence, shown to the human reviewer",
            },
        },
        "required": ["intent", "confidence", "reasoning"],
    },
}


def parsed_intent_from_tool_input(payload: dict[str, Any]) -> ParsedIntent:
    """Validate tool-call JSON into ``ParsedIntent``.

    Args:
        payload: The ``tool_use.input`` object from Claude.

    Returns:
        A typed ``ParsedIntent``.
    """
    promised_raw = payload.get("promised_date")
    promised_date: date | None = None
    if isinstance(promised_raw, str) and promised_raw:
        promised_date = date.fromisoformat(promised_raw)

    amount_raw = payload.get("promised_amount")
    promised_amount: Decimal | None = None
    if amount_raw is not None:
        promised_amount = Decimal(str(amount_raw))

    return ParsedIntent(
        intent=ReplyIntent(str(payload["intent"])),
        promised_date=promised_date,
        promised_amount=promised_amount,
        confidence=float(payload["confidence"]),
        reasoning=str(payload["reasoning"]),
    )


def fallback_intent(reply_text: str, *, as_of: date | None = None) -> ParsedIntent:
    """Offline classifier used when ANTHROPIC_API_KEY is unset.

    This inspects *buyer* text (untrusted input), never model prose. Live
    deployments with a key always go through tool-use instead.
    """
    lowered = reply_text.lower()
    if any(token in lowered for token in ("stop messaging", "do not send", "remove this number")):
        return ParsedIntent(
            intent=ReplyIntent.OPT_OUT,
            confidence=0.95,
            reasoning="Buyer asked to stop contact on this channel.",
        )
    if any(
        token in lowered
        for token in ("wrong", "never received", "duplicate", "mismatch", "already paid")
    ):
        return ParsedIntent(
            intent=ReplyIntent.DISPUTE,
            confidence=0.9,
            reasoning="Buyer challenged the invoice rather than promising payment.",
        )
    if any(
        token in lowered
        for token in ("soon", "will see", "get back", "don't worry", "in process", "dekhta")
    ):
        return ParsedIntent(
            intent=ReplyIntent.AMBIGUOUS,
            confidence=0.31,
            reasoning="No date or commitment stated — abstain.",
        )
    if any(
        token in lowered for token in ("two more weeks", "resend", "last working day", "waiting on")
    ):
        return ParsedIntent(
            intent=ReplyIntent.OBJECTION,
            confidence=0.82,
            reasoning="Buyer requested a delay or a document fix, not a pay-by date.",
        )
    if any(
        token in lowered
        for token in ("will pay", "bhej dunga", "clearing this", "settle", "transfer by")
    ):
        promised = as_of or date.today()
        from datetime import timedelta

        return ParsedIntent(
            intent=ReplyIntent.PROMISE,
            promised_date=promised + timedelta(days=5),
            confidence=0.91,
            reasoning="Buyer stated an explicit payment commitment.",
        )
    return ParsedIntent(
        intent=ReplyIntent.AMBIGUOUS,
        confidence=0.2,
        reasoning="Reply did not match a high-confidence intent class.",
    )


class ReplyParser:
    """Turns untrusted buyer text into ``ParsedIntent``."""

    def __init__(self, client: AnthropicClient) -> None:
        self._client = client

    async def parse(self, reply_text: str, *, as_of: date | None = None) -> ParsedIntent:
        """Classify ``reply_text``.

        The buyer text is placed only in the user turn, never in the system prompt.
        """
        if not self._client.configured:
            return fallback_intent(reply_text, as_of=as_of)
        today = as_of.isoformat() if as_of is not None else "unknown"
        user = f"Today's date (ISO): {today}\n\nBuyer reply (untrusted):\n{reply_text}"
        try:
            payload, _in_tok, _out_tok = await self._client.complete_tool(
                system=reply_parsing.SYSTEM_PROMPT,
                user=user,
                tools=[EXTRACT_REPLY_INTENT_TOOL],
                tool_choice_name="extract_reply_intent",
            )
        except (ConfigurationError, IntegrationError):
            return fallback_intent(reply_text, as_of=as_of)
        return parsed_intent_from_tool_input(payload)
