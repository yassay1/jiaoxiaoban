from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.agent_run_service import get_run, list_runs

router = APIRouter(prefix="/api/agent-runs", tags=["agent-runs"])


@router.get("")
async def list_agent_runs(
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    graphName: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    runs = await list_runs(db=db, limit=limit, status=status, graph_name=graphName)
    return {"runs": runs, "total": len(runs)}


@router.get("/{run_id}")
async def get_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await get_run(run_id, db=db)
    if run is None:
        return {"error": "Agent 运行记录未找到", "run_id": run_id}
    return run