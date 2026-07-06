from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.safety import SafetyCheckRequest, SafetyCheckResponse
from app.services.safety_service import perform_safety_check

router = APIRouter(prefix="/api/safety", tags=["safety"])


@router.post("/check", response_model=SafetyCheckResponse)
async def safety_check(req: SafetyCheckRequest):
    result = await perform_safety_check(
        content=req.content,
        action_type=req.action_type,
        external_user_id=req.external_user_id,
        context=req.context,
    )
    return SafetyCheckResponse(
        check_id="sc_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        risk_level=result["risk_level"],
        risk_reason=result["risk_reason"],
        is_blocked=result["is_blocked"],
        requires_confirmation=result["requires_confirmation"],
        checked_at=datetime.now(timezone.utc),
    )
