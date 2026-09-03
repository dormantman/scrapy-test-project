from dataclasses import replace
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.models import Book
from app.scraper.parser import parse_book
from tests.conftest import BOOK_URL


async def test_upsert_book_is_idempotent(session: AsyncSession, book_html: str) -> None:
    book = parse_book(book_html, BOOK_URL)
    category_id = await repository.get_or_create_category(session, book.category)

    assert await repository.upsert_book(session, book, category_id) is True
    await session.commit()

    assert await repository.upsert_book(session, replace(book, price=Decimal("10.00")), category_id) is False
    await session.commit()

    assert await session.scalar(select(func.count()).select_from(Book)) == 1
    stored = await repository.get_book(session, book.upc)
    assert stored.price == Decimal("10.00")
    assert stored.updated_at > stored.created_at
