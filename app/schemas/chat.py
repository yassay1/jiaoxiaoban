from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096, description="用户消息")
    conversation_id: Optional[str] = Field(None, description="会话 ID，为空则新建会话")
    external_user_id: str = Field(..., min_length=1, max_length=128, description="外部用户 ID")


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    run_id: Optional[str] = None
    role: str = "assistant"
    content: str
    agent_name: Optional[str] = None
    actions: list[dict] = Field(default_factory=list, description="推荐的动作列表")
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    external_user_id: str
    title: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
