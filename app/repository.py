from dataclasses import asdict
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import Row, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book, Category, RunStatus, ScrapeRun
from app.scraper.parser import ParsedBook


async def get_or_create_category(session: AsyncSession, name: str) -> int:
    stmt = insert(Category).values(name=name).on_conflict_do_nothing(index_elements=[Category.name]).returning(Category.id)
    return await session.scalar(stmt) or await session.scalar(select(Category.id).where(Category.name == name))


async def upsert_book(session: AsyncSession, book: ParsedBook, category_id: int) -> bool:
    values = asdict(book) | {"category_id": category_id}
    values.pop("category")
    stmt = insert(Book).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Book.upc],
        set_={key: stmt.excluded[key] for key in values} | {"updated_at": func.now()},
    ).returning(text("xmax = 0"))
    return bool(await session.scalar(stmt))


async def get_book(session: AsyncSession, upc: str) -> Book | None:
    return await session.scalar(select(Book).where(Book.upc == upc))


async def list_books(
    session: AsyncSession,
    *,
    q: str | None,
    category: str | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    min_rating: int | None,
    cursor: int | None,
    limit: int,
) -> tuple[Sequence[Book], int | None]:
    stmt = select(Book).order_by(Book.id).limit(limit + 1)
    if q:
        stmt = stmt.where(Book.title.ilike(f"%{q}%"))
    if category:
        stmt = stmt.join(Book.category).where(Category.name.ilike(category))
    if min_price is not None:
        stmt = stmt.where(Book.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Book.price <= max_price)
    if min_rating is not None:
        stmt = stmt.where(Book.rating >= min_rating)
    if cursor is not None:
        stmt = stmt.where(Book.id > cursor)
    books = (await session.scalars(stmt)).unique().all()
    return books[:limit], books[limit - 1].id if len(books) > limit else None


async def list_categories(session: AsyncSession) -> Sequence[Row[Any]]:
    stmt = (
        select(Category.id, Category.name, func.count(Book.id).label("books_count"))
        .join(Book, Book.category_id == Category.id, isouter=True)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    return (await session.execute(stmt)).all()


async def create_run(session: AsyncSession) -> ScrapeRun:
    run = ScrapeRun(status=RunStatus.RUNNING)
    session.add(run)
    await session.flush()
    return run


async def get_run(session: AsyncSession, run_id: int) -> ScrapeRun | None:
    return await session.get(ScrapeRun, run_id)


async def list_runs(session: AsyncSession, limit: int) -> Sequence[ScrapeRun]:
    return (await session.scalars(select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(limit))).all()


async def has_running(session: AsyncSession) -> bool:
    return bool(await session.scalar(select(ScrapeRun.id).where(ScrapeRun.status == RunStatus.RUNNING).limit(1)))


async def fail_stale_runs(session: AsyncSession) -> None:
    await session.execute(
        update(ScrapeRun)
        .where(ScrapeRun.status == RunStatus.RUNNING)
        .values(status=RunStatus.FAILED, finished_at=func.now(), message="interrupted by restart")
    )
