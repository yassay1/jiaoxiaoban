"""Community service adapter — unified interface between graph nodes and community backend.

Modes:
- mock: in-memory demo adapter (default, for tests and offline demo)
- local: write/read the local CommunityPost tables (for integrated demo)
- real: external community HTTP service (Phase 5 P8)

Phase 5 P8: all three modes are now fully implemented for all operations.
"""

import os
import logging

logger = logging.getLogger(__name__)

_MODE = os.getenv("COMMUNITY_SERVICE_MODE", "mock")
_USE_MOCK = _MODE == "mock"
_USE_LOCAL = _MODE == "local"

# Re-export data types from community_client (single source of truth)
from app.services.community_client import (
    HelpTaskSearchQuery,
    HelpTaskItem,
    PublishHelpTaskResult,
    DeleteHelpTaskResult,
    CommunityServiceError,
)


def _post_to_help_task_item(post) -> HelpTaskItem:
    return HelpTaskItem(
        task_id=post.id,
        title=post.title,
        description=post.content,
        category=post.taskCategory,
        external_user_id=post.userId or "",
        status=post.taskStatus or "published",
        created_at=post.createdAt.isoformat(),
    )


async def _with_local_session(fn):
    from app.db.session import async_session_factory

    async with async_session_factory() as db:
        try:
            result = await fn(db)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise


# ── Search Help Tasks ──

async def search_help_tasks(query: HelpTaskSearchQuery) -> list[HelpTaskItem]:
    if _USE_MOCK:
        from app.services.mock_community_adapter import search_help_tasks as _fn
        return await _fn(query)
    if _USE_LOCAL:
        from app.services.community_post_service import list_task_posts

        async def run(db):
            posts, _ = await list_task_posts(
                db=db,
                keyword=query.keyword,
                tag=None,
                external_user_id="",
                task_status=query.status,
                task_category=query.category,
                page=(query.offset // max(query.limit, 1)) + 1,
                page_size=query.limit,
            )
            return [_post_to_help_task_item(post) for post in posts]

        return await _with_local_session(run)
    # Phase 5 P8: real mode
    from app.services.community_client import community_client
    try:
        results = await community_client.search_tasks(query)
        return [
            HelpTaskItem(
                task_id=r.get("id", r.get("task_id", "")),
                title=r.get("title", ""),
                description=r.get("description", r.get("content", "")),
                category=r.get("category"),
                external_user_id=r.get("external_user_id", ""),
                status=r.get("status", "published"),
                created_at=r.get("created_at", r.get("createdAt", "")),
                tags=r.get("tags", []),
            )
            for r in results
        ]
    except CommunityServiceError:
        raise
    except Exception as e:
        raise CommunityServiceError(f"Real community search failed: {e}") from e


# ── Search My Help Tasks ──

async def search_my_help_tasks(
    external_user_id: str, filters: dict | None = None
) -> list[HelpTaskItem]:
    if _USE_MOCK:
        from app.services.mock_community_adapter import search_my_help_tasks as _fn
        return await _fn(external_user_id, filters)
    if _USE_LOCAL:
        from app.services.community_post_service import list_my_tasks

        filters = filters or {}

        async def run(db):
            posts, _ = await list_my_tasks(
                db=db,
                external_user_id=external_user_id,
                role="published",
                task_status=filters.get("status"),
                page=1,
                page_size=100,
            )
            return [_post_to_help_task_item(post) for post in posts]

        return await _with_local_session(run)
    # Phase 5 P8: real mode
    from app.services.community_client import community_client
    try:
        results = await community_client.get_my_tasks(
            external_user_id=external_user_id,
            status=(filters or {}).get("status"),
        )
        return [
            HelpTaskItem(
                task_id=r.get("id", r.get("task_id", "")),
                title=r.get("title", ""),
                description=r.get("description", r.get("content", "")),
                category=r.get("category"),
                external_user_id=external_user_id,
                status=r.get("status", "published"),
                created_at=r.get("created_at", r.get("createdAt", "")),
            )
            for r in results
        ]
    except CommunityServiceError:
        raise
    except Exception as e:
        raise CommunityServiceError(f"Real community my-tasks failed: {e}") from e


# ── Publish Help Task ──

async def publish_help_task(
    title: str,
    description: str,
    external_user_id: str,
    category: str | None = None,
    idempotency_key: str | None = None,
) -> PublishHelpTaskResult:
    if _USE_MOCK:
        from app.services.mock_community_adapter import publish_help_task as _fn
        return await _fn(
            title=title,
            description=description,
            external_user_id=external_user_id,
            category=category,
            idempotency_key=idempotency_key,
        )
    if _USE_LOCAL:
        from app.schemas.community import PostCreateRequest
        from app.services.community_post_service import create_post

        async def run(db):
            post = await create_post(
                db,
                PostCreateRequest(
                    title=title,
                    content=description,
                    type="任务帖子",
                    tags=[category] if category else [],
                    taskCategory=category,
                    taskStatus="待接单",
                    isAiAssisted=True,
                    sourceAgent=f"community_agent:{idempotency_key}" if idempotency_key else "community_agent",
                ),
                external_user_id=external_user_id,
            )
            return PublishHelpTaskResult(task_id=post.id, status=post.taskStatus or "published")

        return await _with_local_session(run)
    # Phase 5 P8: real mode (existing, with improved error handling)
    from app.services.community_client import community_client, CommunityServiceError
    try:
        result = await community_client.create_task({
            "title": title,
            "description": description,
            "external_user_id": external_user_id,
            "category": category,
            "idempotency_key": idempotency_key,
        })
        return PublishHelpTaskResult(
            task_id=result.get("id", result.get("task_id", "")),
            status="published",
        )
    except CommunityServiceError:
        raise
    except Exception as e:
        raise CommunityServiceError(f"Real community publish failed: {e}") from e


# ── Delete Help Task ──

async def delete_help_task(external_user_id: str, task_id: str) -> DeleteHelpTaskResult:
    if _USE_MOCK:
        from app.services.mock_community_adapter import delete_help_task as _fn
        return await _fn(external_user_id, task_id)
    if _USE_LOCAL:
        from app.services.community_post_service import delete_post

        async def run(db):
            ok = await delete_post(db, task_id, external_user_id=external_user_id)
            return DeleteHelpTaskResult(task_id=task_id, status="deleted" if ok else "not_found")

        return await _with_local_session(run)
    # Phase 5 P8: real mode
    from app.services.community_client import community_client, CommunityServiceError
    try:
        result = await community_client.delete_task(task_id, external_user_id)
        status = result.get("status", "deleted")
        return DeleteHelpTaskResult(task_id=task_id, status=status)
    except CommunityServiceError:
        raise
    except Exception as e:
        raise CommunityServiceError(f"Real community delete failed: {e}") from e