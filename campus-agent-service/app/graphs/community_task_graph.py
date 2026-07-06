"""
community_task_graph: 帖子转互助任务流程

PostInput → PostUnderstanding → HelpIntentDetection → TaskDraftGeneration →
SafetyCheck → UserConfirmation → CallCommunityCreateTaskAPI → ReturnTaskResult
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from app.chains.post_analysis_chain import analyze_post
from app.chains.task_draft_chain import generate_task_draft
from app.chains.safety_check_chain import check_safety
from app.services.llm_service import LLMNotConfiguredError, LLM_NOT_CONFIGURED_MSG


class CommunityTaskState(TypedDict):
    messages: Annotated[list, add_messages]
    post_id: str
    title: str
    content: str
    external_user_id: str
    tags: list[str]
    post_type: str | None
    summary: str | None
    has_help_intent: bool
    task_draft: dict | None
    safety_result: dict | None
    needs_confirmation: bool
    confirmed: bool
    created_task_id: str | None
    response: str | None
    error: str | None


async def node_post_understanding(state: CommunityTaskState) -> CommunityTaskState:
    try:
        result = await analyze_post(state["title"], state["content"], state.get("tags"))
        state["post_type"] = result["post_type"]
        state["summary"] = result["summary"]
        state["has_help_intent"] = result["has_help_intent"]
    except LLMNotConfiguredError:
        state["error"] = LLM_NOT_CONFIGURED_MSG
    return state


async def node_help_intent_detection(state: CommunityTaskState) -> CommunityTaskState:
    if state.get("error"):
        return state
    if not state.get("has_help_intent", False):
        state["response"] = "该帖子未检测到明确的互助意图，不建议转为任务。"
    return state


def should_continue_task(state: CommunityTaskState) -> str:
    if state.get("error") or state.get("response"):
        return "end"
    if state.get("has_help_intent"):
        return "generate_task"
    return "end"


async def node_task_draft_generation(state: CommunityTaskState) -> CommunityTaskState:
    try:
        draft = await generate_task_draft(state["title"], state["content"], state.get("tags"))
        state["task_draft"] = draft
    except LLMNotConfiguredError:
        state["error"] = LLM_NOT_CONFIGURED_MSG
    return state


async def node_safety_check(state: CommunityTaskState) -> CommunityTaskState:
    draft = state.get("task_draft", {})
    content_to_check = f"{draft.get('title', '')}\n{draft.get('description', '')}"
    try:
        result = await check_safety(content_to_check, "create_task")
        state["safety_result"] = result
        if result.get("is_blocked"):
            state["response"] = f"安全检查未通过：{result.get('risk_reason', '')}"
        else:
            state["needs_confirmation"] = result.get("requires_confirmation", True)
    except LLMNotConfiguredError:
        state["error"] = LLM_NOT_CONFIGURED_MSG
    return state


async def node_user_confirmation(state: CommunityTaskState) -> CommunityTaskState:
    if not state.get("needs_confirmation", False):
        state["confirmed"] = True
    return state


async def node_create_task_via_community(state: CommunityTaskState) -> CommunityTaskState:
    if not state.get("confirmed", False):
        state["response"] = "等待用户确认中..."
        return state
    state["created_task_id"] = None
    state["response"] = "任务草稿已生成，待真实社区接口正式创建任务。"
    return state


async def node_return_result(state: CommunityTaskState) -> CommunityTaskState:
    if state.get("error"):
        state["response"] = state["error"]
    elif not state.get("response"):
        state["response"] = "任务草稿处理完成。"
    return state


def build_community_task_graph() -> StateGraph:
    workflow = StateGraph(CommunityTaskState)

    workflow.add_node("post_understanding", node_post_understanding)
    workflow.add_node("help_intent_detection", node_help_intent_detection)
    workflow.add_node("task_draft_generation", node_task_draft_generation)
    workflow.add_node("safety_check", node_safety_check)
    workflow.add_node("user_confirmation", node_user_confirmation)
    workflow.add_node("create_task_via_community", node_create_task_via_community)
    workflow.add_node("return_result", node_return_result)

    workflow.set_entry_point("post_understanding")
    workflow.add_edge("post_understanding", "help_intent_detection")
    workflow.add_conditional_edges("help_intent_detection", should_continue_task, {
        "generate_task": "task_draft_generation",
        "end": "return_result",
    })
    workflow.add_edge("task_draft_generation", "safety_check")
    workflow.add_edge("safety_check", "user_confirmation")
    workflow.add_edge("user_confirmation", "create_task_via_community")
    workflow.add_edge("create_task_via_community", "return_result")
    workflow.add_edge("return_result", END)

    return workflow.compile()


community_task_graph = build_community_task_graph()

