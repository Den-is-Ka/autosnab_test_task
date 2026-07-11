from typing import Any

import asyncpg

from app.schemas import QueryRequest, QueryStatus

HISTORY_COLUMNS = """
    id,
    cadastral_number,
    latitude,
    longitude,
    status,
    result,
    external_response,
    error_message,
    created_at,
    completed_at,
    duration_ms
"""


class RequestRepository:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def create_pending_request(self, query_data: QueryRequest) -> dict[str, Any]:
        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(
                f"""
                INSERT INTO requests_history (
                    cadastral_number,
                    latitude,
                    longitude,
                    status
                )
                VALUES ($1, $2, $3, $4)
                RETURNING {HISTORY_COLUMNS};
                """,
                query_data.cadastral_number,
                query_data.latitude,
                query_data.longitude,
                QueryStatus.PROCESSING.value,
            )
        return dict(row)

    async def mark_completed(
        self,
        request_id: int,
        result: bool,
        external_response: dict[str, Any],
        duration_ms: int,
    ) -> dict[str, Any]:
        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(
                f"""
                UPDATE requests_history
                SET
                    status = $2,
                    result = $3,
                    external_response = $4,
                    error_message = NULL,
                    completed_at = NOW(),
                    duration_ms = $5
                WHERE id = $1
                RETURNING {HISTORY_COLUMNS};
                """,
                request_id,
                QueryStatus.COMPLETED.value,
                result,
                external_response,
                duration_ms,
            )
        if row is None:
            raise LookupError(f"Request history record {request_id} not found")
        return dict(row)

    async def mark_failed(
        self,
        request_id: int,
        status: QueryStatus,
        error_message: str,
        duration_ms: int,
        external_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if status not in {QueryStatus.TIMEOUT, QueryStatus.FAILED}:
            raise ValueError("Failure status must be timeout or failed")

        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(
                f"""
                UPDATE requests_history
                SET
                    status = $2,
                    result = NULL,
                    external_response = $3,
                    error_message = $4,
                    completed_at = NOW(),
                    duration_ms = $5
                WHERE id = $1
                RETURNING {HISTORY_COLUMNS};
                """,
                request_id,
                status.value,
                external_response,
                error_message,
                duration_ms,
            )
        if row is None:
            raise LookupError(f"Request history record {request_id} not found")
        return dict(row)

    async def get_history(
        self,
        cadastral_number: str | None = None,
        status: QueryStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        parameters: list[Any] = []

        if cadastral_number is not None:
            parameters.append(cadastral_number)
            conditions.append(f"cadastral_number = ${len(parameters)}")
        if status is not None:
            parameters.append(status.value)
            conditions.append(f"status = ${len(parameters)}")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with self.db_pool.acquire() as connection:
            total = await connection.fetchval(
                f"SELECT COUNT(*) FROM requests_history {where_clause};",
                *parameters,
            )

            limit_position = len(parameters) + 1
            offset_position = len(parameters) + 2
            rows = await connection.fetch(
                f"""
                SELECT {HISTORY_COLUMNS}
                FROM requests_history
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ${limit_position} OFFSET ${offset_position};
                """,
                *parameters,
                limit,
                offset,
            )

        return [dict(row) for row in rows], int(total)

    async def get_by_id(self, request_id: int) -> dict[str, Any] | None:
        async with self.db_pool.acquire() as connection:
            row = await connection.fetchrow(
                f"""
                SELECT {HISTORY_COLUMNS}
                FROM requests_history
                WHERE id = $1;
                """,
                request_id,
            )
        return dict(row) if row is not None else None
