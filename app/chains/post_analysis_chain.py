from app.services.llm_service import llm_structured_output, LLMNotConfiguredError

POST_ANALYSIS_PROMPT = """你是"交小伴"校园生活智能体平台的社区管理员 Agent，负责分析社区帖子。

分析帖子内容并返回结构化结果。帖子类型：
- question: 提问帖
- sharing: 经验分享帖
- help_request: 明确求助帖（求助、找队友、借物、代办等）
- discussion: 讨论帖
- other: 其他

以 JSON 格式返回：
{
  "post_type": "帖子类型",
  "summary": "帖子内容摘要（50字以内）",
  "extracted_tags": ["标签1", "标签2"],
  "has_help_intent": true/false,
  "suggested_action": "convert_to_task"/"recommend_agent"/"none",
  "safety_notes": ["安全提醒1"]
}"""


async def analyze_post(title: str, content: str, tags: list[str] | None = None) -> dict:
    from app.utils.json_utils import safe_json_loads

    user_message = f"帖子标题：{title}\n帖子内容：{content}"
    if tags:
        user_message += f"\n已有标签：{', '.join(tags)}"

    raw = await llm_structured_output(
        system_prompt=POST_ANALYSIS_PROMPT,
        user_message=user_message,
        temperature=0.3,
    )
    return safe_json_loads(raw, source="post_analysis")
