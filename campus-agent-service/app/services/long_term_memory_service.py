"""Long-term memory persisted in PostgreSQL (user_memories table).

Phase 4: LLM-driven memory extraction, context formatting, and integration
with the assistant conversation flow.
"""

import inspect
import json
import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import UserMemory
from app.services.llm_service import llm_chat, check_llm_configured, LLMNotConfiguredError

logger = logging.getLogger(__name__)

MEMORY_EXTRACT_PROMPT = """你是一个记忆提取助手。分析以下对话，提取需要记住的关键信息。

提取规则：
1. 提取用户的个人信息、偏好、背景（如：专业、年级、目标、兴趣）
2. 提取重要的事实和决定（如：计划、截止日期、承诺）
3. 只提取有意义、可能在未来对话中有用的信息
4. 不要提取闲聊内容或一次性问答
5. 每条记忆应该是简洁的一句话

返回 JSON 格式：
{
  "memories": [
    {"content": "用户是计算机科学专业大三学生", "type": "fact", "importance": 0.8},
    {"content": "用户计划参加2026年秋季保研夏令营", "type": "plan", "importance": 0.9}
  ]
}

如果没有值得记住的信息，返回 {"memories": []}

对话内容：
"""


async def extract_memories_from_conversation(
    user_message: str,
    assistant_response: str,
    existing_memories: list[str] | None = None,
) -> list[dict]:
    """Use LLM to extract long-term memories from a conversation turn.

    Phase 4: Stage 5 — automatic memory extraction.
    Returns list of {content, type, importance} dicts.
    """
    if not check_llm_configured():
        return []

    existing_text = ""
    if existing_memories:
        existing_text = "\n用户已有的记忆（避免重复）：\n" + "\n".join(f"- {m}" for m in existing_memories)

    prompt = (
        MEMORY_EXTRACT_PROMPT
        + f"\n用户消息：{user_message}\n\n助手回复：{assistant_response}"
        + existing_text
    )

    try:
        raw = await llm_chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        # Parse JSON response
        json_text = raw.strip()
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0].strip()
        data = json.loads(json_text)
        return data.get("memories", [])
    except Exception as e:
        logger.warning("Memory extraction failed: %s", e)
        return []


async def save_user_memory(
    db: AsyncSession,
    external_user_id: str,
    content: str,
    memory_type: str = "fact",
    source: str | None = None,
    importance: float = 0.5,
    metadata: dict | None = None,
) -> UserMemory:
    memory = UserMemory(
        id=str(uuid.uuid4()),
        external_user_id=external_user_id,
        memory_type=memory_type,
        content=content,
        source=source,
        importance=importance,
        metadata_=metadata or {},
    )
    add_result = db.add(memory)
    if inspect.isawaitable(add_result):
        await add_result
    await db.flush()
    return memory


async def get_user_memories(
    db: AsyncSession,
    external_user_id: str,
    memory_type: str | None = None,
    limit: int = 20,
) -> list[UserMemory]:
    stmt = select(UserMemory).where(UserMemory.external_user_id == external_user_id)
    if memory_type:
        stmt = stmt.where(UserMemory.memory_type == memory_type)
    stmt = stmt.order_by(UserMemory.importance.desc()).limit(limit)
    result = await db.execute(stmt)
    scalars = result.scalars()
    if inspect.isawaitable(scalars):
        scalars = await scalars
    rows = scalars.all()
    if inspect.isawaitable(rows):
        rows = await rows
    return list(rows)


async def delete_user_memory(db: AsyncSession, memory_id: str) -> bool:
    result = await db.execute(select(UserMemory).where(UserMemory.id == memory_id))
    memory = result.scalar_one_or_none()
    if memory:
        await db.delete(memory)
        await db.flush()
        return True
    return False


async def format_memories_for_context(
    db: AsyncSession,
    external_user_id: str,
    limit: int = 10,
) -> str:
    """Format user memories as context text for LLM prompt injection.

    Phase 4: inject memories into conversation context.
    """
    memories = await get_user_memories(db, external_user_id, limit=limit)
    if not memories:
        return ""

    lines = ["## 用户信息与历史记忆（长期记忆）"]
    for m in memories:
        type_label = {"fact": "事实", "preference": "偏好", "plan": "计划", "note": "备注"}.get(m.memory_type, m.memory_type)
        lines.append(f"- [{type_label}] {m.content}")
    return "\n".join(lines)


async def auto_save_memories_from_turn(
    db: AsyncSession,
    external_user_id: str,
    user_message: str,
    assistant_response: str,
) -> int:
    """Extract and auto-save memories from a conversation turn. Phase 4."""
    existing = await get_user_memories(db, external_user_id, limit=50)
    existing_contents = [m.content for m in existing]

    extracted = await extract_memories_from_conversation(
        user_message=user_message,
        assistant_response=assistant_response,
        existing_memories=existing_contents,
    )

    saved = 0
    for mem_data in extracted:
        content = mem_data.get("content", "").strip()
        if not content or len(content) < 4:
            continue
        # Avoid duplicates
        if any(content == ec for ec in existing_contents):
            continue
        try:
            await save_user_memory(
                db=db,
                external_user_id=external_user_id,
                content=content,
                memory_type=mem_data.get("type", "fact"),
                source="auto_extract",
                importance=float(mem_data.get("importance", 0.5)),
            )
            saved += 1
        except Exception as e:
            logger.warning("Failed to save memory: %s", e)

    if saved:
        logger.info("Auto-saved %d memories for user %s", saved, external_user_id)
    return saved
