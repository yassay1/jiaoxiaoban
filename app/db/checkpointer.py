"""LangGraph PostgresSaver 管理。"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config.settings import get_settings

_checkpointer: AsyncPostgresSaver | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer
    if _checkpointer is None:
        settings = get_settings()
        conn_string = (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        _checkpointer = AsyncPostgresSaver.from_conn_string(conn_string)
        await _checkpointer.setup()
    return _checkpointer


async def close_checkpointer() -> None:
    global _checkpointer
    if _checkpointer:
        await _checkpointer.close()
        _checkpointer = None
