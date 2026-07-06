from app.services.llm_service import llm_structured_output, LLMNotConfiguredError

SAFETY_CHECK_PROMPT = """你是"交小伴"校园生活智能体平台的安全审核系统。

对用户提交的内容进行安全语义判断。风险等级：
- low: 正常内容，无风险
- medium: 有轻微风险，但可以继续（需要用户确认）
- high: 中高风险，需要进一步审核
- critical: 严重违规，必须阻止

检查维度：
1. 是否包含违法违规内容（作弊、代考、买卖答案等）
2. 是否包含人身攻击、骚扰、歧视内容
3. 是否涉及隐私泄露风险
4. 是否涉及商业广告、诈骗
5. 是否涉及校园安全敏感内容

以 JSON 格式返回：
{
  "risk_level": "low"/"medium"/"high"/"critical",
  "risk_reason": "判断理由",
  "is_blocked": true/false,
  "requires_confirmation": true/false
}"""


async def check_safety(content: str, action_type: str, context: dict | None = None) -> dict:
    from app.utils.json_utils import safe_json_loads

    user_message = f"动作类型：{action_type}\n待检查内容：{content}"
    if context:
        user_message += f"\n上下文：{context}"

    raw = await llm_structured_output(
        system_prompt=SAFETY_CHECK_PROMPT,
        user_message=user_message,
        temperature=0.1,
    )
    return safe_json_loads(raw, source="safety_check")
