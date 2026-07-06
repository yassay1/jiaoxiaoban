from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SafetyCheckRequest(BaseModel):
    action_type: str = Field(..., description="动作类型：create_task / send_message / call_external_api")
    content: str = Field(..., min_length=1, max_length=8192, description="待检查内容")
    external_user_id: str = Field(..., min_length=1, max_length=128)
    context: dict = Field(default_factory=dict, description="上下文信息")


class SafetyCheckResponse(BaseModel):
    check_id: str
    risk_level: str = Field(..., description="风险等级：low / medium / high / critical")
    risk_reason: Optional[str] = None
    is_blocked: bool = False
    requires_confirmation: bool = False
    checked_at: datetime
