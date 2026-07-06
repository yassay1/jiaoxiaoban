from app.services.llm_service import llm_structured_output, LLMNotConfiguredError

TASK_DRAFT_PROMPT = """你是"交小伴"校园生活智能体平台的社区管理员 Agent，负责将帖子转为互助任务草稿。

根据帖子内容生成一个结构化的互助任务草稿。任务草稿应该：
- 标题简洁明确
- 描述包含：背景、需求、期望完成时间、对帮助者的要求
- 标注任务类型和标签

以 JSON 格式返回：
{
  "title": "任务标题",
  "description": "任务详细描述",
  "task_type": "学习辅导"/"生活帮助"/"组队招募"/"物品借用"/"代办跑腿"/"其他",
  "tags": ["标签1", "标签2"],
  "deadline_suggestion": "建议截止日期（YYYY-MM-DD格式，可为null）",
  "missing_info": ["需要追问的缺失信息"],
  "safety_notes": ["安全提醒"]
}"""


async def generate_task_draft(title: str, content: str, tags: list[str] | None = None) -> dict:
    from app.utils.json_utils import safe_json_loads

    user_message = f"帖子标题：{title}\n帖子内容：{content}"
    if tags:
        user_message += f"\n已有标签：{', '.join(tags)}"

    raw = await llm_structured_output(
        system_prompt=TASK_DRAFT_PROMPT,
        user_message=user_message,
        temperature=0.5,
    )
    return safe_json_loads(raw, source="task_draft")
