"""Simple poll loop — no Celery. Run as ``python -m backend.tasks.poller``."""

from __future__ import annotations

import asyncio

import structlog

from backend.config import get_settings
from backend.db import create_engine, session_factory
from backend.integrations.razorpay import RazorpayClient
from backend.integrations.whatsapp import WhatsAppSender
from backend.llm.client import AnthropicClient
from backend.llm.message_drafter import MessageDrafter
from backend.llm.reply_parser import ReplyParser
from backend.logging_util import configure_logging
from backend.tasks.aging_checker import run_aging_check
from backend.tasks.nudge_executor import run_nudge_cycle
from backend.tasks.promise_checker import run_promise_check
from backend.tasks.reply_processor import process_unparsed_inbounds

POLL_INTERVAL_SECONDS = 30

logger = structlog.get_logger("duebot.poller")


async def run_once() -> None:
    """One aging → promise → nudge → reply pass."""
    settings = get_settings()
    engine = create_engine(settings)
    factory = session_factory(engine)
    client = AnthropicClient(settings)
    drafter = MessageDrafter(client)
    parser = ReplyParser(client)
    razorpay = RazorpayClient(settings)
    whatsapp = WhatsAppSender(settings)
    async with factory() as session:
        aged = await run_aging_check(session)
        promised = await run_promise_check(session)
        nudged = await run_nudge_cycle(
            session, drafter=drafter, razorpay=razorpay, whatsapp=whatsapp
        )
        replies = await process_unparsed_inbounds(session, parser)
        await session.commit()
        logger.info(
            "poll_cycle",
            aged=aged,
            promised=promised,
            nudged=nudged,
            replies=replies,
        )
    await engine.dispose()


async def main() -> None:
    """Loop until cancelled. Transient errors in a single cycle are logged and skipped."""
    settings = get_settings()
    configure_logging(settings.log_level)
    while True:
        try:
            await run_once()
        except asyncio.CancelledError:
            raise  # propagate shutdown signal
        except Exception:
            logger.exception("poll_cycle_error")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
