import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://books:books@localhost:5432/books_test")
FIXTURES = Path(__file__).parent / "fixtures"
BOOK_URL = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"


@pytest.fixture(scope="session")
def book_html() -> str:
    return (FIXTURES / "book.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def catalogue_html() -> str:
    return (FIXTURES / "catalogue.html").read_text(encoding="utf-8")


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(session):
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
