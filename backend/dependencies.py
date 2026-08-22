"""FastAPI dependency injection — sessions, settings, clients."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.config import Settings, get_settings
from backend.integrations.email_sender import EmailSender
from backend.integrations.razorpay import RazorpayClient
from backend.integrations.whatsapp import WhatsAppSender
from backend.llm.client import AnthropicClient
from backend.llm.message_drafter import MessageDrafter
from backend.llm.reply_parser import ReplyParser


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async session from the app factory."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def settings_dep() -> Settings:
    """Settings singleton."""
    return get_settings()


def razorpay_client(settings: Settings = Depends(settings_dep)) -> RazorpayClient:
    """Razorpay (or mock) client."""
    return RazorpayClient(settings)


def whatsapp_sender(settings: Settings = Depends(settings_dep)) -> WhatsAppSender:
    """WhatsApp sender (simulated by default)."""
    return WhatsAppSender(settings)


def email_sender(settings: Settings = Depends(settings_dep)) -> EmailSender:
    """Email fallback sender."""
    return EmailSender(settings)


def anthropic_client(settings: Settings = Depends(settings_dep)) -> AnthropicClient:
    """Claude client wrapper."""
    return AnthropicClient(settings)


def reply_parser(client: AnthropicClient = Depends(anthropic_client)) -> ReplyParser:
    """Reply parser."""
    return ReplyParser(client)


def message_drafter(client: AnthropicClient = Depends(anthropic_client)) -> MessageDrafter:
    """Message drafter."""
    return MessageDrafter(client)
