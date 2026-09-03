from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import router
from app.db import session_factory
from app.repository import fail_stale_runs
from app.schemas import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with session_factory() as session:
        await fail_stale_runs(session)
        await session.commit()
    yield


app = FastAPI(title="Books API", version="1.0.0", lifespan=lifespan, responses={422: {"model": ErrorResponse}})
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    detail = [{"field": ".".join(str(part) for part in item["loc"][1:]), "message": item["msg"]} for item in error.errors()]
    return JSONResponse(status_code=422, content=ErrorResponse.model_validate({"detail": detail}).model_dump())
