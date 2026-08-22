"""Reply parser: tool JSON mapping and fallback abstention."""

from __future__ import annotations

from datetime import date

from backend.engine.policy import ReplyIntent
from backend.llm.reply_parser import fallback_intent, parsed_intent_from_tool_input


def test_parsed_intent_from_tool_input() -> None:
    """Function-calling payload becomes a ParsedIntent — no regex on prose."""
    parsed = parsed_intent_from_tool_input(
        {
            "intent": "promise",
            "promised_date": "2026-08-28",
            "promised_amount": None,
            "confidence": 0.91,
            "reasoning": "Buyer named Friday.",
        }
    )
    assert parsed.intent is ReplyIntent.PROMISE
    assert parsed.promised_date == date(2026, 8, 28)
    assert parsed.confidence == 0.91


def test_fallback_abstains_on_ambiguous() -> None:
    """The demo wow-moment string must not become a promise."""
    parsed = fallback_intent("will sort it out soon")
    assert parsed.intent is ReplyIntent.AMBIGUOUS
    assert parsed.confidence < 0.7
