from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.schemas.confirmation import (
    ConfirmationRequest,
    ConfirmationResponse,
    ConfirmationResolveRequest,
    ConfirmationResolveResponse,
)

router = APIRouter(prefix="/api/confirmations", tags=["confirmations"])

# 内存确认记录存储（DB 版本在 confirmation_service 中）
_confirmations: dict[str, dict] = {}
_MAX_CONFIRMATIONS_SIZE = 10_000


def _cleanup_expired() -> None:
    now = datetime.now(timezone.utc)
    expired = [cid for cid, r in _confirmations.items() if r.get("expires_at") and r["expires_at"] < now]
    for cid in expired:
        del _confirmations[cid]
    if len(_confirmations) > _MAX_CONFIRMATIONS_SIZE:
        keys_to_remove = list(_confirmations.keys())[:len(_confirmations) // 2]
        for key in keys_to_remove:
            del _confirmations[key]


@router.post("", response_model=ConfirmationResponse)
async def create_confirmation(req: ConfirmationRequest):
    _cleanup_expired()
    cid = f"confirm_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=req.expires_in_seconds or 300)
    _confirmations[cid] = {
        "confirmation_id": cid,
        "status": "pending",
        "action_type": req.action_type,
        "action_summary": req.action_summary,
        "risk_level": req.risk_level,
        "created_at": now,
        "expires_at": expires,
    }
    return ConfirmationResponse(
        confirmation_id=cid,
        status="pending",
        action_type=req.action_type,
        action_summary=req.action_summary,
        risk_level=req.risk_level,
        created_at=now,
        expires_at=expires,
    )


@router.post("/resolve", response_model=ConfirmationResolveResponse)
async def resolve_confirmation(req: ConfirmationResolveRequest):
    _cleanup_expired()
    record = _confirmations.get(req.confirmation_id)
    if not record:
        return ConfirmationResolveResponse(
            confirmation_id=req.confirmation_id,
            status="not_found",
            approved=False,
            resolved_at=datetime.now(timezone.utc),
        )
    record["status"] = "approved" if req.approved else "rejected"
    return ConfirmationResolveResponse(
        confirmation_id=req.confirmation_id,
        status=record["status"],
        approved=req.approved,
        resolved_at=datetime.now(timezone.utc),
    )
