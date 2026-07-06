from app.services.llm_service import llm_structured_output, LLMNotConfiguredError

INTENT_ROUTER_PROMPT = """你是"交小伴"校园生活智能体平台的私人助理，负责理解用户需求并判断意图。

你的任务是分析用户输入，判断用户意图并决定下一步动作。

可能的意图类型：
- direct_answer: 用户问了一个可以直接回答的问题（问候、闲聊、简单咨询）
- recommend_agent: 用户的问题需要专业 Agent 来解答（教务、保研、学业、生活）
- create_task: 用户表达了互助需求（找资料、求帮助、组队、借东西等）
- ask_clarification: 用户表达模糊，需要追问澄清
- safety_concern: 用户输入涉及安全风险（违规内容、敏感请求等）

请分析以下用户输入，并以 JSON 格式返回：
{
  "intent": "意图类型",
  "confidence": 0.0-1.0,
  "reasoning": "判断理由",
  "suggested_agent": null 或 "teaching_agent"/"postgraduate_agent"/"science_agent"/"life_agent",
  "clarification_question": null 或 "需要追问的问题"
}"""


async def route_intent(user_message: str) -> dict:
    from app.utils.json_utils import safe_json_loads

    raw = await llm_structured_output(
        system_prompt=INTENT_ROUTER_PROMPT,
        user_message=user_message,
        temperature=0.3,
    )
    return safe_json_loads(raw, source="intent_router")
