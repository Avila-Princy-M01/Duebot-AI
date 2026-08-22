"""Anthropic client wrapper — the only module that constructs the SDK client.

Retries, timeouts, and token-usage logging live here. The engine never imports this.
"""

from __future__ import annotations

from typing import Any

import structlog
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam, ToolParam

from backend.config import Settings, get_settings
from backend.exceptions import ConfigurationError, IntegrationError

logger = structlog.get_logger("duebot.llm")

MAX_RETRIES = 2
TIMEOUT_SECONDS = 20.0


class AnthropicClient:
    """Thin async wrapper around the official Anthropic SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: AsyncAnthropic | None = None
        if self._settings.anthropic_configured:
            self._client = AsyncAnthropic(
                api_key=self._settings.anthropic_api_key,
                timeout=TIMEOUT_SECONDS,
                max_retries=MAX_RETRIES,
            )

    @property
    def configured(self) -> bool:
        """True when a live API key is present."""
        return self._client is not None

    async def complete_tool(
        self,
        *,
        system: str,
        user: str,
        tools: list[ToolParam],
        tool_choice_name: str,
        model: str | None = None,
    ) -> tuple[dict[str, Any], int, int]:
        """Call Claude with forced tool use.

        Returns:
            (tool input dict, input_tokens, output_tokens)

        Raises:
            ConfigurationError: No API key.
            IntegrationError: API failed or did not return the expected tool call.
        """
        if self._client is None:
            raise ConfigurationError("ANTHROPIC_API_KEY is not set")

        messages: list[MessageParam] = [{"role": "user", "content": user}]
        try:
            response: Message = await self._client.messages.create(
                model=model or self._settings.anthropic_model,
                max_tokens=512,
                system=system,
                tools=tools,
                tool_choice={"type": "tool", "name": tool_choice_name},
                messages=messages,
            )
        except Exception as exc:
            logger.error("anthropic_call_failed", error=type(exc).__name__)
            raise IntegrationError("Claude API call failed") from None

        usage_in = int(response.usage.input_tokens)
        usage_out = int(response.usage.output_tokens)
        logger.info(
            "llm_tokens", input_tokens=usage_in, output_tokens=usage_out, model=response.model
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == tool_choice_name:
                if not isinstance(block.input, dict):
                    raise IntegrationError("Claude tool input was not an object")
                return block.input, usage_in, usage_out

        raise IntegrationError("Claude did not return the expected tool call")
