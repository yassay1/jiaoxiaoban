import pytest


@pytest.mark.asyncio
async def test_mock_search_auto_seeds_default_tasks():
    from app.services.mock_community_adapter import HelpTaskSearchQuery, search_help_tasks

    results = await search_help_tasks(HelpTaskSearchQuery(keyword="快递"))
    assert any("快递" in item.title or "快递" in item.description for item in results)


@pytest.mark.asyncio
async def test_delete_flow_matches_task_id(monkeypatch):
    from app.graphs.community_agent_subgraph import node_delete_task_execute

    async def fake_delete(external_user_id: str, task_id: str):
        class Result:
            status = "deleted"
        return Result()

    monkeypatch.setattr("app.graphs.community_agent_subgraph.delete_help_task", fake_delete)
    monkeypatch.setattr(
        "app.graphs.community_agent_subgraph.interrupt",
        lambda payload: {"decision": "approve"},
    )

    state = {
        "external_user_id": "u001",
        "user_message": "帮我删掉 task_abc123",
        "search_results": [
            {
                "task_id": "task_abc123",
                "title": "帮忙取快递",
                "description": "东区快递站",
                "category": "生活帮助",
                "status": "published",
                "created_at": "2026-07-04T00:00:00Z",
            }
        ],
        "actions": [],
    }

    result = await node_delete_task_execute(state)
    assert "已成功删除" in result["response"]
    assert result["actions"] == [{"type": "task_deleted", "task_id": "task_abc123"}]


@pytest.mark.asyncio
async def test_real_mode_attempts_http_call(monkeypatch):
    """Phase 5 P8: real mode now attempts actual HTTP calls instead of NotImplementedError."""
    import app.services.community_service_adapter as adapter
    from app.services.community_client import CommunityServiceError, HelpTaskSearchQuery

    monkeypatch.setattr(adapter, "_USE_MOCK", False)

    # Mock the real HTTP client at its import location inside each adapter function
    import app.services.community_client as client_module
    original = client_module.community_client
    monkeypatch.setattr(client_module, "community_client", type("Fake", (), {
        "search_tasks": staticmethod(lambda q: (_ for _ in ()).throw(CommunityServiceError("unreachable"))),
    })())

    with pytest.raises(CommunityServiceError):
        await adapter.search_help_tasks(HelpTaskSearchQuery(keyword="拼车"))

    monkeypatch.setattr(client_module, "community_client", original)


@pytest.mark.asyncio
async def test_local_adapter_publishes_to_community_posts(monkeypatch):
    import app.services.community_service_adapter as adapter
    import app.services.community_post_service as post_service

    captured = {}

    async def fake_with_local_session(fn):
        return await fn("db-session")

    async def fake_create_post(db, req, external_user_id):
        captured.update({"db": db, "req": req, "external_user_id": external_user_id})

        class Post:
            id = "post-001"
            taskStatus = "待接单"

        return Post()

    monkeypatch.setattr(adapter, "_USE_MOCK", False)
    monkeypatch.setattr(adapter, "_USE_LOCAL", True)
    monkeypatch.setattr(adapter, "_with_local_session", fake_with_local_session)
    monkeypatch.setattr(post_service, "create_post", fake_create_post)

    result = await adapter.publish_help_task(
        title="找人取快递",
        description="东区快递站",
        external_user_id="u100",
        category="生活帮助",
        idempotency_key="draft_001",
    )

    assert result.task_id == "post-001"
    assert result.status == "待接单"
    assert captured["db"] == "db-session"
    assert captured["external_user_id"] == "u100"
    assert captured["req"].title == "找人取快递"
    assert captured["req"].type == "任务帖子"
    assert captured["req"].taskCategory == "生活帮助"
    assert captured["req"].sourceAgent == "community_agent:draft_001"


@pytest.mark.asyncio
async def test_local_adapter_searches_local_task_posts(monkeypatch):
    import app.services.community_service_adapter as adapter
    import app.services.community_post_service as post_service

    captured = {}

    async def fake_with_local_session(fn):
        return await fn("db-session")

    async def fake_list_task_posts(**kwargs):
        captured.update(kwargs)

        class Post:
            id = "post-001"
            title = "找人取快递"
            content = "东区快递站"
            taskCategory = "生活帮助"
            userId = "u100"
            taskStatus = "待接单"

            class CreatedAt:
                @staticmethod
                def isoformat():
                    return "2026-07-04T00:00:00+00:00"

            createdAt = CreatedAt()

        return [Post()], 1

    monkeypatch.setattr(adapter, "_USE_MOCK", False)
    monkeypatch.setattr(adapter, "_USE_LOCAL", True)
    monkeypatch.setattr(adapter, "_with_local_session", fake_with_local_session)
    monkeypatch.setattr(post_service, "list_task_posts", fake_list_task_posts)

    results = await adapter.search_help_tasks(adapter.HelpTaskSearchQuery(keyword="快递", category="生活帮助", status="待接单"))

    assert len(results) == 1
    assert results[0].task_id == "post-001"
    assert captured["db"] == "db-session"
    assert captured["keyword"] == "快递"
    assert captured["task_category"] == "生活帮助"
    assert captured["task_status"] == "待接单"


@pytest.mark.asyncio
async def test_local_adapter_deletes_local_post(monkeypatch):
    import app.services.community_service_adapter as adapter
    import app.services.community_post_service as post_service

    captured = {}

    async def fake_with_local_session(fn):
        return await fn("db-session")

    async def fake_delete_post(db, post_id, external_user_id):
        captured.update({"db": db, "post_id": post_id, "external_user_id": external_user_id})
        return True

    monkeypatch.setattr(adapter, "_USE_MOCK", False)
    monkeypatch.setattr(adapter, "_USE_LOCAL", True)
    monkeypatch.setattr(adapter, "_with_local_session", fake_with_local_session)
    monkeypatch.setattr(post_service, "delete_post", fake_delete_post)

    result = await adapter.delete_help_task("u100", "post-001")

    assert result.status == "deleted"
    assert captured == {"db": "db-session", "post_id": "post-001", "external_user_id": "u100"}

@pytest.mark.asyncio
async def test_publish_task_requires_confirmation_before_adapter(monkeypatch):
    from app.graphs.community_agent_subgraph import node_publish_task

    called = False

    async def fake_publish(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("publish adapter should not be called before confirmation")

    monkeypatch.setattr("app.graphs.community_agent_subgraph.publish_help_task", fake_publish)

    result = await node_publish_task({
        "external_user_id": "u001",
        "task_fields": {"title": "帮忙取快递", "description": "东区快递站"},
        "actions": [],
    })

    assert called is False
    assert result["actions"] == [{"type": "confirmation_required", "action": "confirm_publish_task"}]


@pytest.mark.asyncio
async def test_confirm_publish_records_approved_state(monkeypatch):
    from app.graphs.community_agent_subgraph import node_confirm_publish, route_after_confirm_publish

    monkeypatch.setattr(
        "app.graphs.community_agent_subgraph.interrupt",
        lambda payload: {"decision": "approve"},
    )

    result = await node_confirm_publish({
        "task_fields": {"title": "帮忙取快递"},
        "task_draft_id": "draft-001",
        "actions": [],
    })

    assert result["confirmation_id"] == "confirmed"
    assert route_after_confirm_publish(result) == "publish_task"


@pytest.mark.asyncio
async def test_delete_flow_reject_does_not_call_delete(monkeypatch):
    from app.graphs.community_agent_subgraph import node_delete_task_execute

    async def fake_delete(external_user_id: str, task_id: str):
        raise AssertionError("delete adapter should not be called after rejection")

    monkeypatch.setattr("app.graphs.community_agent_subgraph.delete_help_task", fake_delete)
    monkeypatch.setattr(
        "app.graphs.community_agent_subgraph.interrupt",
        lambda payload: {"decision": "reject"},
    )

    result = await node_delete_task_execute({
        "external_user_id": "u001",
        "user_message": "帮我删掉 task_abc123",
        "search_results": [
            {
                "task_id": "task_abc123",
                "title": "帮忙取快递",
                "description": "东区快递站",
                "category": "生活帮助",
                "status": "published",
                "created_at": "2026-07-04T00:00:00Z",
            }
        ],
        "actions": [],
    })

    assert result["confirmation_id"] == "cancelled"
    assert result["actions"] == [{"type": "task_delete_cancelled", "task_id": "task_abc123"}]
@pytest.mark.asyncio
async def test_publish_task_passes_draft_id_as_idempotency_key(monkeypatch):
    from app.graphs.community_agent_subgraph import node_publish_task

    captured = {}

    async def fake_publish(**kwargs):
        captured.update(kwargs)

        class Result:
            task_id = "post-001"
            status = "published"

        return Result()

    monkeypatch.setattr("app.graphs.community_agent_subgraph.publish_help_task", fake_publish)

    result = await node_publish_task({
        "external_user_id": "u001",
        "confirmation_id": "confirmed",
        "task_draft_id": "draft_001",
        "task_fields": {"title": "task", "description": "desc"},
        "actions": [],
    })

    assert captured["idempotency_key"] == "draft_001"
    assert result["actions"] == [{"type": "task_published", "task_id": "post-001"}]


@pytest.mark.asyncio
async def test_publish_task_failure_uses_public_error_message(monkeypatch):
    from app.graphs.community_agent_subgraph import node_publish_task
    from app.utils.shared import public_error_message

    async def fake_publish(**kwargs):
        raise RuntimeError("internal publish token leaked")

    monkeypatch.setattr("app.graphs.community_agent_subgraph.publish_help_task", fake_publish)

    result = await node_publish_task({
        "external_user_id": "u001",
        "confirmation_id": "confirmed",
        "task_fields": {"title": "task", "description": "desc"},
        "actions": [],
    })

    assert result["error"] == "internal publish token leaked"
    assert result["response"] == public_error_message()
    assert "internal publish token leaked" not in result["response"]


@pytest.mark.asyncio
async def test_delete_task_failure_uses_public_error_message(monkeypatch):
    from app.graphs.community_agent_subgraph import node_delete_task_execute
    from app.utils.shared import public_error_message

    async def fake_delete(external_user_id: str, task_id: str):
        raise RuntimeError("internal delete token leaked")

    monkeypatch.setattr("app.graphs.community_agent_subgraph.delete_help_task", fake_delete)
    monkeypatch.setattr(
        "app.graphs.community_agent_subgraph.interrupt",
        lambda payload: {"decision": "approve"},
    )

    result = await node_delete_task_execute({
        "external_user_id": "u001",
        "user_message": "delete task_abc123",
        "search_results": [
            {
                "task_id": "task_abc123",
                "title": "task",
                "description": "desc",
                "category": "life",
                "status": "published",
                "created_at": "2026-07-04T00:00:00Z",
            }
        ],
        "actions": [],
    })

    assert result["error"] == "internal delete token leaked"
    assert result["response"] == public_error_message()
    assert "internal delete token leaked" not in result["response"]


@pytest.mark.asyncio
async def test_search_task_failure_uses_public_error_message(monkeypatch):
    from app.graphs.community_agent_subgraph import node_search_task_execute
    from app.utils.shared import public_error_message

    async def fake_search(query):
        raise RuntimeError("internal search token leaked")

    monkeypatch.setattr("app.graphs.community_agent_subgraph.search_help_tasks", fake_search)

    result = await node_search_task_execute({
        "external_user_id": "u001",
        "user_message": "search task",
        "actions": [],
    })

    assert result["error"] == "internal search token leaked"
    assert result["response"] == public_error_message()
    assert "internal search token leaked" not in result["response"]
@pytest.mark.asyncio
async def test_delete_task_execute_preserves_search_failure():
    from app.graphs.community_agent_subgraph import node_delete_task_execute
    from app.utils.shared import public_error_message

    result = await node_delete_task_execute({
        "external_user_id": "u001",
        "user_message": "delete my task",
        "error": "internal search failure leaked",
        "actions": [],
    })

    assert result["error"] == "internal search failure leaked"
    assert result["response"] == public_error_message()
    assert "internal search failure leaked" not in result["response"]
