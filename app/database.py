import asyncio
import json
import logging
from pathlib import Path

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)
pool: asyncpg.Pool | None = None


async def _initialize_connection(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await connection.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def connect_to_db() -> None:
    global pool

    for attempt in range(1, settings.database_connect_retries + 1):
        try:
            pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=1,
                max_size=10,
                command_timeout=settings.external_timeout_seconds + 10,
                init=_initialize_connection,
            )
            logger.info("Database connection pool created")
            return
        except (OSError, asyncpg.PostgresError) as error:
            if attempt == settings.database_connect_retries:
                logger.exception("Database connection failed after all retries")
                raise
            logger.warning(
                "Database is not ready, retrying (%s/%s): %s",
                attempt,
                settings.database_connect_retries,
                error,
            )
            await asyncio.sleep(settings.database_retry_delay_seconds)


async def close_db() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None
        logger.info("Database connection pool closed")


async def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool is not initialized")
    return pool


async def check_database(db_pool: asyncpg.Pool) -> bool:
    async with db_pool.acquire() as connection:
        return await connection.fetchval("SELECT 1;") == 1


async def apply_migrations() -> None:
    db_pool = await get_pool()
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    async with db_pool.acquire() as connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        for migration_file in migration_files:
            already_applied = await connection.fetchval(
                "SELECT 1 FROM schema_migrations WHERE filename = $1;",
                migration_file.name,
            )
            if already_applied:
                continue

            sql = migration_file.read_text(encoding="utf-8")
            async with connection.transaction():
                await connection.execute(sql)
                await connection.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1);",
                    migration_file.name,
                )
            logger.info("Applied migration: %s", migration_file.name)
