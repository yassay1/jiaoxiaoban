from pydantic import BaseModel, Field
from typing import Optional


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    llm_configured: bool = False
    demo_mode: bool = False

