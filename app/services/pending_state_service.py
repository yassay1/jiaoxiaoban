import json
from datetime import datetime, timezone, timedelta

from app.services.memory_service import memory_service


PENDING_KEY_PREFIX = "pending"
DEFAULT_TTL = 3600  # 1 小时


def _pending_key(external_user_id: str, conversation_id: str) -> str:
    return f"{PENDING_KEY_PREFIX}:{external_user_id}:{conversation_id}"


async def save_pending_state(
    external_user_id: str,
    conversation_id: str,
    flow_type: str,
    status: str,
    payload: dict | None = None,
    draft_id: str | None = None,
    confirmation_id: str | None = None,
    ttl: int = DEFAULT_TTL,
) -> dict:
    state = {
        "pending_id": f"pending_{_uuid()}",
        "flow_type": flow_type,
        "status": status,
        "external_user_id": external_user_id,
        "conversation_id": conversation_id,
        "draft_id": draft_id,
        "confirmation_id": confirmation_id,
        "payload": payload or {},
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat(),
    }
    await memory_service.set_session_state(
        session_id=_pending_key(external_user_id, conversation_id),
        key="state",
        value=state,
        ttl=ttl,
    )
    return state


async def get_pending_state(
    external_user_id: str,
    conversation_id: str,
) -> dict | None:
    return await memory_service.get_session_state(
        session_id=_pending_key(external_user_id, conversation_id),
        key="state",
    )


async def clear_pending_state(
    external_user_id: str,
    conversation_id: str,
) -> None:
    redis = await memory_service._get_redis()
    key = _pending_key(external_user_id, conversation_id)
    full_key = f"session:{key}:state"
    await redis.delete(full_key)


def _uuid() -> str:
    import uuid
    return str(uuid.uuid4())
