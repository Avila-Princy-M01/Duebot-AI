"""LLM client wrapper — constructs Anthropic or Gemini clients with fallback.

Retries, timeouts, and token-usage logging live here. The engine never imports this.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam, ToolParam

from backend.config import Settings, get_settings
from backend.exceptions import ConfigurationError, IntegrationError

logger = structlog.get_logger("duebot.llm")

MAX_RETRIES = 2
TIMEOUT_SECONDS = 20.0


def _clean_schema_for_gemini(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert Anthropic JSON schema types to OpenAPI/Gemini upper-case types."""
    out: dict[str, Any] = {}
    for k, v in schema.items():
        if k == "type":
            if isinstance(v, list):
                types = [str(t).upper() for t in v if t != "null"]
                out["type"] = types[0] if types else "STRING"
                out["nullable"] = True
            else:
                out["type"] = str(v).upper()
        elif k == "properties" and isinstance(v, dict):
            out["properties"] = {pk: _clean_schema_for_gemini(pv) for pk, pv in v.items()}
        elif k == "items" and isinstance(v, dict):
            out["items"] = _clean_schema_for_gemini(v)
        else:
            out[k] = v
    return out


class AnthropicClient:
    """Async wrapper around Anthropic Claude & Google Gemini API."""

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
        """True when an Anthropic or Gemini API key is present."""
        return self._client is not None or self._settings.gemini_configured

    async def complete_tool(
        self,
        *,
        system: str,
        user: str,
        tools: list[ToolParam],
        tool_choice_name: str,
        model: str | None = None,
    ) -> tuple[dict[str, Any], int, int]:
        """Call Claude or Gemini with forced tool use.

        Returns:
            (tool input dict, input_tokens, output_tokens)

        Raises:
            ConfigurationError: No API key.
            IntegrationError: API failed or did not return the expected tool call.
        """
        if self._settings.gemini_configured:
            return await self._complete_gemini(
                system=system,
                user=user,
                tools=tools,
                tool_choice_name=tool_choice_name,
                model=model,
            )

        if self._client is None:
            raise ConfigurationError("Neither ANTHROPIC_API_KEY nor GEMINI_API_KEY is set")

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

    async def _complete_gemini(
        self,
        *,
        system: str,
        user: str,
        tools: list[ToolParam],
        tool_choice_name: str,
        model: str | None = None,
    ) -> tuple[dict[str, Any], int, int]:
        target_tool = next((t for t in tools if t.get("name") == tool_choice_name), tools[0])
        cleaned_params = _clean_schema_for_gemini(target_tool.get("input_schema", {}))

        decl = {
            "name": tool_choice_name,
            "description": target_tool.get("description", ""),
            "parameters": cleaned_params,
        }

        gemini_model = model or self._settings.gemini_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={self._settings.gemini_api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "tools": [{"functionDeclarations": [decl]}],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "ANY",
                    "allowedFunctionNames": [tool_choice_name],
                }
            },
        }

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error("gemini_error_response", status_code=resp.status_code, text=resp.text)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error("gemini_call_failed", error=type(exc).__name__)
            raise IntegrationError("Gemini API call failed") from None

        candidates = data.get("candidates", [])
        if not candidates:
            raise IntegrationError("Gemini returned empty candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            func_call = part.get("functionCall")
            if func_call and func_call.get("name") == tool_choice_name:
                args = func_call.get("args", {})
                meta = data.get("usageMetadata", {})
                in_tok = meta.get("promptTokenCount", 0)
                out_tok = meta.get("candidatesTokenCount", 0)
                logger.info(
                    "llm_tokens", input_tokens=in_tok, output_tokens=out_tok, model=gemini_model
                )
                return args, in_tok, out_tok

        raise IntegrationError("Gemini did not return expected function call")
