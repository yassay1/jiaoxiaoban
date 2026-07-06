import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import ConfirmationRecord, utc_now


def _uuid() -> str:
    return str(uuid.uuid4())


async def create_confirmation(
    db: AsyncSession,
    external_user_id: str,
    action_type: str,
    action_summary: str,
    action_detail: dict | None = None,
    risk_level: str = "low",
    expires_in_seconds: int = 300,
) -> ConfirmationRecord:
    now = utc_now()
    record = ConfirmationRecord(
        id=_uuid(),
        external_user_id=external_user_id,
        action_type=action_type,
        action_summary=action_summary,
        action_detail=action_detail or {},
        risk_level=risk_level,
        status="pending",
        expires_at=now + timedelta(seconds=expires_in_seconds),
    )
    db.add(record)
    await db.flush()
    return record


async def resolve_confirmation(
    db: AsyncSession,
    confirmation_id: str,
    approved: bool,
) -> ConfirmationRecord | None:
    result = await db.execute(
        select(ConfirmationRecord).where(ConfirmationRecord.id == confirmation_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    record.status = "confirmed" if approved else "cancelled"
    record.confirmed_at = utc_now()
    await db.flush()
    return record


async def get_confirmation(
    db: AsyncSession,
    confirmation_id: str,
) -> ConfirmationRecord | None:
    result = await db.execute(
        select(ConfirmationRecord).where(ConfirmationRecord.id == confirmation_id)
    )
    return result.scalar_one_or_none()
