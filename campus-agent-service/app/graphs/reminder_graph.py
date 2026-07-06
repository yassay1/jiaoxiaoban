"""
reminder_graph: 提醒创建流程 (LangGraph StateGraph)

流程:
  reminder_entry → extract_fields
    ├─ 缺少字段 → ask_missing → END
    └─ 字段完整 → create_draft → confirm → create_reminder → END
"""

from typing import TypedDict, Annotated, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from app.chains.reminder_fields_extract_chain import extract_reminder_fields
from app.services.llm_service import LLMNotConfiguredError, LLM_NOT_CONFIGURED_MSG


class ReminderState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    external_user_id: str
    conversation_id: str
    user_message: str

    reminder_fields: dict | None
    missing_fields: list[str]
    draft_id: str | None
    confirmation_id: str | None
    reminder_id: str | None

    response: str | None
    error: str | None
    actions: list


async def node_reminder_entry(state: ReminderState) -> ReminderState:
    state["actions"] = []
    return state


async def node_extract_reminder_fields(state: ReminderState) -> ReminderState:
    try:
        fields = await extract_reminder_fields(state["user_message"])
        state["reminder_fields"] = {
            "title": fields.title,
            "remind_at": fields.remind_at,
            "repeat_rule": fields.repeat_rule,
            "description": fields.description,
        }
        state["missing_fields"] = fields.missing_fields
    except LLMNotConfiguredError:
        state["error"] = LLM_NOT_CONFIGURED_MSG
        state["missing_fields"] = ["LLM not configured"]
    return state


def should_ask_or_confirm(state: ReminderState) -> str:
    if state.get("error"):
        return "return_error"
    if state.get("missing_fields"):
        return "ask_missing"
    return "create_draft"


async def node_ask_missing_reminder_fields(state: ReminderState) -> ReminderState:
    missing = state.get("missing_fields", [])
    fields_str = "、".join(missing)
    state["response"] = f"为了帮你设置提醒，还需要以下信息：{fields_str}。请告诉我吧。"
    state["actions"] = [{"type": "ask_clarification", "missing_fields": missing}]
    return state


async def node_create_reminder_draft(state: ReminderState) -> ReminderState:
    import uuid
    fields = state.get("reminder_fields", {})
    draft_id = f"rdraft_{uuid.uuid4().hex[:12]}"
    state["draft_id"] = draft_id

    title = fields.get("title", "提醒")
    remind_at = fields.get("remind_at", "未指定")
    repeat = fields.get("repeat_rule")
    desc = fields.get("description", "")

    msg = (
        f"⏰ **提醒草稿**\n\n"
        f"**标题**：{title}\n"
        f"**时间**：{remind_at}\n"
    )
    if repeat:
        msg += f"**重复**：{repeat}\n"
    if desc:
        msg += f"**备注**：{desc}\n"
    msg += "\n是否确认创建此提醒？"

    state["response"] = msg
    state["actions"] = [{"type": "confirm_create_reminder", "draft_id": draft_id, "fields": fields}]
    return state


async def node_confirm_reminder(state: ReminderState) -> ReminderState:
    """Interrupt 确认节点：等待用户确认后才创建提醒。"""
    fields = state.get("reminder_fields", {})
    title = fields.get("title", "提醒")

    decision = interrupt({
        "action": "create_reminder",
        "summary": f"确认创建提醒「{title}」",
        "detail": {
            "title": title,
            "remind_at": fields.get("remind_at"),
            "repeat_rule": fields.get("repeat_rule"),
            "description": fields.get("description"),
        },
        "message": f"是否确认创建提醒「{title}」？",
    })

    approved = isinstance(decision, dict) and decision.get("decision") == "approve"

    if approved:
        state["confirmation_id"] = "confirmed"
    else:
        state["response"] = "好的，已取消提醒创建。"
        state["actions"] = [{"type": "cancelled", "action": "create_reminder"}]
    return state


def route_after_reminder_confirm(state: ReminderState) -> str:
    if state.get("confirmation_id") == "confirmed":
        return "create_reminder"
    return "end"


async def node_create_reminder(state: ReminderState) -> ReminderState:
    import uuid
    fields = state.get("reminder_fields", {})
    reminder_id = f"rem_{uuid.uuid4().hex[:12]}"
    state["reminder_id"] = reminder_id
    title = fields.get("title", "提醒")
    state["response"] = f"提醒「{title}」已创建成功！我会在指定时间提醒你。"
    state["actions"] = [{"type": "reminder_created", "reminder_id": reminder_id}]
    return state


async def node_return_error(state: ReminderState) -> ReminderState:
    state["response"] = state.get("error", "处理提醒时出错")
    return state


def build_reminder_graph(checkpointer=None) -> StateGraph:
    workflow = StateGraph(ReminderState)

    workflow.add_node("reminder_entry", node_reminder_entry)
    workflow.add_node("extract_fields", node_extract_reminder_fields)
    workflow.add_node("ask_missing", node_ask_missing_reminder_fields)
    workflow.add_node("create_draft", node_create_reminder_draft)
    workflow.add_node("confirm_reminder", node_confirm_reminder)
    workflow.add_node("create_reminder", node_create_reminder)
    workflow.add_node("return_error", node_return_error)

    workflow.set_entry_point("reminder_entry")
    workflow.add_edge("reminder_entry", "extract_fields")

    workflow.add_conditional_edges("extract_fields", should_ask_or_confirm, {
        "ask_missing": "ask_missing",
        "create_draft": "create_draft",
        "return_error": "return_error",
    })
    workflow.add_edge("ask_missing", END)

    # create_draft → confirm_reminder (interrupt) → create_reminder or END
    workflow.add_edge("create_draft", "confirm_reminder")
    workflow.add_conditional_edges("confirm_reminder", route_after_reminder_confirm, {
        "create_reminder": "create_reminder",
        "end": END,
    })
    workflow.add_edge("create_reminder", END)
    workflow.add_edge("return_error", END)

    return workflow.compile(checkpointer=checkpointer)


reminder_graph = build_reminder_graph()
