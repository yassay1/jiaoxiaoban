from app.chains.safety_check_chain import check_safety
from app.services.llm_service import LLMNotConfiguredError, LLM_NOT_CONFIGURED_MSG


async def perform_safety_check(
    content: str,
    action_type: str,
    external_user_id: str,
    context: dict | None = None,
) -> dict:
    """执行安全检查并返回结构化结果。"""
    try:
        result = await check_safety(content, action_type, context)
        return {
            "risk_level": result.get("risk_level", "low"),
            "risk_reason": result.get("risk_reason", ""),
            "is_blocked": result.get("is_blocked", False),
            "requires_confirmation": result.get("requires_confirmation", False),
        }
    except LLMNotConfiguredError:
        return {
            "risk_level": "error",
            "risk_reason": LLM_NOT_CONFIGURED_MSG,
            "is_blocked": False,
            "requires_confirmation": False,
        }
