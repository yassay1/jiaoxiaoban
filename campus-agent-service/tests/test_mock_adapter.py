import pytest
from app.services.mock_community_adapter import (
    search_help_tasks,
    search_my_help_tasks,
    publish_help_task,
    delete_help_task,
    HelpTaskSearchQuery,
    _seed_mock_data,
)


@pytest.mark.asyncio
async def test_publish_and_search():
    await _seed_mock_data()

    result = await publish_help_task(
        title="测试任务",
        description="这是一个测试任务",
        external_user_id="user_test",
        category="生活帮助",
    )
    assert result.task_id.startswith("task_")
    assert result.status == "published"

    query = HelpTaskSearchQuery(keyword="测试")
    results = await search_help_tasks(query)
    assert len(results) >= 1
    assert results[0].title == "测试任务"


@pytest.mark.asyncio
async def test_publish_is_idempotent_when_key_repeats():
    first = await publish_help_task("重复任务", "测试", "user_idempotent", "其他", idempotency_key="draft_001")
    second = await publish_help_task("重复任务", "测试", "user_idempotent", "其他", idempotency_key="draft_001")

    assert second.task_id == first.task_id

    mine = await search_my_help_tasks("user_idempotent")
    assert [task.task_id for task in mine].count(first.task_id) == 1

@pytest.mark.asyncio
async def test_search_my_tasks():
    await _seed_mock_data()
    await publish_help_task("我的任务", "测试", "user_my_test", "学习辅导")

    results = await search_my_help_tasks("user_my_test")
    assert len(results) >= 1
    assert results[0].external_user_id == "user_my_test"


@pytest.mark.asyncio
async def test_delete_task():
    await _seed_mock_data()
    result = await publish_help_task("待删除任务", "test", "user_delete_test", "其他")
    task_id = result.task_id

    # 删除前应该能搜索到
    before = await search_my_help_tasks("user_delete_test")
    assert any(t.task_id == task_id for t in before)

    # 执行删除
    delete_result = await delete_help_task("user_delete_test", task_id)
    assert delete_result.status == "deleted"

    # 删除后不应该搜索到
    after = await search_my_help_tasks("user_delete_test")
    assert not any(t.task_id == task_id for t in after)
