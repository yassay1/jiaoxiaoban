import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Conversation


def _uuid() -> str:
    return str(uuid.uuid4())


async def create_conversation(
    db: AsyncSession,
    external_user_id: str,
    agent_config_id: str | None = None,
    title: str | None = None,
) -> Conversation:
    conv = Conversation(
        id=_uuid(),
        external_user_id=external_user_id,
        agent_config_id=agent_config_id,
        title=title,
        status="active",
    )
    db.add(conv)
    await db.flush()
    return conv


async def get_conversation(db: AsyncSession, conversation_id: str) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_conversation(
    db: AsyncSession,
    external_user_id: str,
    conversation_id: str | None = None,
) -> Conversation:
    if conversation_id:
        conv = await get_conversation(db, conversation_id)
        if conv:
            return conv
    return await create_conversation(db, external_user_id)
