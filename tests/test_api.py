from dataclasses import replace
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.scraper.parser import parse_book
from tests.conftest import BOOK_URL


async def test_get_books_filtered_by_category_and_rating(client: AsyncClient, session: AsyncSession, book_html: str) -> None:
    book = parse_book(book_html, BOOK_URL)
    poetry = await repository.get_or_create_category(session, "Poetry")
    fiction = await repository.get_or_create_category(session, "Fiction")
    await repository.upsert_book(session, book, poetry)
    await repository.upsert_book(session, replace(book, upc="other", title="Other", rating=1, price=Decimal("5.00")), fiction)
    await session.commit()

    response = await client.get("/books", params={"category": "poetry", "min_rating": 3, "limit": 10})

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_cursor"] is None
    assert [item["title"] for item in payload["items"]] == ["A Light in the Attic"]
    assert payload["items"][0]["category"]["name"] == "Poetry"


async def test_invalid_query_param_returns_422(client: AsyncClient) -> None:
    response = await client.get("/books", params={"min_rating": 9})

    assert response.status_code == 422
    assert response.json() == {"detail": [{"field": "min_rating", "message": "Input should be less than or equal to 5"}]}
