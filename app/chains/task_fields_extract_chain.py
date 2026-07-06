import logging
from pydantic import BaseModel, Field, ValidationError
from typing import Optional

from app.services.llm_service import llm_structured_output
from app.utils.json_utils import safe_json_loads

logger = logging.getLogger(__name__)


class HelpTaskFields(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    expected_time: Optional[str] = None
    reward_points: Optional[int] = None
    contact_method: Optional[str] = None
    missing_fields: list[str] = []
    suggested_category: Optional[str] = None
    safety_notes: list[str] = []


TASK_EXTRACT_PROMPT = """你是"交小伴"校园互助平台的求助任务字段提取助手。

从用户的消息中提取求助任务的关键信息。返回 JSON 格式：
{
  "title": "任务标题（简洁明确）",
  "description": "任务详细描述",
  "category": "类别：学习辅导/生活帮助/组队招募/物品借用/代办跑腿/其他",
  "location": "地点（如：东区快递站）",
  "expected_time": "期望时间（如：今晚7点）",
  "reward_points": 悬赏积分（整数，可为null）,
  "contact_method": "联系方式偏好",
  "missing_fields": ["缺失的关键字段"],
  "suggested_category": "建议的类别",
  "safety_notes": ["安全提醒"]
}

如果某个字段无法从消息中提取，设为 null。missing_fields 列出确实需要追问的关键信息。"""


async def extract_help_task_fields(user_message: str) -> HelpTaskFields:
    raw = await llm_structured_output(
        system_prompt=TASK_EXTRACT_PROMPT,
        user_message=user_message,
        temperature=0.3,
    )

    logger.info("task_fields_extract 原始输出：%r", raw)

    try:
        data = safe_json_loads(raw, source="task_fields_extract")
        return HelpTaskFields(**data)
    except (ValueError, ValidationError) as e:
        logger.exception("task_fields_extract 输出解析失败，返回空提取结果。raw=%r", raw)
        return HelpTaskFields(
            missing_fields=["无法解析模型输出"],
            safety_notes=[f"字段提取失败：{e}"],
        )
