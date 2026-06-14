import asyncio
import random
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query

from app.config import settings
from app.crud import create_request_history, get_request_history
from app.database import apply_migrations, close_db, connect_to_db, get_pool
from app.schemas import HistoryItem, QueryRequest, ResultResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    await apply_migrations()

    yield

    await close_db()


app = FastAPI(
    title="АВТОСНАБ Test Task API",
    description="Сервис для проверки кадастрового номера, широты и долготы через эмуляцию внешнего сервера.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/ping")
async def ping() -> dict:
    return {"status": "ok"}


@app.get("/result", response_model=ResultResponse)
async def result() -> dict:
    # По ТЗ внешний сервер может обрабатывать запрос до 60 секунд.
    # Для удобства проверки используется задержка от 1 до 5 секунд.
    await asyncio.sleep(random.randint(1, 5))

    return {"result": random.choice([True, False])}


async def call_external_server() -> bool:
    try:
        async with httpx.AsyncClient(timeout=65.0) as client:
            response = await client.get(settings.external_server_url)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail=f"External server error: {error}",
        )

    data = response.json()

    if "result" not in data or not isinstance(data["result"], bool):
        raise HTTPException(
            status_code=502,
            detail="External server returned invalid response",
        )

    return data["result"]


@app.post("/query", response_model=HistoryItem)
async def query(query_data: QueryRequest) -> dict:
    external_result = await call_external_server()

    db_pool = await get_pool()

    saved_record = await create_request_history(
        db_pool=db_pool,
        query_data=query_data,
        result=external_result,
    )

    return saved_record


@app.get("/history", response_model=list[HistoryItem])
async def history(
    cadastral_number: str | None = Query(
        default=None,
        description="Фильтр по кадастровому номеру",
    ),
) -> list[dict]:
    db_pool = await get_pool()

    return await get_request_history(
        db_pool=db_pool,
        cadastral_number=cadastral_number,
    )
