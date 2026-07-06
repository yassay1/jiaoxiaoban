from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TaskDraftResponse(BaseModel):
    id: str
    external_user_id: str
    source_post_id: Optional[str] = None
    title: str
    description: str
    task_type: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    status: str
    created_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
