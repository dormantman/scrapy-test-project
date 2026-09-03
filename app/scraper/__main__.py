import asyncio
import logging

from app import repository
from app.db import session_factory
from app.scraper.runner import run_scrape


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with session_factory() as session:
        run = await repository.create_run(session)
        await session.commit()
    await run_scrape(run.id)


asyncio.run(main())
