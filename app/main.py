import asyncio
import logging
import random
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request

from app.config import settings
from app.crud import RequestRepository
from app.database import (
    apply_migrations,
    check_database,
    close_db,
    connect_to_db,
    get_pool,
)
from app.external_client import ExternalServiceClient
from app.schemas import (
    CADASTRAL_NUMBER_PATTERN,
    ErrorDetail,
    HistoryItem,
    HistoryResponse,
    QueryRequest,
    QueryStatus,
    ResultResponse,
)
from app.services import QueryProcessingError, QueryService

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    await apply_migrations()
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.external_timeout_seconds)
    )
    app.state.external_client = ExternalServiceClient(app.state.http_client)
    try:
        yield
    finally:
        await app.state.http_client.aclose()
        await close_db()


async def get_repository() -> RequestRepository:
    return RequestRepository(await get_pool())


async def get_external_client(request: Request) -> ExternalServiceClient:
    client = getattr(request.app.state, "external_client", None)
    if client is None:
        raise RuntimeError("External service client is not initialized")
    return client


async def emulate_external_result() -> dict[str, bool]:
    delay = random.randint(
        settings.emulator_min_delay_seconds,
        settings.emulator_max_delay_seconds,
    )
    await asyncio.sleep(delay)
    return {"result": random.choice([True, False])}


@router.get("/ping", summary="Проверить, что сервер запущен")
async def ping() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health", summary="Проверить сервер и подключение к PostgreSQL")
async def health() -> dict[str, str]:
    try:
        database_ok = await check_database(await get_pool())
    except Exception as error:
        logger.warning("Database health check failed: %s", error)
        raise HTTPException(status_code=503, detail="Database is unavailable") from error
    return {"status": "ok", "database": "connected" if database_ok else "unavailable"}


@router.get(
    "/result",
    response_model=ResultResponse,
    summary="Эмуляция внешнего сервера (совместимый GET)",
)
async def result_get() -> dict[str, bool]:
    return await emulate_external_result()


@router.post(
    "/result",
    response_model=ResultResponse,
    summary="Эмуляция внешнего сервера",
)
async def result_post(_: QueryRequest) -> dict[str, bool]:
    return await emulate_external_result()


@router.post(
    "/query",
    response_model=HistoryItem,
    summary="Отправить данные на внешний сервер и сохранить результат",
    responses={
        502: {"model": ErrorDetail, "description": "Ошибка внешнего сервера"},
        504: {"model": ErrorDetail, "description": "Тайм-аут внешнего сервера"},
    },
)
async def query(
    query_data: QueryRequest,
    repository: Annotated[RequestRepository, Depends(get_repository)],
    external_client: Annotated[ExternalServiceClient, Depends(get_external_client)],
) -> dict:
    service = QueryService(repository, external_client)
    try:
        return await service.execute(query_data)
    except QueryProcessingError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={
                "request_id": error.request_id,
                "status": error.status.value,
                "message": error.message,
            },
        ) from error


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Получить историю запросов",
)
async def history(
    repository: Annotated[RequestRepository, Depends(get_repository)],
    cadastral_number: str | None = Query(
        default=None,
        min_length=7,
        max_length=100,
        pattern=CADASTRAL_NUMBER_PATTERN,
        description="Фильтр по кадастровому номеру",
    ),
    status: QueryStatus | None = Query(default=None, description="Фильтр по статусу"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> HistoryResponse:
    items, total = await repository.get_history(
        cadastral_number=cadastral_number,
        status=status,
        limit=limit,
        offset=offset,
    )
    return HistoryResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/history/{request_id}",
    response_model=HistoryItem,
    summary="Получить один запрос из истории",
)
async def history_item(
    request_id: int,
    repository: Annotated[RequestRepository, Depends(get_repository)],
) -> dict:
    record = await repository.get_by_id(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="History record not found")
    return record


def create_app(*, enable_lifespan: bool = True) -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Асинхронный сервис для обработки кадастровых запросов, "
            "сохранения результата и ошибок внешнего сервера в PostgreSQL."
        ),
        version=settings.app_version,
        lifespan=lifespan if enable_lifespan else None,
    )
    application.include_router(router)
    return application


app = create_app()
