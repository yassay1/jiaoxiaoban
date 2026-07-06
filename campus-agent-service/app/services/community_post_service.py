from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CommunityComment,
    CommunityPost,
    CommunityPostFavorite,
    CommunityPostLike,
    CommunityReport,
    CommunityTaskParticipant,
    utc_now,
)
from app.schemas.community import (
    CommentCreateRequest,
    CommentResponse,
    ModerationRequest,
    PostCreateRequest,
    PostInteractionResponse,
    PostResponse,
    ReportCreateRequest,
    ReportResolveRequest,
    ReportResponse,
    TaskActionResponse,
)
DEMO_USER_ID = "demo_user"
DEMO_USER_NAME = "演示同学"

_demo_seeded: bool = False
_seed_lock = asyncio.Lock()


async def ensure_demo_posts(db: AsyncSession) -> None:
    global _demo_seeded
    if _demo_seeded:
        return
    async with _seed_lock:
        if _demo_seeded:
            return
        result = await db.execute(select(func.count(CommunityPost.id)))
        count = result.scalar_one()
        if count:
            _demo_seeded = True
            return
        seeds = [
            CommunityPost(
                external_user_id="demo_user",
                user_name="演示同学",
                title="找学习搭子今晚复习高数",
                content="今晚 7 点在图书馆二楼一起复习高数，主要看极限和积分。",
                post_type="任务帖子",
                tags=["学习搭子", "高数"],
                task_status="待接单",
                task_category="学习搭子",
                task_location="图书馆二楼",
                task_time_text="今晚7点",
                task_reward_type="无偿",
                is_ai_assisted=True,
                source_agent="DEMO_MODE",
            ),
            CommunityPost(
                external_user_id="student_aze",
                user_name="保研学长阿泽",
                title="保研材料准备经验分享",
                content="建议提前整理成绩排名、科研经历、竞赛证明和个人陈述，联系导师时要具体说明研究兴趣。",
                post_type="普通帖子",
                tags=["保研", "经验分享"],
            ),
            CommunityPost(
                external_user_id="demo_user",
                user_name="演示同学",
                title="提醒我明天看教务通知",
                content="担心错过选课退课截止时间，想设置一个提醒。",
                post_type="普通帖子",
                tags=["教务", "提醒"],
                is_ai_assisted=False,
            ),
        ]
        db.add_all(seeds)
        await db.flush()
        _demo_seeded = True


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _to_response(
    post: CommunityPost,
    *,
    liked_by_me: bool = False,
    favorited_by_me: bool = False,
    favorite_count: int = 0,
    comment_count: int = 0,
) -> PostResponse:
    return PostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        type=post.post_type,
        tags=post.tags or [],
        userId=post.external_user_id,
        userName=post.user_name or DEMO_USER_NAME,
        userAvatar=post.user_avatar,
        createdAt=post.created_at or utc_now(),
        isAiAssisted=bool(post.is_ai_assisted),
        sourceAgent=post.source_agent,
        imageUrls=post.image_urls or [],
        likeCount=post.like_count or 0,
        likedByMe=liked_by_me,
        favoriteCount=favorite_count,
        favoritedByMe=favorited_by_me,
        commentCount=comment_count,
        taskStatus=post.task_status,
        taskCategory=post.task_category,
        taskLocation=post.task_location,
        taskTimeText=post.task_time_text,
        taskDeadline=post.task_deadline.isoformat() if post.task_deadline else None,
        taskRewardType=post.task_reward_type,
        taskRewardText=post.task_reward_text,
        taskMaxParticipants=post.task_max_participants,
        taskAcceptedCount=post.task_accepted_count or 0,
    )


def _to_comment_response(comment: CommunityComment) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        postId=comment.post_id,
        content=comment.content,
        userId=comment.external_user_id,
        userName=comment.user_name,
        createdAt=comment.created_at,
    )




def _to_report_response(report: CommunityReport) -> ReportResponse:
    return ReportResponse(
        id=report.id,
        targetType=report.target_type,
        targetId=report.target_id,
        reporterUserId=report.reporter_external_user_id,
        reporterName=report.reporter_name or DEMO_USER_NAME,
        reason=report.reason,
        detail=report.detail,
        status=report.status,
        reviewerUserId=report.reviewer_external_user_id,
        resolution=report.resolution,
        resolutionNote=report.resolution_note,
        createdAt=report.created_at or utc_now(),
        resolvedAt=report.resolved_at,
    )

async def _get_post_model(db: AsyncSession, post_id: str) -> CommunityPost | None:
    result = await db.execute(select(CommunityPost).where(CommunityPost.id == post_id))
    return result.scalar_one_or_none()


async def _count_comments(db: AsyncSession, post_id: str) -> int:
    result = await db.execute(
        select(func.count(CommunityComment.id)).where(
            CommunityComment.post_id == post_id,
            CommunityComment.status == "published",
        )
    )
    return int(result.scalar_one())


async def _count_favorites(db: AsyncSession, post_id: str) -> int:
    result = await db.execute(select(func.count(CommunityPostFavorite.id)).where(CommunityPostFavorite.post_id == post_id))
    return int(result.scalar_one())


async def _count_likes(db: AsyncSession, post_id: str) -> int:
    result = await db.execute(select(func.count(CommunityPostLike.id)).where(CommunityPostLike.post_id == post_id))
    return int(result.scalar_one())


async def _count_accepted_participants(db: AsyncSession, post_id: str) -> int:
    result = await db.execute(
        select(func.count(CommunityTaskParticipant.id)).where(
            CommunityTaskParticipant.post_id == post_id,
            CommunityTaskParticipant.status == "accepted",
        )
    )
    return int(result.scalar_one())


async def _rollback_after_integrity_error(db: AsyncSession) -> None:
    await db.rollback()


async def _exists_like(db: AsyncSession, post_id: str, external_user_id: str) -> bool:
    result = await db.execute(
        select(CommunityPostLike).where(
            CommunityPostLike.post_id == post_id,
            CommunityPostLike.external_user_id == external_user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _exists_favorite(db: AsyncSession, post_id: str, external_user_id: str) -> bool:
    result = await db.execute(
        select(CommunityPostFavorite).where(
            CommunityPostFavorite.post_id == post_id,
            CommunityPostFavorite.external_user_id == external_user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _interaction_response(db: AsyncSession, post_id: str, external_user_id: str) -> PostInteractionResponse | None:
    post = await _get_post_model(db, post_id)
    if not post:
        return None
    like_count = await _count_likes(db, post_id)
    if post.like_count != like_count:
        post.like_count = like_count
        post.updated_at = utc_now()
        await db.flush()
    return PostInteractionResponse(
        postId=post_id,
        likeCount=like_count,
        likedByMe=await _exists_like(db, post_id, external_user_id),
        favoriteCount=await _count_favorites(db, post_id),
        favoritedByMe=await _exists_favorite(db, post_id, external_user_id),
    )


async def _to_response_with_interactions(
    db: AsyncSession,
    post: CommunityPost,
    external_user_id: str,
) -> PostResponse:
    liked_by_me = await _exists_like(db, post.id, external_user_id)
    favorited_by_me = await _exists_favorite(db, post.id, external_user_id)
    favorite_count = await _count_favorites(db, post.id)
    comment_count = await _count_comments(db, post.id)
    return _to_response(
        post,
        liked_by_me=liked_by_me,
        favorited_by_me=favorited_by_me,
        favorite_count=favorite_count,
        comment_count=comment_count,
    )


async def list_posts(
    db: AsyncSession,
    keyword: str | None = None,
    tag: str | None = None,
    post_type: str | None = None,
    mine: bool = False,
    external_user_id: str = DEMO_USER_ID,
    task_status: str | None = None,
    task_category: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PostResponse], int]:
    await ensure_demo_posts(db)
    stmt = select(CommunityPost)
    if not mine:
        stmt = stmt.where(CommunityPost.status == "published")
    if keyword:
        kw = f"%{keyword}%"
        stmt = stmt.where(or_(CommunityPost.title.ilike(kw), CommunityPost.content.ilike(kw)))
    if tag:
        stmt = stmt.where(CommunityPost.tags.any(tag))
    if post_type:
        stmt = stmt.where(CommunityPost.post_type == post_type)
    if mine:
        stmt = stmt.where(CommunityPost.external_user_id == external_user_id)
    if task_status:
        stmt = stmt.where(CommunityPost.task_status == task_status)
    if task_category:
        stmt = stmt.where(CommunityPost.task_category == task_category)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(CommunityPost.created_at.desc()).offset(max(page - 1, 0) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    posts = [await _to_response_with_interactions(db, p, external_user_id) for p in rows]
    return posts, total


async def get_post(db: AsyncSession, post_id: str, external_user_id: str = DEMO_USER_ID) -> PostResponse | None:
    await ensure_demo_posts(db)
    post = await _get_post_model(db, post_id)
    if not post:
        return None
    if post.status != "published" and post.external_user_id != external_user_id:
        return None
    return await _to_response_with_interactions(db, post, external_user_id)


async def create_post(
    db: AsyncSession,
    req: PostCreateRequest,
    external_user_id: str = DEMO_USER_ID,
    user_name: str = DEMO_USER_NAME,
) -> PostResponse:
    if req.sourceAgent and req.sourceAgent.startswith("community_agent:draft_"):
        existing_result = await db.execute(
            select(CommunityPost).where(
                CommunityPost.external_user_id == external_user_id,
                CommunityPost.source_agent == req.sourceAgent,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return await _to_response_with_interactions(db, existing, external_user_id)

    post = CommunityPost(
        external_user_id=external_user_id,
        user_name=user_name,
        title=req.title,
        content=req.content,
        post_type=req.type,
        tags=req.tags or [],
        image_urls=req.imageUrls or [],
        is_ai_assisted=bool(req.isAiAssisted),
        source_agent=req.sourceAgent,
        task_status=req.taskStatus or ("待接单" if req.type == "任务帖子" else None),
        task_category=req.taskCategory,
        task_location=req.taskLocation,
        task_time_text=req.taskTimeText,
        task_deadline=_parse_optional_datetime(req.taskDeadline),
        task_reward_type=req.taskRewardType,
        task_reward_text=req.taskRewardText,
        task_max_participants=req.taskMaxParticipants,
    )
    db.add(post)
    await db.flush()
    return _to_response(post)


async def delete_post(db: AsyncSession, post_id: str, external_user_id: str = DEMO_USER_ID) -> bool:
    post = await _get_post_model(db, post_id)
    if not post or post.external_user_id != external_user_id:
        return False
    await db.delete(post)
    await db.flush()
    return True


async def update_task_status(
    db: AsyncSession,
    post_id: str,
    task_status: str,
    external_user_id: str = DEMO_USER_ID,
) -> PostResponse | None:
    post = await _get_post_model(db, post_id)
    if not post or post.external_user_id != external_user_id:
        return None
    post.task_status = task_status
    post.updated_at = utc_now()
    await db.flush()
    return _to_response(post)


async def list_comments(
    db: AsyncSession,
    post_id: str,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[CommentResponse], int] | None:
    if not await _get_post_model(db, post_id):
        return None
    stmt = select(CommunityComment).where(
        CommunityComment.post_id == post_id,
        CommunityComment.status == "published",
    )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(CommunityComment.created_at.asc()).offset(max(page - 1, 0) * page_size).limit(page_size)
        )
    ).scalars().all()
    return [_to_comment_response(comment) for comment in rows], total


async def create_comment(
    db: AsyncSession,
    post_id: str,
    req: CommentCreateRequest,
    external_user_id: str = DEMO_USER_ID,
    user_name: str = DEMO_USER_NAME,
) -> CommentResponse | None:
    if not await _get_post_model(db, post_id):
        return None
    comment = CommunityComment(
        post_id=post_id,
        external_user_id=external_user_id,
        user_name=user_name,
        content=req.content,
    )
    db.add(comment)
    await db.flush()
    return _to_comment_response(comment)


async def delete_comment(
    db: AsyncSession,
    post_id: str,
    comment_id: str,
    external_user_id: str = DEMO_USER_ID,
) -> bool:
    result = await db.execute(
        select(CommunityComment).where(
            CommunityComment.id == comment_id,
            CommunityComment.post_id == post_id,
        )
    )
    comment = result.scalar_one_or_none()
    if not comment or comment.external_user_id != external_user_id:
        return False
    await db.delete(comment)
    await db.flush()
    return True


async def toggle_like(
    db: AsyncSession,
    post_id: str,
    external_user_id: str = DEMO_USER_ID,
) -> PostInteractionResponse | None:
    post = await _get_post_model(db, post_id)
    if not post:
        return None
    result = await db.execute(
        select(CommunityPostLike).where(
            CommunityPostLike.post_id == post_id,
            CommunityPostLike.external_user_id == external_user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        post.like_count = max((post.like_count or 0) - 1, 0)
    else:
        db.add(CommunityPostLike(post_id=post_id, external_user_id=external_user_id))
        post.like_count = (post.like_count or 0) + 1
    post.updated_at = utc_now()
    try:
        await db.flush()
    except IntegrityError:
        await _rollback_after_integrity_error(db)
    return await _interaction_response(db, post_id, external_user_id)


async def toggle_favorite(
    db: AsyncSession,
    post_id: str,
    external_user_id: str = DEMO_USER_ID,
) -> PostInteractionResponse | None:
    post = await _get_post_model(db, post_id)
    if not post:
        return None
    result = await db.execute(
        select(CommunityPostFavorite).where(
            CommunityPostFavorite.post_id == post_id,
            CommunityPostFavorite.external_user_id == external_user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
    else:
        db.add(CommunityPostFavorite(post_id=post_id, external_user_id=external_user_id))
    try:
        await db.flush()
    except IntegrityError:
        await _rollback_after_integrity_error(db)
    return await _interaction_response(db, post_id, external_user_id)

async def list_task_posts(
    db: AsyncSession,
    keyword: str | None = None,
    tag: str | None = None,
    external_user_id: str = DEMO_USER_ID,
    task_status: str | None = None,
    task_category: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PostResponse], int]:
    return await list_posts(
        db=db,
        keyword=keyword,
        tag=tag,
        post_type="任务帖子",
        mine=False,
        external_user_id=external_user_id,
        task_status=task_status,
        task_category=task_category,
        page=page,
        page_size=page_size,
    )


async def _get_task_participant(
    db: AsyncSession,
    post_id: str,
    external_user_id: str,
) -> CommunityTaskParticipant | None:
    result = await db.execute(
        select(CommunityTaskParticipant).where(
            CommunityTaskParticipant.post_id == post_id,
            CommunityTaskParticipant.external_user_id == external_user_id,
        )
    )
    return result.scalar_one_or_none()


def _is_task_post(post: CommunityPost) -> bool:
    return post.post_type == "任务帖子"


def _task_action_response(post: CommunityPost, action: str) -> TaskActionResponse:
    return TaskActionResponse(
        post=_to_response(post),
        action=action,
        taskStatus=post.task_status,
        taskAcceptedCount=post.task_accepted_count or 0,
    )


async def _accepted_task_response_after_conflict(
    db: AsyncSession,
    post_id: str,
    external_user_id: str,
) -> TaskActionResponse | None:
    post = await _get_post_model(db, post_id)
    participant = await _get_task_participant(db, post_id, external_user_id)
    if not post or not participant or participant.status != "accepted":
        return None
    accepted_count = await _count_accepted_participants(db, post_id)
    if post.task_accepted_count != accepted_count:
        post.task_accepted_count = accepted_count
        post.updated_at = utc_now()
        await db.flush()
    return _task_action_response(post, "accepted")


async def accept_task(
    db: AsyncSession,
    post_id: str,
    external_user_id: str = DEMO_USER_ID,
    user_name: str = DEMO_USER_NAME,
) -> TaskActionResponse | None:
    post = await _get_post_model(db, post_id)
    if not post or not _is_task_post(post) or post.external_user_id == external_user_id:
        return None
    if post.task_status in {"已取消", "已完成"}:
        return None

    participant = await _get_task_participant(db, post_id, external_user_id)
    if participant and participant.status == "accepted":
        return _task_action_response(post, "accepted")

    accepted_count = post.task_accepted_count or 0
    if post.task_max_participants is not None and accepted_count >= post.task_max_participants:
        return None

    if participant:
        participant.status = "accepted"
        participant.user_name = user_name
        participant.updated_at = utc_now()
    else:
        db.add(
            CommunityTaskParticipant(
                post_id=post_id,
                external_user_id=external_user_id,
                user_name=user_name,
                status="accepted",
            )
        )
    post.task_accepted_count = accepted_count + 1
    post.task_status = "进行中"
    post.updated_at = utc_now()
    try:
        await db.flush()
    except IntegrityError:
        await _rollback_after_integrity_error(db)
        return await _accepted_task_response_after_conflict(db, post_id, external_user_id)
    return _task_action_response(post, "accepted")


async def cancel_task(
    db: AsyncSession,
    post_id: str,
    external_user_id: str = DEMO_USER_ID,
) -> TaskActionResponse | None:
    post = await _get_post_model(db, post_id)
    if not post or not _is_task_post(post) or post.task_status == "已完成":
        return None

    if post.external_user_id == external_user_id:
        post.task_status = "已取消"
        post.task_accepted_count = 0
        post.updated_at = utc_now()
        await db.execute(
            update(CommunityTaskParticipant)
            .where(
                CommunityTaskParticipant.post_id == post_id,
                CommunityTaskParticipant.status == "accepted",
            )
            .values(status="cancelled", updated_at=utc_now())
        )
        await db.flush()
        return _task_action_response(post, "cancelled")

    participant = await _get_task_participant(db, post_id, external_user_id)
    if not participant or participant.status != "accepted":
        return None
    participant.status = "cancelled"
    participant.updated_at = utc_now()
    post.task_accepted_count = max((post.task_accepted_count or 0) - 1, 0)
    if post.task_accepted_count == 0 and post.task_status != "已取消":
        post.task_status = "待接单"
    post.updated_at = utc_now()
    await db.flush()
    return _task_action_response(post, "cancelled")


async def complete_task(
    db: AsyncSession,
    post_id: str,
    external_user_id: str = DEMO_USER_ID,
) -> TaskActionResponse | None:
    post = await _get_post_model(db, post_id)
    if not post or not _is_task_post(post) or post.external_user_id != external_user_id:
        return None
    if post.task_status == "已取消":
        return None
    post.task_status = "已完成"
    post.updated_at = utc_now()
    await db.flush()
    return _task_action_response(post, "completed")

async def _list_posts_by_statement(
    db: AsyncSession,
    stmt,
    external_user_id: str,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PostResponse], int]:
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    page_stmt = stmt.order_by(CommunityPost.created_at.desc()).offset(max(page - 1, 0) * page_size).limit(page_size)
    rows = (await db.execute(page_stmt)).scalars().all()
    posts = [await _to_response_with_interactions(db, p, external_user_id) for p in rows]
    return posts, total


async def list_my_posts(
    db: AsyncSession,
    external_user_id: str = DEMO_USER_ID,
    post_type: str | None = None,
    task_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PostResponse], int]:
    stmt = select(CommunityPost).where(CommunityPost.external_user_id == external_user_id)
    if post_type:
        stmt = stmt.where(CommunityPost.post_type == post_type)
    if task_status:
        stmt = stmt.where(CommunityPost.task_status == task_status)
    return await _list_posts_by_statement(db, stmt, external_user_id, page=page, page_size=page_size)


async def list_my_participated_tasks(
    db: AsyncSession,
    external_user_id: str = DEMO_USER_ID,
    participant_status: str | None = "accepted",
    task_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PostResponse], int]:
    stmt = select(CommunityPost).join(
        CommunityTaskParticipant,
        CommunityTaskParticipant.post_id == CommunityPost.id,
    ).where(CommunityTaskParticipant.external_user_id == external_user_id)
    if participant_status:
        stmt = stmt.where(CommunityTaskParticipant.status == participant_status)
    if task_status:
        stmt = stmt.where(CommunityPost.task_status == task_status)
    return await _list_posts_by_statement(db, stmt, external_user_id, page=page, page_size=page_size)


async def list_my_tasks(
    db: AsyncSession,
    external_user_id: str = DEMO_USER_ID,
    role: str = "all",
    task_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PostResponse], int]:
    if role == "published":
        stmt = select(CommunityPost).where(
            CommunityPost.external_user_id == external_user_id,
            CommunityPost.task_status.is_not(None),
        )
    elif role == "participated":
        return await list_my_participated_tasks(
            db,
            external_user_id=external_user_id,
            participant_status="accepted",
            task_status=task_status,
            page=page,
            page_size=page_size,
        )
    else:
        stmt = select(CommunityPost).outerjoin(
            CommunityTaskParticipant,
            CommunityTaskParticipant.post_id == CommunityPost.id,
        ).where(
            or_(
                (CommunityPost.external_user_id == external_user_id) & CommunityPost.task_status.is_not(None),
                CommunityTaskParticipant.external_user_id == external_user_id,
            )
        ).distinct()
    if task_status:
        stmt = stmt.where(CommunityPost.task_status == task_status)
    return await _list_posts_by_statement(db, stmt, external_user_id, page=page, page_size=page_size)

async def create_report(
    db: AsyncSession,
    post_id: str,
    req: ReportCreateRequest,
    external_user_id: str = DEMO_USER_ID,
    user_name: str = DEMO_USER_NAME,
) -> ReportResponse | None:
    if req.targetType != "post":
        return None
    if not await _get_post_model(db, post_id):
        return None
    existing_result = await db.execute(
        select(CommunityReport).where(
            CommunityReport.target_type == req.targetType,
            CommunityReport.target_id == post_id,
            CommunityReport.reporter_external_user_id == external_user_id,
            CommunityReport.status == "pending",
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return _to_report_response(existing)
    report = CommunityReport(
        target_type=req.targetType,
        target_id=post_id,
        reporter_external_user_id=external_user_id,
        reporter_name=user_name,
        reason=req.reason,
        detail=req.detail,
        status="pending",
    )
    db.add(report)
    await db.flush()
    return _to_report_response(report)


async def list_reports(
    db: AsyncSession,
    status: str | None = "pending",
    target_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ReportResponse], int]:
    stmt = select(CommunityReport)
    if status:
        stmt = stmt.where(CommunityReport.status == status)
    if target_type:
        stmt = stmt.where(CommunityReport.target_type == target_type)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    page_stmt = stmt.order_by(CommunityReport.created_at.desc()).offset(max(page - 1, 0) * page_size).limit(page_size)
    rows = (await db.execute(page_stmt)).scalars().all()
    return [_to_report_response(report) for report in rows], total


async def resolve_report(
    db: AsyncSession,
    report_id: str,
    req: ReportResolveRequest,
    reviewer_external_user_id: str = DEMO_USER_ID,
) -> ReportResponse | None:
    result = await db.execute(select(CommunityReport).where(CommunityReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        return None
    if report.status == "resolved":
        return _to_report_response(report)
    report.status = "resolved"
    report.reviewer_external_user_id = reviewer_external_user_id
    report.resolution = req.resolution
    report.resolution_note = req.resolutionNote
    report.resolved_at = utc_now()
    report.updated_at = utc_now()
    if req.postStatus and report.target_type == "post":
        post = await _get_post_model(db, report.target_id)
        if post:
            post.status = req.postStatus
            post.updated_at = utc_now()
    await db.flush()
    return _to_report_response(report)


async def moderate_post(
    db: AsyncSession,
    post_id: str,
    req: ModerationRequest,
    reviewer_external_user_id: str = DEMO_USER_ID,
) -> PostResponse | None:
    post = await _get_post_model(db, post_id)
    if not post:
        return None
    post.status = req.status
    post.updated_at = utc_now()
    await db.flush()
    return _to_response(post)
