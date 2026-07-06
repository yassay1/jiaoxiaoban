"""Mock community service adapter — 模拟社区服务接口，后期替换为真实 HTTP 调用。

Phase 5 P8: uses shared types from community_client for consistency.
"""

import uuid
from datetime import datetime, timezone

# Shared types from community_client (single source of truth)
from app.services.community_client import (
    HelpTaskSearchQuery,
    HelpTaskItem,
    PublishHelpTaskResult,
    DeleteHelpTaskResult,
)


_mock_tasks: list[HelpTaskItem] = []
_seeded = False


def _generate_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


async def _seed_mock_data():
    global _seeded
    if _seeded:
        return
    seeds = [
        ("找人帮忙取快递", "东区快递站，今天下午3点之前，帮忙取一个中通快递", "生活帮助"),
        ("求组队参加美赛", "大三，有编程基础，想找2-3个人一起参加美赛", "组队招募"),
        ("借一本线性代数教材", "需要借一本同济版线性代数，用一周", "物品借用"),
    ]
    for title, desc, cat in seeds:
        await publish_help_task(title, desc, "user_mock_001", cat)
    _seeded = True


async def search_help_tasks(query: HelpTaskSearchQuery) -> list[HelpTaskItem]:
    await _seed_mock_data()
    results = _mock_tasks
    if query.keyword:
        keyword = query.keyword.lower()
        results = [t for t in results if keyword in t.title.lower() or keyword in t.description.lower()]
    if query.category:
        results = [t for t in results if t.category == query.category]
    if query.status:
        results = [t for t in results if t.status == query.status]
    return results[query.offset : query.offset + query.limit]


async def search_my_help_tasks(external_user_id: str, filters: dict | None = None) -> list[HelpTaskItem]:
    await _seed_mock_data()
    results = [t for t in _mock_tasks if t.external_user_id == external_user_id]
    filters = filters or {}
    status = filters.get("status")
    if status:
        results = [t for t in results if t.status == status]
    return results


async def publish_help_task(
    title: str,
    description: str,
    external_user_id: str,
    category: str | None = None,
    idempotency_key: str | None = None,
) -> PublishHelpTaskResult:
    if idempotency_key:
        existing = next(
            (
                task for task in _mock_tasks
                if task.external_user_id == external_user_id
                and task.tags
                and f"idempotency:{idempotency_key}" in task.tags
            ),
            None,
        )
        if existing:
            return PublishHelpTaskResult(task_id=existing.task_id, status=existing.status)
    task_id = _generate_task_id()
    task = HelpTaskItem(
        task_id=task_id,
        title=title,
        description=description,
        category=category,
        external_user_id=external_user_id,
        status="published",
        created_at=datetime.now(timezone.utc).isoformat(),
        tags=[f"idempotency:{idempotency_key}"] if idempotency_key else [],
    )
    _mock_tasks.append(task)
    return PublishHelpTaskResult(task_id=task_id, status="published")


async def delete_help_task(external_user_id: str, task_id: str) -> DeleteHelpTaskResult:
    global _mock_tasks
    before = len(_mock_tasks)
    _mock_tasks = [t for t in _mock_tasks if not (t.task_id == task_id and t.external_user_id == external_user_id)]
    status = "deleted" if len(_mock_tasks) < before else "not_found"
    return DeleteHelpTaskResult(task_id=task_id, status=status)
