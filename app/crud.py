import asyncpg

from app.schemas import QueryRequest


async def create_request_history(
    db_pool: asyncpg.Pool,
    query_data: QueryRequest,
    result: bool,
) -> dict:
    async with db_pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            INSERT INTO requests_history (
                cadastral_number,
                latitude,
                longitude,
                result
            )
            VALUES ($1, $2, $3, $4)
            RETURNING
                id,
                cadastral_number,
                latitude,
                longitude,
                result,
                created_at;
            """,
            query_data.cadastral_number,
            query_data.latitude,
            query_data.longitude,
            result,
        )

    return dict(row)


async def get_request_history(
    db_pool: asyncpg.Pool,
    cadastral_number: str | None = None,
) -> list[dict]:
    async with db_pool.acquire() as connection:
        if cadastral_number:
            rows = await connection.fetch(
                """
                SELECT
                    id,
                    cadastral_number,
                    latitude,
                    longitude,
                    result,
                    created_at
                FROM requests_history
                WHERE cadastral_number = $1
                ORDER BY created_at DESC;
                """,
                cadastral_number,
            )
        else:
            rows = await connection.fetch(
                """
                SELECT
                    id,
                    cadastral_number,
                    latitude,
                    longitude,
                    result,
                    created_at
                FROM requests_history
                ORDER BY created_at DESC;
                """
            )

    return [dict(row) for row in rows]
