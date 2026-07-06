from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConfirmationRequest(BaseModel):
    external_user_id: str = Field(..., min_length=1, max_length=128)
    action_type: str = Field(..., description="动作类型")
    action_summary: str = Field(..., description="动作摘要，用于展示给用户")
    action_detail: dict = Field(default_factory=dict, description="动作详情")
    risk_level: str = Field(default="low", description="风险等级")
    expires_in_seconds: Optional[int] = Field(default=300, description="确认过期时间（秒）")


class ConfirmationResponse(BaseModel):
    confirmation_id: str
    status: str
    action_type: str
    action_summary: str
    risk_level: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class ConfirmationResolveRequest(BaseModel):
    confirmation_id: str = Field(...)
    approved: bool = Field(..., description="用户是否同意")


class ConfirmationResolveResponse(BaseModel):
    confirmation_id: str
    status: str
    approved: bool
    resolved_at: datetime
