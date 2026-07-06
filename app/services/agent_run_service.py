import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AgentRun, utc_now


def _uuid() -> str:
    return str(uuid.uuid4())


async def create_run(
    db: AsyncSession | None,
    graph_name: str,
    input_data: dict,
    conversation_id: str | None = None,
) -> str:
    run_id = _uuid()
    if db is not None:
        run = AgentRun(
            id=run_id,
            conversation_id=conversation_id,
            graph_name=graph_name,
            input_data=input_data,
            status="running",
        )
        db.add(run)
        await db.flush()
    # 同时保留内存存储作为 fallback（当没有 DB session 时）
    _cleanup_run_store()
    _run_store[run_id] = {
        "run_id": run_id,
        "conversation_id": conversation_id,
        "graph_name": graph_name,
        "input_data": input_data,
        "output_data": None,
        "status": "running",
        "error_message": None,
        "started_at": utc_now().isoformat(),
        "finished_at": None,
    }
    return run_id


async def update_run(
    run_id: str,
    db: AsyncSession | None = None,
    output_data: dict | None = None,
    status: str = "completed",
    error: str | None = None,
) -> None:
    if db is not None:
        result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if run:
            run.output_data = output_data
            run.status = status
            run.error_message = error
            run.finished_at = utc_now()
            await db.flush()
    if run_id in _run_store:
        _run_store[run_id]["status"] = status
        _run_store[run_id]["output_data"] = output_data
        _run_store[run_id]["error_message"] = error
        _run_store[run_id]["finished_at"] = utc_now().isoformat()


async def get_run(run_id: str, db: AsyncSession | None = None) -> dict | None:
    if db is not None:
        result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if run:
            return {
                "run_id": run.id,
                "conversation_id": run.conversation_id,
                "graph_name": run.graph_name,
                "input_data": run.input_data,
                "output_data": run.output_data,
                "status": run.status,
                "error_message": run.error_message,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            }
    return _run_store.get(run_id)



async def list_runs(
    db: AsyncSession | None = None,
    limit: int = 20,
    status: str | None = None,
    graph_name: str | None = None,
) -> list[dict]:
    safe_limit = max(1, min(limit, 100))
    runs: list[dict] = []
    seen_run_ids: set[str] = set()
    if db is not None:
        stmt = select(AgentRun)
        if status:
            stmt = stmt.where(AgentRun.status == status)
        if graph_name:
            stmt = stmt.where(AgentRun.graph_name == graph_name)
        stmt = stmt.order_by(AgentRun.started_at.desc()).limit(safe_limit)
        rows = (await db.execute(stmt)).scalars().all()
        for run in rows:
            run_data = {
                "run_id": run.id,
                "conversation_id": run.conversation_id,
                "graph_name": run.graph_name,
                "input_data": run.input_data,
                "output_data": run.output_data,
                "status": run.status,
                "error_message": run.error_message,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            }
            runs.append(run_data)
            seen_run_ids.add(run.id)

    memory_runs = list(_run_store.values())
    if status:
        memory_runs = [run for run in memory_runs if run.get("status") == status]
    if graph_name:
        memory_runs = [run for run in memory_runs if run.get("graph_name") == graph_name]
    runs.extend(run for run in memory_runs if run.get("run_id") not in seen_run_ids)
    return sorted(runs, key=lambda run: run.get("started_at") or "", reverse=True)[:safe_limit]

_run_store: dict[str, dict] = {}
_MAX_RUN_STORE_SIZE = 10_000


def _cleanup_run_store() -> None:
    """超过上限时清理最早的一半记录，防止内存无限增长."""
    if len(_run_store) > _MAX_RUN_STORE_SIZE:
        remove_count = len(_run_store) // 2
        keys_to_remove = list(_run_store.keys())[:remove_count]
        for key in keys_to_remove:
            del _run_store[key]
