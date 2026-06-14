import asyncio
from pathlib import Path

import asyncpg

from app.config import settings


pool: asyncpg.Pool | None = None


async def connect_to_db() -> None:
    global pool

    for attempt in range(30):
        try:
            pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=1,
                max_size=10,
            )
            return
        except Exception:
            if attempt == 29:
                raise
            await asyncio.sleep(1)


async def close_db() -> None:
    global pool

    if pool is not None:
        await pool.close()
        pool = None


async def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool is not initialized")
    return pool


async def apply_migrations() -> None:
    db_pool = await get_pool()

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    async with db_pool.acquire() as connection:
        async with connection.transaction():
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
                    """
                    SELECT 1
                    FROM schema_migrations
                    WHERE filename = $1;
                    """,
                    migration_file.name,
                )

                if already_applied:
                    continue

                sql = migration_file.read_text(encoding="utf-8")
                await connection.execute(sql)

                await connection.execute(
                    """
                    INSERT INTO schema_migrations (filename)
                    VALUES ($1);
                    """,
                    migration_file.name,
                )
