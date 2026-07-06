"""
safety_graph: 安全检查流程

ActionRequest → LLMSafetyJudge → RiskLevelDecision → RecordSafetyCheck
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from app.chains.safety_check_chain import check_safety
from app.services.llm_service import LLMNotConfiguredError, LLM_NOT_CONFIGURED_MSG


class SafetyState(TypedDict):
    messages: Annotated[list, add_messages]
    action_type: str
    content: str
    external_user_id: str
    context: dict | None
    risk_level: str | None
    risk_reason: str | None
    is_blocked: bool
    requires_confirmation: bool
    check_id: str | None
    error: str | None


async def node_safety_judge(state: SafetyState) -> SafetyState:
    try:
        result = await check_safety(
            content=state["content"],
            action_type=state["action_type"],
            context=state.get("context"),
        )
        state["risk_level"] = result["risk_level"]
        state["risk_reason"] = result["risk_reason"]
        state["is_blocked"] = result["is_blocked"]
        state["requires_confirmation"] = result["requires_confirmation"]
    except LLMNotConfiguredError:
        state["error"] = LLM_NOT_CONFIGURED_MSG
        state["risk_level"] = "error"
    return state


def risk_decision(state: SafetyState) -> str:
    if state.get("is_blocked"):
        return "block"
    if state.get("requires_confirmation"):
        return "confirm"
    return "pass"


async def node_record_check(state: SafetyState) -> SafetyState:
    return state


def build_safety_graph() -> StateGraph:
    workflow = StateGraph(SafetyState)

    workflow.add_node("safety_judge", node_safety_judge)
    workflow.add_node("record_check", node_record_check)

    workflow.set_entry_point("safety_judge")
    workflow.add_edge("safety_judge", "record_check")
    workflow.add_edge("record_check", END)

    return workflow.compile()


safety_graph = build_safety_graph()
