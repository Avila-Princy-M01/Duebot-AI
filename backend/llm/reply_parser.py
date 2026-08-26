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
    """Offline classifier used when API key is unset or rate limited.

    This inspects *buyer* text (untrusted input), never model prose. Live
    deployments with a key always go through tool-use instead.
    """
    lowered = reply_text.lower()
    if any(
        token in lowered
        for token in (
            "stop messaging",
            "do not contact",
            "remove",
            "unsubscribe",
            "mat bhejna",
            "block",
            "don't send",
            "stop spamming",
        )
    ):
        return ParsedIntent(
            intent=ReplyIntent.OPT_OUT,
            confidence=0.95,
            reasoning="Buyer asked to stop contact on this channel.",
        )
    if any(
        token in lowered
        for token in (
            "wrong",
            "never received",
            "duplicate",
            "mismatch",
            "already paid",
            "galat bill",
            "higher than",
            "never ordered",
            "discount",
        )
    ):
        return ParsedIntent(
            intent=ReplyIntent.DISPUTE,
            confidence=0.9,
            reasoning="Buyer challenged the invoice rather than promising payment.",
        )
    if any(
        token in lowered
        for token in (
            "resend",
            "waiting on",
            "cash flow",
            "bank account",
            "audit leave",
            "courier",
            "erp system",
            "month end",
            "gst breakdown",
            "out of office",
            "two more weeks",
        )
    ):
        return ParsedIntent(
            intent=ReplyIntent.OBJECTION,
            confidence=0.85,
            reasoning="Buyer requested a document fix, info, or process delay.",
        )
    if any(
        token in lowered
        for token in (
            "clear payment",
            "bhej dunga",
            "will transfer",
            "will pay",
            "rtgs",
            "settle",
            "pakka",
            "cheque",
            "neft",
            "releasing",
            "clearing this",
        )
    ):
        promised = as_of or date.today()
        from datetime import timedelta

        return ParsedIntent(
            intent=ReplyIntent.PROMISE,
            promised_date=promised + timedelta(days=5),
            confidence=0.91,
            reasoning="Buyer stated an explicit payment commitment.",
        )
    if any(
        token in lowered
        for token in (
            "soon",
            "will see",
            "get back",
            "don't worry",
            "in process",
            "dekhta",
            "noted",
        )
    ):
        return ParsedIntent(
            intent=ReplyIntent.AMBIGUOUS,
            confidence=0.35,
            reasoning="No date or commitment stated — abstain.",
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

    async def parse_with_meta(
        self,
        reply_text: str,
        *,
        as_of: date | None = None,
        allow_fallback: bool = True,
    ) -> tuple[ParsedIntent, bool]:
        """Classify ``reply_text`` and return tuple of (ParsedIntent, is_fallback).

        If ``allow_fallback`` is False and the API call fails or is unconfigured,
        this method raises ConfigurationError / IntegrationError.
        """
        if not self._client.configured:
            if not allow_fallback:
                raise ConfigurationError("LLM API key is not configured")
            return fallback_intent(reply_text, as_of=as_of), True
        today = as_of.isoformat() if as_of is not None else "unknown"
        user = f"Today's date (ISO): {today}\n\nBuyer reply (untrusted):\n{reply_text}"
        try:
            payload, _in_tok, _out_tok = await self._client.complete_tool(
                system=reply_parsing.SYSTEM_PROMPT,
                user=user,
                tools=[EXTRACT_REPLY_INTENT_TOOL],
                tool_choice_name="extract_reply_intent",
            )
        except (ConfigurationError, IntegrationError) as err:
            if not allow_fallback:
                raise err
            return fallback_intent(reply_text, as_of=as_of), True
        return parsed_intent_from_tool_input(payload), False

    async def parse(
        self,
        reply_text: str,
        *,
        as_of: date | None = None,
        allow_fallback: bool = True,
    ) -> ParsedIntent:
        """Classify ``reply_text``.

        The buyer text is placed only in the user turn, never in the system prompt.
        """
        result, _ = await self.parse_with_meta(
            reply_text, as_of=as_of, allow_fallback=allow_fallback
        )
        return result
