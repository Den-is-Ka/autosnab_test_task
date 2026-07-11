import asyncio
import random

from fastapi import FastAPI

from app.config import settings
from app.schemas import QueryRequest, ResultResponse

app = FastAPI(
    title="АВТОСНАБ External Server Emulator",
    description="Отдельный сервис, эмулирующий внешний сервер с задержкой до 60 секунд.",
    version="1.0.0",
)


async def emulate() -> dict[str, bool]:
    delay = random.randint(
        settings.emulator_min_delay_seconds,
        settings.emulator_max_delay_seconds,
    )
    await asyncio.sleep(delay)
    return {"result": random.choice([True, False])}


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/result", response_model=ResultResponse)
async def result_get() -> dict[str, bool]:
    return await emulate()


@app.post("/result", response_model=ResultResponse)
async def result_post(_: QueryRequest) -> dict[str, bool]:
    return await emulate()
