from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api import agent_runs as agent_runs_api
from app.services import agent_run_service


@pytest.mark.asyncio
async def test_list_runs_returns_recent_memory_runs(monkeypatch):
    monkeypatch.setattr(agent_run_service, "_run_store", {})
    first = await agent_run_service.create_run(None, "assistant_graph", {"q": "old"}, conversation_id="c1")
    second = await agent_run_service.create_run(None, "community_graph", {"q": "new"}, conversation_id="c2")
    await agent_run_service.update_run(first, status="completed", output_data={"ok": True})
    await agent_run_service.update_run(second, status="failed", error="boom")

    runs = await agent_run_service.list_runs(limit=10)
    failed = await agent_run_service.list_runs(limit=10, status="failed")
    community = await agent_run_service.list_runs(limit=10, graph_name="community_graph")

    assert [run["run_id"] for run in runs] == [second, first]
    assert runs[0]["conversation_id"] == "c2"
    assert failed == [runs[0]]
    assert community == [runs[0]]


class _RunRows:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


@pytest.mark.asyncio
async def test_list_runs_merges_memory_fallback_when_db_is_available(monkeypatch):
    monkeypatch.setattr(agent_run_service, "_run_store", {})
    memory_run_id = await agent_run_service.create_run(None, "professional_agent_graph", {"q": "memory"}, conversation_id="c-memory")
    await agent_run_service.update_run(memory_run_id, status="failed", error="memory boom")

    db_run = MagicMock()
    db_run.id = "db-run-001"
    db_run.conversation_id = "c-db"
    db_run.graph_name = "assistant_graph"
    db_run.input_data = {"q": "db"}
    db_run.output_data = {"ok": True}
    db_run.status = "completed"
    db_run.error_message = None
    db_run.started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_run.finished_at = datetime.now(timezone.utc) - timedelta(minutes=4)

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_RunRows([db_run]), _RunRows([])])

    runs = await agent_run_service.list_runs(db=db, limit=10)
    failed = await agent_run_service.list_runs(db=db, limit=10, status="failed")

    assert {run["run_id"] for run in runs} == {"db-run-001", memory_run_id}
    assert failed == [next(run for run in runs if run["run_id"] == memory_run_id)]

@pytest.mark.asyncio
async def test_api_list_agent_runs_passes_filters(monkeypatch):
    captured = {}

    async def fake_list_runs(**kwargs):
        captured.update(kwargs)
        return [{"run_id": "run-001", "status": "completed"}]

    monkeypatch.setattr(agent_runs_api, "list_runs", fake_list_runs)
    db = MagicMock()

    result = await agent_runs_api.list_agent_runs(limit=5, status="completed", graphName="assistant_graph", db=db)

    assert result == {"runs": [{"run_id": "run-001", "status": "completed"}], "total": 1}
    assert captured == {"db": db, "limit": 5, "status": "completed", "graph_name": "assistant_graph"}


@pytest.mark.asyncio
async def test_api_get_agent_run_uses_db(monkeypatch):
    captured = {}

    async def fake_get_run(run_id, db=None):
        captured["run_id"] = run_id
        captured["db"] = db
        return {"run_id": run_id, "status": "completed"}

    monkeypatch.setattr(agent_runs_api, "get_run", fake_get_run)
    db = MagicMock()

    result = await agent_runs_api.get_agent_run("run-001", db=db)

    assert result == {"run_id": "run-001", "status": "completed"}
    assert captured == {"run_id": "run-001", "db": db}