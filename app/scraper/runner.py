import asyncio
import logging
from collections import Counter

import httpx
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.config import settings
from app.db import session_factory
from app.models import RunStatus, ScrapeRun
from app.scraper.client import Fetcher
from app.scraper.parser import ParsedBook, parse_book, parse_catalogue

logger = logging.getLogger(__name__)


async def collect_book_urls(fetcher: Fetcher, start_url: str) -> list[str]:
    urls: list[str] = []
    page_url: str | None = start_url
    while page_url:
        books, page_url = parse_catalogue(await fetcher.get(page_url), page_url)
        urls.extend(books)
    return urls


async def load_book(fetcher: Fetcher, url: str) -> ParsedBook:
    return parse_book(await fetcher.get(url), url)


async def scrape(session: AsyncSession, run: ScrapeRun) -> None:
    stats: Counter[str] = Counter()
    categories: dict[str, int] = {}
    async with httpx.AsyncClient(timeout=settings.scraper_timeout, follow_redirects=True) as client:
        fetcher = Fetcher(client, settings.scraper_concurrency, settings.scraper_retries, settings.scraper_backoff)
        urls = await collect_book_urls(fetcher, settings.scraper_base_url)
        tasks = [asyncio.create_task(load_book(fetcher, url)) for url in urls]
        for task in asyncio.as_completed(tasks):
            try:
                book = await task
            except Exception:
                logger.exception("failed to load book")
                stats["errors"] += 1
                continue
            if book.category not in categories:
                categories[book.category] = await repository.get_or_create_category(session, book.category)
            created = await repository.upsert_book(session, book, categories[book.category])
            stats["created" if created else "updated"] += 1
            stats["processed"] += 1
            if stats["processed"] % settings.scraper_commit_every == 0:
                await save(session, run, stats)
    await save(session, run, stats)


async def save(session: AsyncSession, run: ScrapeRun, stats: Counter[str]) -> None:
    run.processed, run.created, run.updated, run.errors = (stats[key] for key in ("processed", "created", "updated", "errors"))
    await session.commit()


async def run_scrape(run_id: int) -> None:
    async with session_factory() as session:
        run = await repository.get_run(session, run_id)
        try:
            await scrape(session, run)
            run.status = RunStatus.SUCCESS
        except Exception as error:
            await session.rollback()
            logger.exception("scrape run %s failed", run_id)
            run.status = RunStatus.FAILED
            run.message = f"{type(error).__name__}: {error}"
        run.finished_at = func.now()
        await session.commit()
