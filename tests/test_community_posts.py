from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError

from app.db.models import CommunityComment, CommunityPost, CommunityPostFavorite, CommunityPostLike, CommunityReport, CommunityTaskParticipant
from app.api import community as community_api
from app.schemas.community import CommentCreateRequest, ModerationRequest, PostCreateRequest, ReportCreateRequest, ReportResolveRequest, TaskStatusUpdateRequest
from app.services import community_post_service as service


class _ScalarOneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class _ListResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


def _unique_constraint_names(model):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_community_user_action_tables_keep_unique_constraints():
    assert "uq_community_post_like_user" in _unique_constraint_names(CommunityPostLike)
    assert "uq_community_post_favorite_user" in _unique_constraint_names(CommunityPostFavorite)
    assert "uq_community_task_participant_user" in _unique_constraint_names(CommunityTaskParticipant)


@pytest.mark.asyncio
async def test_create_post_uses_request_user_and_task_deadline(monkeypatch):
    captured = {}

    def fake_to_response(post):
        captured["post"] = post
        return MagicMock(id="post-001")

    monkeypatch.setattr(service, "_to_response", fake_to_response)
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    req = PostCreateRequest(
        title="找人取快递",
        content="东区快递站",
        type="任务帖子",
        tags=["快递"],
        taskStatus="待接单",
        taskCategory="生活帮助",
        taskDeadline="2026-07-04T12:00:00+00:00",
    )

    await service.create_post(db, req, external_user_id="u100", user_name="小明")

    post = captured["post"]
    assert post.external_user_id == "u100"
    assert post.user_name == "小明"
    assert post.task_deadline == datetime.fromisoformat("2026-07-04T12:00:00+00:00")
    db.add.assert_called_once_with(post)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_post_returns_existing_draft_publish(monkeypatch):
    existing = CommunityPost(
        id="post-001",
        external_user_id="u100",
        title="t",
        content="c",
        source_agent="community_agent:draft_001",
    )

    async def fake_response(db, post, external_user_id):
        return {"id": post.id, "sourceAgent": post.source_agent, "viewer": external_user_id}

    monkeypatch.setattr(service, "_to_response_with_interactions", fake_response)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult(existing))
    db.add = MagicMock()
    db.flush = AsyncMock()
    req = PostCreateRequest(title="t", content="c", sourceAgent="community_agent:draft_001")

    result = await service.create_post(db, req, external_user_id="u100", user_name="Alice")

    assert result == {"id": "post-001", "sourceAgent": "community_agent:draft_001", "viewer": "u100"}
    db.add.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_public_list_posts_filters_hidden_status(monkeypatch):
    captured = []

    async def fake_ensure_demo_posts(db):
        return None

    async def fake_execute(stmt):
        captured.append(stmt)
        if len(captured) == 1:
            return _ListResult(0)
        return _ListResult([])

    monkeypatch.setattr(service, "ensure_demo_posts", fake_ensure_demo_posts)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=fake_execute)

    posts, total = await service.list_posts(db, external_user_id="viewer")

    assert posts == []
    assert total == 0
    assert "community_posts.status" in str(captured[0])
    assert "community_posts.status" in str(captured[1])


@pytest.mark.asyncio
async def test_get_post_hides_unpublished_from_other_users(monkeypatch):
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c", status="hidden")

    async def fake_ensure_demo_posts(db):
        return None

    async def fake_response(db, post, external_user_id):
        return {"id": post.id, "viewer": external_user_id}

    monkeypatch.setattr(service, "ensure_demo_posts", fake_ensure_demo_posts)
    monkeypatch.setattr(service, "_to_response_with_interactions", fake_response)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult(post))

    hidden = await service.get_post(db, "post-001", external_user_id="viewer")
    owner_view = await service.get_post(db, "post-001", external_user_id="owner")

    assert hidden is None
    assert owner_view == {"id": "post-001", "viewer": "owner"}

@pytest.mark.asyncio
async def test_delete_post_requires_owner():
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c")
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ScalarResult(post), _ScalarResult(post)])
    db.delete = AsyncMock()
    db.flush = AsyncMock()

    ok = await service.delete_post(db, "post-001", external_user_id="other")
    assert ok is False
    db.delete.assert_not_called()

    ok = await service.delete_post(db, "post-001", external_user_id="owner")
    assert ok is True
    db.delete.assert_awaited_once_with(post)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_task_status_requires_owner(monkeypatch):
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c", task_status="待接单")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult(post))
    db.flush = AsyncMock()
    monkeypatch.setattr(service, "_to_response", lambda p: {"id": p.id, "taskStatus": p.task_status})

    denied = await service.update_task_status(db, "post-001", "已完成", external_user_id="other")
    assert denied is None
    assert post.task_status == "待接单"

    updated = await service.update_task_status(db, "post-001", "已完成", external_user_id="owner")
    assert updated == {"id": "post-001", "taskStatus": "已完成"}
    assert post.task_status == "已完成"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_create_post_passes_request_user(monkeypatch):
    captured = {}

    async def fake_create_post(db, req, external_user_id, user_name):
        captured.update(
            {
                "db": db,
                "req": req,
                "external_user_id": external_user_id,
                "user_name": user_name,
            }
        )
        return {"id": "post-001"}

    monkeypatch.setattr(community_api, "create_post", fake_create_post)
    db = MagicMock()
    req = PostCreateRequest(title="找人取快递", content="东区快递站")

    result = await community_api.api_create_post(req, externalUserId="u100", userName="小明", db=db)

    assert result == {"id": "post-001"}
    assert captured == {
        "db": db,
        "req": req,
        "external_user_id": "u100",
        "user_name": "小明",
    }


@pytest.mark.asyncio
async def test_api_delete_post_passes_request_user(monkeypatch):
    captured = {}

    async def fake_delete_post(db, post_id, external_user_id):
        captured.update({"db": db, "post_id": post_id, "external_user_id": external_user_id})
        return True

    monkeypatch.setattr(community_api, "delete_post", fake_delete_post)
    db = MagicMock()

    result = await community_api.api_delete_post("post-001", externalUserId="owner", db=db)

    assert result == {"detail": "deleted"}
    assert captured == {"db": db, "post_id": "post-001", "external_user_id": "owner"}


@pytest.mark.asyncio
async def test_api_update_task_status_passes_request_user(monkeypatch):
    captured = {}

    async def fake_update_task_status(db, post_id, task_status, external_user_id):
        captured.update(
            {
                "db": db,
                "post_id": post_id,
                "task_status": task_status,
                "external_user_id": external_user_id,
            }
        )
        return {"id": "post-001", "taskStatus": task_status}

    monkeypatch.setattr(community_api, "update_task_status", fake_update_task_status)
    db = MagicMock()
    req = TaskStatusUpdateRequest(taskStatus="已完成")

    result = await community_api.api_update_task_status("post-001", req, externalUserId="owner", db=db)

    assert result == {"id": "post-001", "taskStatus": "已完成"}
    assert captured == {
        "db": db,
        "post_id": "post-001",
        "task_status": "已完成",
        "external_user_id": "owner",
    }

@pytest.mark.asyncio
async def test_create_comment_uses_request_user(monkeypatch):
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c")
    captured = {}

    def fake_to_comment_response(comment):
        captured["comment"] = comment
        return {"id": "comment-001"}

    monkeypatch.setattr(service, "_to_comment_response", fake_to_comment_response)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult(post))
    db.add = MagicMock()
    db.flush = AsyncMock()
    req = CommentCreateRequest(content="useful")

    result = await service.create_comment(db, "post-001", req, external_user_id="u100", user_name="Alice")

    assert result == {"id": "comment-001"}
    comment = captured["comment"]
    assert comment.post_id == "post-001"
    assert comment.external_user_id == "u100"
    assert comment.user_name == "Alice"
    assert comment.content == "useful"
    db.add.assert_called_once_with(comment)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_comment_requires_owner():
    comment = CommunityComment(id="comment-001", post_id="post-001", external_user_id="owner", content="c")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult(comment))
    db.delete = AsyncMock()
    db.flush = AsyncMock()

    denied = await service.delete_comment(db, "post-001", "comment-001", external_user_id="other")
    assert denied is False
    db.delete.assert_not_called()

    ok = await service.delete_comment(db, "post-001", "comment-001", external_user_id="owner")
    assert ok is True
    db.delete.assert_awaited_once_with(comment)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_like_creates_and_removes_like():
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c", like_count=0)
    db = MagicMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(post),
            _ScalarResult(None),
            _ScalarResult(post),
            _ScalarOneResult(1),
            _ScalarResult(CommunityPostLike(post_id="post-001", external_user_id="u100")),
            _ScalarOneResult(0),
            _ScalarResult(None),
        ]
    )

    liked = await service.toggle_like(db, "post-001", external_user_id="u100")

    assert liked.postId == "post-001"
    assert liked.likedByMe is True
    assert liked.likeCount == 1
    assert isinstance(db.add.call_args.args[0], CommunityPostLike)
    db.flush.assert_awaited_once()

    existing = CommunityPostLike(post_id="post-001", external_user_id="u100")
    db = MagicMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    post.like_count = 1
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(post),
            _ScalarResult(existing),
            _ScalarResult(post),
            _ScalarOneResult(0),
            _ScalarResult(None),
            _ScalarOneResult(0),
            _ScalarResult(None),
        ]
    )

    unliked = await service.toggle_like(db, "post-001", external_user_id="u100")

    assert unliked.likedByMe is False
    assert unliked.likeCount == 0
    db.delete.assert_awaited_once_with(existing)
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_toggle_favorite_creates_and_removes_favorite():
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c", like_count=2)
    db = MagicMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(post),
            _ScalarResult(None),
            _ScalarResult(post),
            _ScalarOneResult(2),
            _ScalarResult(None),
            _ScalarOneResult(1),
            _ScalarResult(CommunityPostFavorite(post_id="post-001", external_user_id="u100")),
        ]
    )

    favorited = await service.toggle_favorite(db, "post-001", external_user_id="u100")

    assert favorited.postId == "post-001"
    assert favorited.favoritedByMe is True
    assert favorited.favoriteCount == 1
    assert isinstance(db.add.call_args.args[0], CommunityPostFavorite)
    db.flush.assert_awaited_once()

    existing = CommunityPostFavorite(post_id="post-001", external_user_id="u100")
    db = MagicMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(post),
            _ScalarResult(existing),
            _ScalarResult(post),
            _ScalarOneResult(2),
            _ScalarResult(None),
            _ScalarOneResult(0),
            _ScalarResult(None),
        ]
    )

    unfavorited = await service.toggle_favorite(db, "post-001", external_user_id="u100")

    assert unfavorited.favoritedByMe is False
    assert unfavorited.favoriteCount == 0
    db.delete.assert_awaited_once_with(existing)
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_toggle_like_returns_current_state_after_unique_conflict():
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c", like_count=0)
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=[IntegrityError("insert like", {}, Exception())])
    db.rollback = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(post),
            _ScalarResult(None),
            _ScalarResult(post),
            _ScalarOneResult(1),
            _ScalarResult(CommunityPostLike(post_id="post-001", external_user_id="u100")),
            _ScalarOneResult(0),
            _ScalarResult(None),
        ]
    )

    liked = await service.toggle_like(db, "post-001", external_user_id="u100")

    assert liked.likedByMe is True
    assert liked.likeCount == 1
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_toggle_favorite_returns_current_state_after_unique_conflict():
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c", like_count=0)
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=[IntegrityError("insert favorite", {}, Exception())])
    db.rollback = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(post),
            _ScalarResult(None),
            _ScalarResult(post),
            _ScalarOneResult(0),
            _ScalarResult(None),
            _ScalarOneResult(1),
            _ScalarResult(CommunityPostFavorite(post_id="post-001", external_user_id="u100")),
        ]
    )

    favorited = await service.toggle_favorite(db, "post-001", external_user_id="u100")

    assert favorited.favoritedByMe is True
    assert favorited.favoriteCount == 1
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_comment_and_interaction_endpoints_pass_user(monkeypatch):
    captured = {}

    async def fake_create_comment(db, post_id, req, external_user_id, user_name):
        captured["comment"] = (db, post_id, req, external_user_id, user_name)
        return {"id": "comment-001"}

    async def fake_toggle_like(db, post_id, external_user_id):
        captured["like"] = (db, post_id, external_user_id)
        return {"postId": post_id, "likedByMe": True, "likeCount": 1}

    async def fake_toggle_favorite(db, post_id, external_user_id):
        captured["favorite"] = (db, post_id, external_user_id)
        return {"postId": post_id, "favoritedByMe": True, "favoriteCount": 1}

    monkeypatch.setattr(community_api, "create_comment", fake_create_comment)
    monkeypatch.setattr(community_api, "toggle_like", fake_toggle_like)
    monkeypatch.setattr(community_api, "toggle_favorite", fake_toggle_favorite)
    db = MagicMock()
    req = CommentCreateRequest(content="useful")

    comment = await community_api.api_create_comment("post-001", req, externalUserId="u100", userName="Alice", db=db)
    like = await community_api.api_toggle_like("post-001", externalUserId="u100", db=db)
    favorite = await community_api.api_toggle_favorite("post-001", externalUserId="u100", db=db)

    assert comment == {"id": "comment-001"}
    assert like["likedByMe"] is True
    assert favorite["favoritedByMe"] is True
    assert captured["comment"] == (db, "post-001", req, "u100", "Alice")
    assert captured["like"] == (db, "post-001", "u100")
    assert captured["favorite"] == (db, "post-001", "u100")

@pytest.mark.asyncio
async def test_accept_task_rejects_owner_and_full_task():
    owner_post = CommunityPost(
        id="task-001",
        external_user_id="owner",
        title="t",
        content="c",
        post_type="任务帖子",
        task_status="待接单",
        task_accepted_count=0,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult(owner_post))

    denied_owner = await service.accept_task(db, "task-001", external_user_id="owner", user_name="Owner")
    assert denied_owner is None

    full_post = CommunityPost(
        id="task-001",
        external_user_id="owner",
        title="t",
        content="c",
        post_type="任务帖子",
        task_status="待接单",
        task_accepted_count=1,
        task_max_participants=1,
    )
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ScalarResult(full_post), _ScalarResult(None)])

    denied_full = await service.accept_task(db, "task-001", external_user_id="helper", user_name="Helper")
    assert denied_full is None


@pytest.mark.asyncio
async def test_accept_task_creates_participant_and_updates_status():
    post = CommunityPost(
        id="task-001",
        external_user_id="owner",
        title="t",
        content="c",
        post_type="任务帖子",
        task_status="待接单",
        task_accepted_count=0,
        task_max_participants=2,
    )
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(side_effect=[_ScalarResult(post), _ScalarResult(None)])

    result = await service.accept_task(db, "task-001", external_user_id="helper", user_name="Helper")

    assert result.action == "accepted"
    assert result.taskStatus == "进行中"
    assert result.taskAcceptedCount == 1
    assert post.task_status == "进行中"
    assert post.task_accepted_count == 1
    participant = db.add.call_args.args[0]
    assert isinstance(participant, CommunityTaskParticipant)
    assert participant.external_user_id == "helper"
    assert participant.user_name == "Helper"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_accept_task_returns_current_state_after_unique_conflict():
    post = CommunityPost(
        id="task-001",
        external_user_id="owner",
        title="t",
        content="c",
        post_type="任务帖子",
        task_status="待接单",
        task_accepted_count=0,
        task_max_participants=2,
    )
    accepted_post = CommunityPost(
        id="task-001",
        external_user_id="owner",
        title="t",
        content="c",
        post_type="任务帖子",
        task_status="进行中",
        task_accepted_count=1,
        task_max_participants=2,
    )
    participant = CommunityTaskParticipant(
        post_id="task-001",
        external_user_id="helper",
        user_name="Helper",
        status="accepted",
    )
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=[IntegrityError("insert participant", {}, Exception())])
    db.rollback = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(post),
            _ScalarResult(None),
            _ScalarResult(accepted_post),
            _ScalarResult(participant),
            _ScalarOneResult(1),
        ]
    )

    result = await service.accept_task(db, "task-001", external_user_id="helper", user_name="Helper")

    assert result.action == "accepted"
    assert result.taskAcceptedCount == 1
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_task_supports_participant_and_owner():
    post = CommunityPost(
        id="task-001",
        external_user_id="owner",
        title="t",
        content="c",
        post_type="任务帖子",
        task_status="进行中",
        task_accepted_count=1,
    )
    participant = CommunityTaskParticipant(
        post_id="task-001",
        external_user_id="helper",
        user_name="Helper",
        status="accepted",
    )
    db = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(side_effect=[_ScalarResult(post), _ScalarResult(participant)])

    cancelled_by_helper = await service.cancel_task(db, "task-001", external_user_id="helper")

    assert cancelled_by_helper.action == "cancelled"
    assert cancelled_by_helper.taskStatus == "待接单"
    assert post.task_accepted_count == 0
    assert participant.status == "cancelled"

    post.task_status = "进行中"
    post.task_accepted_count = 1
    db = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(return_value=_ScalarResult(post))

    cancelled_by_owner = await service.cancel_task(db, "task-001", external_user_id="owner")

    assert cancelled_by_owner.taskStatus == "已取消"
    assert post.task_accepted_count == 0
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_complete_task_requires_owner():
    post = CommunityPost(
        id="task-001",
        external_user_id="owner",
        title="t",
        content="c",
        post_type="任务帖子",
        task_status="进行中",
        task_accepted_count=1,
    )
    db = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(return_value=_ScalarResult(post))

    denied = await service.complete_task(db, "task-001", external_user_id="helper")
    assert denied is None
    assert post.task_status == "进行中"

    completed = await service.complete_task(db, "task-001", external_user_id="owner")
    assert completed.action == "completed"
    assert completed.taskStatus == "已完成"
    assert post.task_status == "已完成"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_task_endpoints_pass_user(monkeypatch):
    captured = {}

    async def fake_accept_task(db, post_id, external_user_id, user_name):
        captured["accept"] = (db, post_id, external_user_id, user_name)
        return {"action": "accepted"}

    async def fake_cancel_task(db, post_id, external_user_id):
        captured["cancel"] = (db, post_id, external_user_id)
        return {"action": "cancelled"}

    async def fake_complete_task(db, post_id, external_user_id):
        captured["complete"] = (db, post_id, external_user_id)
        return {"action": "completed"}

    monkeypatch.setattr(community_api, "accept_task", fake_accept_task)
    monkeypatch.setattr(community_api, "cancel_task", fake_cancel_task)
    monkeypatch.setattr(community_api, "complete_task", fake_complete_task)
    db = MagicMock()

    accepted = await community_api.api_accept_task("task-001", externalUserId="helper", userName="Helper", db=db)
    cancelled = await community_api.api_cancel_task("task-001", externalUserId="helper", db=db)
    completed = await community_api.api_complete_task("task-001", externalUserId="owner", db=db)

    assert accepted == {"action": "accepted"}
    assert cancelled == {"action": "cancelled"}
    assert completed == {"action": "completed"}
    assert captured["accept"] == (db, "task-001", "helper", "Helper")
    assert captured["cancel"] == (db, "task-001", "helper")
    assert captured["complete"] == (db, "task-001", "owner")

@pytest.mark.asyncio
async def test_list_my_posts_filters_owner(monkeypatch):
    posts = [CommunityPost(id="post-001", external_user_id="u100", title="t", content="c")]

    async def fake_response(db, post, external_user_id):
        return {"id": post.id, "viewer": external_user_id}

    monkeypatch.setattr(service, "_to_response_with_interactions", fake_response)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ListResult(1), _ListResult(posts)])

    result, total = await service.list_my_posts(db, external_user_id="u100")

    assert total == 1
    assert result == [{"id": "post-001", "viewer": "u100"}]
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_my_participated_tasks_uses_participant_relation(monkeypatch):
    posts = [CommunityPost(id="task-001", external_user_id="owner", title="t", content="c", task_status="open")]

    async def fake_response(db, post, external_user_id):
        return {"id": post.id, "viewer": external_user_id}

    monkeypatch.setattr(service, "_to_response_with_interactions", fake_response)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ListResult(1), _ListResult(posts)])

    result, total = await service.list_my_participated_tasks(db, external_user_id="helper")

    assert total == 1
    assert result == [{"id": "task-001", "viewer": "helper"}]
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_my_tasks_supports_role_variants(monkeypatch):
    posts = [CommunityPost(id="task-001", external_user_id="owner", title="t", content="c", task_status="open")]

    async def fake_response(db, post, external_user_id):
        return {"id": post.id, "viewer": external_user_id}

    monkeypatch.setattr(service, "_to_response_with_interactions", fake_response)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ListResult(1), _ListResult(posts)])

    result, total = await service.list_my_tasks(db, external_user_id="helper", role="all")

    assert total == 1
    assert result == [{"id": "task-001", "viewer": "helper"}]

    async def fake_participated(*args, **kwargs):
        return ([{"id": "task-002"}], 1)

    monkeypatch.setattr(service, "list_my_participated_tasks", fake_participated)
    participated, participated_total = await service.list_my_tasks(db, external_user_id="helper", role="participated")

    assert participated == [{"id": "task-002"}]
    assert participated_total == 1


@pytest.mark.asyncio
async def test_api_mine_endpoints_pass_user_and_filters(monkeypatch):
    captured = {}

    def post_payload(post_id):
        return {
            "id": post_id,
            "title": "t",
            "content": "c",
            "type": "normal",
            "tags": [],
            "userName": "Alice",
            "createdAt": datetime.fromisoformat("2026-07-04T00:00:00+00:00"),
        }

    async def fake_list_my_posts(**kwargs):
        captured["posts"] = kwargs
        return ([post_payload("post-001")], 1)

    async def fake_list_my_tasks(**kwargs):
        captured["tasks"] = kwargs
        return ([post_payload("task-001")], 1)

    async def fake_list_my_participated_tasks(**kwargs):
        captured["participated"] = kwargs
        return ([post_payload("task-002")], 1)

    monkeypatch.setattr(community_api, "list_my_posts", fake_list_my_posts)
    monkeypatch.setattr(community_api, "list_my_tasks", fake_list_my_tasks)
    monkeypatch.setattr(community_api, "list_my_participated_tasks", fake_list_my_participated_tasks)
    db = MagicMock()

    posts = await community_api.api_list_my_posts(postType="normal", taskStatus="open", externalUserId="u100", db=db)
    tasks = await community_api.api_list_my_tasks(role="published", taskStatus="open", externalUserId="u100", db=db)
    participated = await community_api.api_list_my_participated_tasks(
        participantStatus="cancelled",
        taskStatus="closed",
        externalUserId="u100",
        db=db,
    )

    assert posts.total == 1
    assert tasks.total == 1
    assert participated.total == 1
    assert captured["posts"]["external_user_id"] == "u100"
    assert captured["posts"]["post_type"] == "normal"
    assert captured["tasks"]["role"] == "published"
    assert captured["participated"]["participant_status"] == "cancelled"

@pytest.mark.asyncio
async def test_create_report_uses_request_user(monkeypatch):
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c")
    captured = {}

    def fake_report_response(report):
        captured["report"] = report
        return {"id": "report-001"}

    monkeypatch.setattr(service, "_to_report_response", fake_report_response)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ScalarResult(post), _ScalarResult(None)])
    db.add = MagicMock()
    db.flush = AsyncMock()
    req = ReportCreateRequest(reason="spam", detail="ads")

    result = await service.create_report(db, "post-001", req, external_user_id="u100", user_name="Alice")

    assert result == {"id": "report-001"}
    report = captured["report"]
    assert report.target_type == "post"
    assert report.target_id == "post-001"
    assert report.reporter_external_user_id == "u100"
    assert report.reporter_name == "Alice"
    assert report.reason == "spam"
    assert report.status == "pending"
    db.add.assert_called_once_with(report)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_report_returns_existing_pending_report(monkeypatch):
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c")
    existing = CommunityReport(
        id="report-001",
        target_type="post",
        target_id="post-001",
        reporter_external_user_id="u100",
        reporter_name="Alice",
        reason="spam",
        status="pending",
    )
    monkeypatch.setattr(service, "_to_report_response", lambda report: {"id": report.id, "status": report.status})
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(side_effect=[_ScalarResult(post), _ScalarResult(existing)])
    req = ReportCreateRequest(reason="spam", detail="duplicate click")

    result = await service.create_report(db, "post-001", req, external_user_id="u100", user_name="Alice")

    assert result == {"id": "report-001", "status": "pending"}
    db.add.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_list_reports_filters_status(monkeypatch):
    reports = [
        CommunityReport(
            id="report-001",
            target_type="post",
            target_id="post-001",
            reporter_external_user_id="u100",
            reporter_name="Alice",
            reason="spam",
            status="pending",
        )
    ]
    monkeypatch.setattr(service, "_to_report_response", lambda report: {"id": report.id, "status": report.status})
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ListResult(1), _ListResult(reports)])

    result, total = await service.list_reports(db, status="pending")

    assert total == 1
    assert result == [{"id": "report-001", "status": "pending"}]
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_resolve_report_updates_report_and_post(monkeypatch):
    report = CommunityReport(
        id="report-001",
        target_type="post",
        target_id="post-001",
        reporter_external_user_id="u100",
        reporter_name="Alice",
        reason="spam",
        status="pending",
    )
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c", status="published")
    monkeypatch.setattr(service, "_to_report_response", lambda r: {"id": r.id, "status": r.status, "resolution": r.resolution})
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_ScalarResult(report), _ScalarResult(post)])
    db.flush = AsyncMock()
    req = ReportResolveRequest(resolution="hide_post", resolutionNote="confirmed", postStatus="hidden")

    result = await service.resolve_report(db, "report-001", req, reviewer_external_user_id="admin")

    assert result == {"id": "report-001", "status": "resolved", "resolution": "hide_post"}
    assert report.status == "resolved"
    assert report.reviewer_external_user_id == "admin"
    assert report.resolution_note == "confirmed"
    assert report.resolved_at is not None
    assert post.status == "hidden"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_report_is_idempotent_after_resolved(monkeypatch):
    report = CommunityReport(
        id="report-001",
        target_type="post",
        target_id="post-001",
        reporter_external_user_id="u100",
        reporter_name="Alice",
        reason="spam",
        status="resolved",
        reviewer_external_user_id="admin-a",
        resolution="hide_post",
        resolution_note="confirmed",
    )
    monkeypatch.setattr(
        service,
        "_to_report_response",
        lambda r: {"id": r.id, "reviewer": r.reviewer_external_user_id, "resolution": r.resolution},
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult(report))
    db.flush = AsyncMock()
    req = ReportResolveRequest(resolution="reject", resolutionNote="second click")

    result = await service.resolve_report(db, "report-001", req, reviewer_external_user_id="admin-b")

    assert result == {"id": "report-001", "reviewer": "admin-a", "resolution": "hide_post"}
    assert report.reviewer_external_user_id == "admin-a"
    assert report.resolution == "hide_post"
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_moderate_post_updates_status(monkeypatch):
    post = CommunityPost(id="post-001", external_user_id="owner", title="t", content="c", status="published")
    monkeypatch.setattr(service, "_to_response", lambda p: {"id": p.id, "status": p.status})
    db = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarResult(post))
    db.flush = AsyncMock()
    req = ModerationRequest(status="hidden", reason="policy")

    result = await service.moderate_post(db, "post-001", req, reviewer_external_user_id="admin")

    assert result == {"id": "post-001", "status": "hidden"}
    assert post.status == "hidden"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_report_and_moderation_endpoints_pass_user(monkeypatch):
    captured = {}

    async def fake_create_report(db, post_id, req, external_user_id, user_name):
        captured["create"] = (db, post_id, req, external_user_id, user_name)
        return {"id": "report-001"}

    async def fake_list_reports(**kwargs):
        captured["list"] = kwargs
        payload = {
            "id": "report-001",
            "targetType": "post",
            "targetId": "post-001",
            "reporterUserId": "u100",
            "reporterName": "Alice",
            "reason": "spam",
            "status": "pending",
            "createdAt": datetime.fromisoformat("2026-07-04T00:00:00+00:00"),
        }
        return ([payload], 1)

    async def fake_resolve_report(db, report_id, req, reviewer_external_user_id):
        captured["resolve"] = (db, report_id, req, reviewer_external_user_id)
        return {
            "id": report_id,
            "targetType": "post",
            "targetId": "post-001",
            "reporterUserId": "u100",
            "reporterName": "Alice",
            "reason": "spam",
            "status": "resolved",
            "createdAt": datetime.fromisoformat("2026-07-04T00:00:00+00:00"),
        }

    async def fake_moderate_post(db, post_id, req, reviewer_external_user_id):
        captured["moderate"] = (db, post_id, req, reviewer_external_user_id)
        return {
            "id": post_id,
            "title": "t",
            "content": "c",
            "type": "normal",
            "tags": [],
            "userName": "Alice",
            "createdAt": datetime.fromisoformat("2026-07-04T00:00:00+00:00"),
        }

    monkeypatch.setattr(community_api, "create_report", fake_create_report)
    monkeypatch.setattr(community_api, "list_reports", fake_list_reports)
    monkeypatch.setattr(community_api, "resolve_report", fake_resolve_report)
    monkeypatch.setattr(community_api, "moderate_post", fake_moderate_post)
    db = MagicMock()
    report_req = ReportCreateRequest(reason="spam")
    resolve_req = ReportResolveRequest(resolution="reject")
    moderation_req = ModerationRequest(status="hidden")

    created = await community_api.api_create_report("post-001", report_req, externalUserId="u100", userName="Alice", db=db)
    listed = await community_api.api_list_reports(status="pending", targetType="post", db=db)
    resolved = await community_api.api_resolve_report("report-001", resolve_req, reviewerExternalUserId="admin", db=db)
    moderated = await community_api.api_moderate_post("post-001", moderation_req, reviewerExternalUserId="admin", db=db)

    assert created["id"] == "report-001"
    assert listed.total == 1
    assert resolved["status"] == "resolved"
    assert moderated["id"] == "post-001"
    assert captured["create"] == (db, "post-001", report_req, "u100", "Alice")
    assert captured["list"]["status"] == "pending"
    assert captured["resolve"] == (db, "report-001", resolve_req, "admin")
    assert captured["moderate"] == (db, "post-001", moderation_req, "admin")
