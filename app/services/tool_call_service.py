import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ToolCall, utc_now


def _uuid() -> str:
    return str(uuid.uuid4())


async def log_tool_call_start(
    db: AsyncSession,
    agent_run_id: str,
    tool_name: str,
    input_params: dict | None = None,
) -> ToolCall:
    tc = ToolCall(
        id=_uuid(),
        agent_run_id=agent_run_id,
        tool_name=tool_name,
        input_params=input_params or {},
        status="pending",
    )
    db.add(tc)
    await db.flush()
    return tc


async def log_tool_call_end(
    db: AsyncSession,
    tool_call_id: str,
    output_result: dict | None = None,
    status: str = "success",
    error_message: str | None = None,
) -> None:
    from sqlalchemy import select
    result = await db.execute(select(ToolCall).where(ToolCall.id == tool_call_id))
    tc = result.scalar_one_or_none()
    if tc:
        tc.output_result = output_result or {}
        tc.status = status
        tc.error_message = error_message
        tc.finished_at = utc_now()
        await db.flush()
