import re
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


@dataclass(frozen=True, slots=True)
class ParsedBook:
    upc: str
    title: str
    price: Decimal
    availability: int
    rating: int
    category: str
    description: str | None
    url: str
    image_url: str


def parse_catalogue(html: str, url: str) -> tuple[list[str], str | None]:
    tree = HTMLParser(html)
    books = [urljoin(url, node.attributes["href"]) for node in tree.css("article.product_pod h3 a")]
    next_page = tree.css_first("li.next a")
    return books, urljoin(url, next_page.attributes["href"]) if next_page else None


def parse_book(html: str, url: str) -> ParsedBook:
    tree = HTMLParser(html)
    info = {row.css_first("th").text(strip=True): row.css_first("td").text(strip=True) for row in tree.css("table tr")}
    description = tree.css_first("#product_description ~ p")
    return ParsedBook(
        upc=info["UPC"],
        title=tree.css_first(".product_main h1").text(strip=True),
        price=Decimal(re.sub(r"[^\d.]", "", info["Price (incl. tax)"])),
        availability=int(re.search(r"\d+", info["Availability"]).group()),
        rating=RATINGS[tree.css_first(".product_main .star-rating").attributes["class"].split()[-1]],
        category=tree.css("ul.breadcrumb li")[2].text(strip=True),
        description=description.text(strip=True) if description else None,
        url=url,
        image_url=urljoin(url, tree.css_first("#product_gallery img").attributes["src"]),
    )
