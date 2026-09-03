import asyncio
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.db import get_session
from app.schemas import BookOut, CategoryStats, Page, ScrapeRunOut
from app.scraper.runner import run_scrape

SessionDep = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter()
background_tasks: set[asyncio.Task[None]] = set()


@router.get("/books")
async def get_books(
    session: SessionDep,
    q: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    min_rating: Annotated[int | None, Query(ge=1, le=5)] = None,
    cursor: Annotated[int | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[BookOut]:
    books, next_cursor = await repository.list_books(
        session,
        q=q,
        category=category,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        cursor=cursor,
        limit=limit,
    )
    return Page[BookOut](items=books, next_cursor=next_cursor)


@router.get("/books/{upc}")
async def get_book(session: SessionDep, upc: str) -> BookOut:
    book = await repository.get_book(session, upc)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "book not found")
    return BookOut.model_validate(book)


@router.get("/categories")
async def get_categories(session: SessionDep) -> list[CategoryStats]:
    return [CategoryStats.model_validate(row) for row in await repository.list_categories(session)]


@router.get("/scrape/runs")
async def get_runs(session: SessionDep, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> list[ScrapeRunOut]:
    return [ScrapeRunOut.model_validate(run) for run in await repository.list_runs(session, limit)]


@router.get("/scrape/runs/{run_id}")
async def get_run(session: SessionDep, run_id: int) -> ScrapeRunOut:
    run = await repository.get_run(session, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "run not found")
    return ScrapeRunOut.model_validate(run)


@router.post("/scrape/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_run(session: SessionDep) -> ScrapeRunOut:
    if await repository.has_running(session):
        raise HTTPException(status.HTTP_409_CONFLICT, "scrape is already running")
    run = await repository.create_run(session)
    await session.commit()
    task = asyncio.create_task(run_scrape(run.id))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return ScrapeRunOut.model_validate(run)
