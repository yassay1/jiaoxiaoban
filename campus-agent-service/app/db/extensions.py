from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def ensure_postgres_extensions(conn: AsyncConnection) -> None:
    """Enable PostgreSQL extensions required by the schema before table creation."""
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
