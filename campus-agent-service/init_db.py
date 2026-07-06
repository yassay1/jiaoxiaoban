import asyncio

from sqlalchemy import text

from app.db.session import engine, Base
from app.db import models  # noqa: F401 - import all models before metadata creation
from app.db.extensions import ensure_postgres_extensions


async def init_database():
    """Initialize database extensions and tables."""
    print("Initializing database...")

    async with engine.begin() as conn:
        await ensure_postgres_extensions(conn)
        await conn.run_sync(Base.metadata.create_all)

    print("Database tables created successfully.")

    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"\nCreated tables ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")


if __name__ == "__main__":
    asyncio.run(init_database())
