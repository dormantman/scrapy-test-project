from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.models import RunStatus

ItemT = TypeVar("ItemT")


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    upc: str
    title: str
    price: Decimal
    availability: int
    rating: int
    category: CategoryOut
    description: str | None
    url: str
    image_url: str
    updated_at: datetime


class Page(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    next_cursor: int | None


class ScrapeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    processed: int
    created: int
    updated: int
    errors: int
    message: str | None


class ErrorItem(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    detail: list[ErrorItem]


class CategoryStats(CategoryOut):
    books_count: int
