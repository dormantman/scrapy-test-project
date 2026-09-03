from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
BOOK_URL = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"


@pytest.fixture(scope="session")
def book_html() -> str:
    return (FIXTURES / "book.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def catalogue_html() -> str:
    return (FIXTURES / "catalogue.html").read_text(encoding="utf-8")
