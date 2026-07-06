from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PostAnalyzeRequest(BaseModel):
    post_id: str = Field(..., description="社区帖子 ID")
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1, max_length=8192)
    author_external_user_id: str = Field(..., min_length=1, max_length=128)
    tags: list[str] = Field(default_factory=list)


class PostAnalyzeResponse(BaseModel):
    post_id: str
    post_type: str = Field(..., description="帖子类型：question / sharing / help_request / discussion / other")
    summary: str
    extracted_tags: list[str] = Field(default_factory=list)
    has_help_intent: bool = False
    suggested_action: str = Field(..., description="建议动作：convert_to_task / recommend_agent / none")
    safety_notes: list[str] = Field(default_factory=list)


class ConvertPostToTaskRequest(BaseModel):
    post_id: str = Field(..., description="来源帖子 ID")
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1, max_length=8192)
    external_user_id: str = Field(..., min_length=1, max_length=128)
    tags: list[str] = Field(default_factory=list)


class ConvertPostToTaskResponse(BaseModel):
    post_id: str
    task_draft_id: str
    title: str
    description: str
    task_type: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    deadline_suggestion: Optional[datetime] = None
    safety_check_passed: bool = False
    safety_notes: list[str] = Field(default_factory=list)
    needs_confirmation: bool = True
    created_task_id: Optional[str] = None
