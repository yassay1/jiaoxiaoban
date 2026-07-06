from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AgentInfo(BaseModel):
    agent_name: str
    display_name: str
    description: str
    capabilities: list[str] = Field(default_factory=list)


class AgentRecommendRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096, description="用户需求描述")
    external_user_id: str = Field(..., min_length=1, max_length=128)


class AgentRecommendResponse(BaseModel):
    recommended_agents: list[AgentInfo]
    reason: str
    conversation_id: Optional[str] = None


class AgentChatRequest(BaseModel):
    agent_name: str = Field(..., description="目标 Agent 名称")
    message: str = Field(..., min_length=1, max_length=4096)
    conversation_id: Optional[str] = None
    session_id: Optional[str] = Field(None, description="专业 Agent 会话 ID")
    external_user_id: str = Field(..., min_length=1, max_length=128)


class AgentChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    run_id: Optional[str] = None
    agent_name: str
    role: str = "assistant"
    content: str
    boundary_reminder: Optional[str] = None
    created_at: datetime
