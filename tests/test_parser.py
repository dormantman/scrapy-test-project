from decimal import Decimal

from app.scraper.parser import parse_book, parse_catalogue
from tests.conftest import BOOK_URL, CATALOGUE_URL


def test_parse_book(book_html: str) -> None:
    book = parse_book(book_html, BOOK_URL)

    assert book.upc == "a897fe39b1053632"
    assert book.title == "A Light in the Attic"
    assert book.price == Decimal("51.77")
    assert book.availability == 22
    assert book.rating == 3
    assert book.category == "Poetry"
    assert book.description.startswith("It's hard to imagine a world without A Light in the Attic.")
    assert book.url == BOOK_URL
    assert book.image_url == "https://books.toscrape.com/media/cache/fe/72/fe72f0532301ec28892ae79a629a293c.jpg"


def test_parse_catalogue(catalogue_html: str) -> None:
    books, next_page = parse_catalogue(catalogue_html, CATALOGUE_URL)

    assert len(books) == 20
    assert books[0] == BOOK_URL
    assert next_page == "https://books.toscrape.com/catalogue/page-2.html"
