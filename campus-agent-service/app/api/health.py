from fastapi import APIRouter

from app.schemas.common import HealthResponse
from app.services.llm_service import check_llm_configured
from app.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        llm_configured=check_llm_configured(),
        demo_mode=settings.demo_mode,
    )

