from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PostCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(default="", max_length=8192)
    type: str = Field(default="普通帖子")
    tags: list[str] = Field(default_factory=list)
    imageUrls: list[str] | None = None
    isAiAssisted: bool | None = None
    sourceAgent: str | None = None
    taskStatus: str | None = None
    taskCategory: str | None = None
    taskLocation: str | None = None
    taskTimeText: str | None = None
    taskDeadline: str | None = None
    taskRewardType: str | None = None
    taskRewardText: str | None = None
    taskMaxParticipants: int | None = None


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    type: str
    tags: list[str]
    userId: str | None = None
    userName: str
    userAvatar: str | None = None
    createdAt: datetime
    isAiAssisted: bool = False
    sourceAgent: str | None = None
    imageUrls: list[str] = Field(default_factory=list)
    likeCount: int = 0
    likedByMe: bool = False
    favoriteCount: int = 0
    favoritedByMe: bool = False
    commentCount: int = 0
    taskStatus: str | None = None
    taskCategory: str | None = None
    taskLocation: str | None = None
    taskTimeText: str | None = None
    taskDeadline: str | None = None
    taskRewardType: str | None = None
    taskRewardText: str | None = None
    taskMaxParticipants: int | None = None
    taskAcceptedCount: int | None = 0
    publisherReputationScore: int | None = 100
    publisherReputationLevel: str | None = "良好"


class PostListResponse(BaseModel):
    posts: list[PostResponse]
    total: int


class TaskStatusUpdateRequest(BaseModel):
    taskStatus: str = Field(..., min_length=1, max_length=32)


class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2048)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    postId: str
    content: str
    userId: str
    userName: str
    createdAt: datetime


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
    total: int


class PostInteractionResponse(BaseModel):
    postId: str
    likeCount: int = 0
    likedByMe: bool = False
    favoriteCount: int = 0
    favoritedByMe: bool = False

class TaskActionResponse(BaseModel):
    post: PostResponse
    action: str
    taskStatus: str | None = None
    taskAcceptedCount: int = 0

class ReportCreateRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=128)
    detail: str | None = Field(default=None, max_length=2048)
    targetType: str = Field(default="post", max_length=32)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    targetType: str
    targetId: str
    reporterUserId: str
    reporterName: str
    reason: str
    detail: str | None = None
    status: str
    reviewerUserId: str | None = None
    resolution: str | None = None
    resolutionNote: str | None = None
    createdAt: datetime
    resolvedAt: datetime | None = None


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int


class ReportResolveRequest(BaseModel):
    resolution: str = Field(..., min_length=1, max_length=64)
    resolutionNote: str | None = Field(default=None, max_length=2048)
    postStatus: str | None = Field(default=None, max_length=32)


class ModerationRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    reason: str | None = Field(default=None, max_length=2048)