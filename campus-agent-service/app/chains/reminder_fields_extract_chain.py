import logging
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
from datetime import datetime

from app.services.llm_service import llm_structured_output
from app.utils.json_utils import safe_json_loads

logger = logging.getLogger(__name__)


class ReminderFields(BaseModel):
    title: Optional[str] = None
    remind_at: Optional[str] = None
    repeat_rule: Optional[str] = None
    description: Optional[str] = None
    missing_fields: list[str] = []


REMINDER_EXTRACT_PROMPT = """你是"交小伴"的提醒创建助手。从用户消息中提取提醒信息。

时间解析规则：
- "明天早上八点" → "2026-05-25T08:00:00"
- "今晚7点" → "2026-05-24T19:00:00"
- "下周一上午10点" → 对应日期
- "每天" → 重复规则 "daily"
- "每周一" → 重复规则 "weekly:monday"
- 当前日期为 2026-05-24

返回 JSON 格式：
{
  "title": "提醒标题",
  "remind_at": "ISO 8601 格式时间（可为null）",
  "repeat_rule": "daily/weekly:xxx/monthly:xxx/null",
  "description": "提醒备注说明",
  "missing_fields": ["缺失的关键字段，如：提醒时间"]
}"""


async def extract_reminder_fields(user_message: str) -> ReminderFields:
    raw = await llm_structured_output(
        system_prompt=REMINDER_EXTRACT_PROMPT,
        user_message=user_message,
        temperature=0.2,
    )

    logger.info("reminder_fields_extract 原始输出：%r", raw)

    try:
        data = safe_json_loads(raw, source="reminder_fields_extract")
        return ReminderFields(**data)
    except (ValueError, ValidationError) as e:
        logger.exception("reminder_fields_extract 输出解析失败，返回空提取结果。raw=%r", raw)
        return ReminderFields(
            missing_fields=["无法解析模型输出"],
        )
