import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Message


def _uuid() -> str:
    return str(uuid.uuid4())


async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> Message:
    msg = Message(
        id=_uuid(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        metadata_=metadata or {},
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_recent_messages(
    db: AsyncSession,
    conversation_id: str,
    limit: int = 10,
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
