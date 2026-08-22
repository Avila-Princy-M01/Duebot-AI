"""Seed the database from the synthetic generator."""

from __future__ import annotations

import argparse
import asyncio

from backend.config import get_settings
from backend.data.seed import seed_from_generator
from backend.db import create_engine, session_factory
from backend.logging_util import configure_logging


async def _run(num_invoices: int, seed: int) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    if settings.database_url.startswith("sqlite"):
        from backend.db import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    factory = session_factory(engine)
    async with factory() as session:
        counts = await seed_from_generator(session, num_invoices=num_invoices, seed=seed)
        await session.commit()
        print(counts)
    await engine.dispose()


def main() -> None:
    """CLI."""
    parser = argparse.ArgumentParser(description="Seed DueBot from the synthetic generator.")
    parser.add_argument("--num-invoices", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    asyncio.run(_run(args.num_invoices, args.seed))


if __name__ == "__main__":
    main()
