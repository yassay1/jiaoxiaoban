from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.session import get_db, AsyncSession
from app.schemas.community import (
    CommentCreateRequest,
    CommentListResponse,
    CommentResponse,
    ModerationRequest,
    PostCreateRequest,
    PostInteractionResponse,
    PostListResponse,
    PostResponse,
    ReportCreateRequest,
    ReportListResponse,
    ReportResolveRequest,
    ReportResponse,
    TaskActionResponse,
    TaskStatusUpdateRequest,
)
from app.services.community_post_service import (
    accept_task,
    cancel_task,
    complete_task,
    create_comment,
    create_post,
    create_report,
    delete_comment,
    delete_post,
    get_post,
    list_comments,
    list_my_participated_tasks,
    list_my_posts,
    list_my_tasks,
    list_posts,
    list_reports,
    list_task_posts,
    moderate_post,
    resolve_report,
    toggle_favorite,
    toggle_like,
    update_task_status,
)
router = APIRouter(prefix="/api/posts", tags=["community"])

@router.get("/tasks", response_model=PostListResponse)
async def api_list_tasks(
    keyword: str | None = None,
    tag: str | None = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=100),
    taskStatus: str | None = None,
    taskCategory: str | None = None,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    posts, total = await list_task_posts(
        db=db,
        keyword=keyword,
        tag=tag,
        external_user_id=externalUserId,
        task_status=taskStatus,
        task_category=taskCategory,
        page=page,
        page_size=pageSize,
    )
    return PostListResponse(posts=posts, total=total)


@router.get("", response_model=PostListResponse)
async def api_list_posts(
    keyword: str | None = None,
    tag: str | None = None,
    postType: str | None = None,
    mine: bool = False,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=100),
    taskStatus: str | None = None,
    taskCategory: str | None = None,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    posts, total = await list_posts(
        db=db,
        keyword=keyword,
        tag=tag,
        post_type=postType,
        mine=mine,
        external_user_id=externalUserId,
        task_status=taskStatus,
        task_category=taskCategory,
        page=page,
        page_size=pageSize,
    )
    return PostListResponse(posts=posts, total=total)


@router.post("", response_model=PostResponse)
async def api_create_post(
    req: PostCreateRequest,
    externalUserId: str = "demo_user",
    userName: str = "演示同学",
    db: AsyncSession = Depends(get_db),
):
    return await create_post(db, req, external_user_id=externalUserId, user_name=userName)




@router.get("/mine", response_model=PostListResponse)
async def api_list_my_posts(
    postType: str | None = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=100),
    taskStatus: str | None = None,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    posts, total = await list_my_posts(
        db=db,
        external_user_id=externalUserId,
        post_type=postType,
        task_status=taskStatus,
        page=page,
        page_size=pageSize,
    )
    return PostListResponse(posts=posts, total=total)


@router.get("/mine/tasks", response_model=PostListResponse)
async def api_list_my_tasks(
    role: str = "all",
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=100),
    taskStatus: str | None = None,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    posts, total = await list_my_tasks(
        db=db,
        external_user_id=externalUserId,
        role=role,
        task_status=taskStatus,
        page=page,
        page_size=pageSize,
    )
    return PostListResponse(posts=posts, total=total)


@router.get("/mine/participated", response_model=PostListResponse)
async def api_list_my_participated_tasks(
    participantStatus: str | None = "accepted",
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=100),
    taskStatus: str | None = None,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    posts, total = await list_my_participated_tasks(
        db=db,
        external_user_id=externalUserId,
        participant_status=participantStatus,
        task_status=taskStatus,
        page=page,
        page_size=pageSize,
    )
    return PostListResponse(posts=posts, total=total)



@router.get("/reports", response_model=ReportListResponse)
async def api_list_reports(
    status: str | None = "pending",
    targetType: str | None = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    reports, total = await list_reports(
        db=db,
        status=status,
        target_type=targetType,
        page=page,
        page_size=pageSize,
    )
    return ReportListResponse(reports=reports, total=total)


@router.post("/reports/{report_id}/resolve", response_model=ReportResponse)
async def api_resolve_report(
    report_id: str,
    req: ReportResolveRequest,
    reviewerExternalUserId: str = "demo_admin",
    db: AsyncSession = Depends(get_db),
):
    report = await resolve_report(db, report_id, req, reviewer_external_user_id=reviewerExternalUserId)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    return report

@router.get("/{post_id}", response_model=PostResponse)
async def api_get_post(
    post_id: str,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    post = await get_post(db, post_id, external_user_id=externalUserId)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return post


@router.delete("/{post_id}")
async def api_delete_post(
    post_id: str,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    ok = await delete_post(db, post_id, external_user_id=externalUserId)
    if not ok:
        raise HTTPException(status_code=404, detail="帖子不存在或无权删除")
    return {"detail": "deleted"}


@router.patch("/{post_id}/task-status", response_model=PostResponse)
async def api_update_task_status(
    post_id: str,
    req: TaskStatusUpdateRequest,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    post = await update_task_status(db, post_id, req.taskStatus, external_user_id=externalUserId)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return post


@router.get("/{post_id}/comments", response_model=CommentListResponse)
async def api_list_comments(
    post_id: str,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await list_comments(db, post_id, page=page, page_size=pageSize)
    if result is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    comments, total = result
    return CommentListResponse(comments=comments, total=total)


@router.post("/{post_id}/comments", response_model=CommentResponse)
async def api_create_comment(
    post_id: str,
    req: CommentCreateRequest,
    externalUserId: str = "demo_user",
    userName: str = "演示同学",
    db: AsyncSession = Depends(get_db),
):
    comment = await create_comment(db, post_id, req, external_user_id=externalUserId, user_name=userName)
    if not comment:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return comment


@router.delete("/{post_id}/comments/{comment_id}")
async def api_delete_comment(
    post_id: str,
    comment_id: str,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    ok = await delete_comment(db, post_id, comment_id, external_user_id=externalUserId)
    if not ok:
        raise HTTPException(status_code=404, detail="评论不存在或无权删除")
    return {"detail": "deleted"}


@router.post("/{post_id}/like", response_model=PostInteractionResponse)
async def api_toggle_like(
    post_id: str,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    result = await toggle_like(db, post_id, external_user_id=externalUserId)
    if not result:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return result


@router.post("/{post_id}/favorite", response_model=PostInteractionResponse)
async def api_toggle_favorite(
    post_id: str,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    result = await toggle_favorite(db, post_id, external_user_id=externalUserId)
    if not result:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return result

@router.post("/{post_id}/accept", response_model=TaskActionResponse)
async def api_accept_task(
    post_id: str,
    externalUserId: str = "demo_user",
    userName: str = "演示同学",
    db: AsyncSession = Depends(get_db),
):
    result = await accept_task(db, post_id, external_user_id=externalUserId, user_name=userName)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在或无法接单")
    return result


@router.post("/{post_id}/cancel", response_model=TaskActionResponse)
async def api_cancel_task(
    post_id: str,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    result = await cancel_task(db, post_id, external_user_id=externalUserId)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在或无权取消")
    return result


@router.post("/{post_id}/complete", response_model=TaskActionResponse)
async def api_complete_task(
    post_id: str,
    externalUserId: str = "demo_user",
    db: AsyncSession = Depends(get_db),
):
    result = await complete_task(db, post_id, external_user_id=externalUserId)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在或无权完成")
    return result

@router.post("/{post_id}/report", response_model=ReportResponse)
async def api_create_report(
    post_id: str,
    req: ReportCreateRequest,
    externalUserId: str = "demo_user",
    userName: str = "演示同学",
    db: AsyncSession = Depends(get_db),
):
    report = await create_report(db, post_id, req, external_user_id=externalUserId, user_name=userName)
    if not report:
        raise HTTPException(status_code=404, detail="post not found or unsupported report target")
    return report


@router.patch("/{post_id}/moderation", response_model=PostResponse)
async def api_moderate_post(
    post_id: str,
    req: ModerationRequest,
    reviewerExternalUserId: str = "demo_admin",
    db: AsyncSession = Depends(get_db),
):
    post = await moderate_post(db, post_id, req, reviewer_external_user_id=reviewerExternalUserId)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    return post