"""
community_agent_subgraph: 社区求助任务子代理 (LangGraph StateGraph)

处理三类操作：
  - create_help_task: 创建求助任务
  - delete_own_help_task: 删除自己的求助任务
  - search_help_task: 查找求助任务
"""

from typing import TypedDict, Annotated, Literal
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from app.chains.task_fields_extract_chain import extract_help_task_fields
from app.services.llm_service import LLMNotConfiguredError, LLM_NOT_CONFIGURED_MSG
from app.services.community_service_adapter import (
    search_help_tasks,
    search_my_help_tasks,
    publish_help_task,
    delete_help_task,
    HelpTaskSearchQuery,
)
from app.utils.shared import public_error_message


class CommunityAgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    external_user_id: str
    conversation_id: str
    community_intent: str  # create_help_task / delete_own_help_task / search_help_task
    user_message: str

    # 任务字段
    task_fields: dict | None
    task_draft_id: str | None
    missing_fields: list[str]
    confirmation_id: str | None

    # 搜索结果
    search_results: list[dict]
    formatted_results: str | None

    # 输出
    response: str | None
    error: str | None
    actions: list


async def node_community_entry(state: CommunityAgentState) -> CommunityAgentState:
    if "actions" not in state:
        state["actions"] = []
    return state


def route_community_intent(state: CommunityAgentState) -> Literal[
    "create_help_task_extract",
    "delete_help_task_search",
    "search_help_task_execute",
]:
    intent = state.get("community_intent", "search_help_task")
    route_map = {
        "create_help_task": "create_help_task_extract",
        "delete_own_help_task": "delete_help_task_search",
        "search_help_task": "search_help_task_execute",
    }
    return route_map.get(intent, "search_help_task_execute")


# === 创建求助任务流程 ===

async def node_create_task_extract(state: CommunityAgentState) -> CommunityAgentState:
    try:
        fields = await extract_help_task_fields(state["user_message"])
        state["task_fields"] = {
            "title": fields.title,
            "description": fields.description,
            "category": fields.category,
            "location": fields.location,
            "expected_time": fields.expected_time,
            "reward_points": fields.reward_points,
            "contact_method": fields.contact_method,
            "safety_notes": fields.safety_notes,
        }
        state["missing_fields"] = fields.missing_fields
    except LLMNotConfiguredError:
        state["error"] = LLM_NOT_CONFIGURED_MSG
    return state


def should_ask_or_draft(state: CommunityAgentState) -> str:
    if state.get("error"):
        return "return_error"
    if state.get("missing_fields"):
        return "ask_missing_fields"
    return "create_draft"


async def node_ask_missing_fields(state: CommunityAgentState) -> CommunityAgentState:
    missing = state.get("missing_fields", [])
    fields_str = "、".join(missing)
    state["response"] = f"为了帮你更好地创建求助任务，还需要补充以下信息：{fields_str}。请告诉我这些信息吧。"
    state["actions"] = [{"type": "ask_clarification", "missing_fields": missing}]
    return state


async def node_create_task_draft(state: CommunityAgentState) -> CommunityAgentState:
    import uuid
    fields = state.get("task_fields", {})
    draft_id = f"draft_{uuid.uuid4().hex[:12]}"
    state["task_draft_id"] = draft_id
    title = fields.get("title", "求助任务")
    desc = fields.get("description", "")
    state["response"] = (
        f"📋 **求助任务草稿**\n\n"
        f"**标题**：{title}\n"
        f"**描述**：{desc}\n"
        f"**类别**：{fields.get('category', '未指定')}\n"
        f"**地点**：{fields.get('location', '未指定')}\n"
        f"**期望时间**：{fields.get('expected_time', '未指定')}\n\n"
        f"是否确认发布此求助任务？"
    )
    state["actions"] = [{"type": "confirm_create_task", "draft_id": draft_id, "task_fields": fields}]
    return state


async def node_confirm_publish(state: CommunityAgentState) -> CommunityAgentState:
    fields = state.get("task_fields", {})
    title = fields.get("title", "求助任务")
    decision = interrupt({
        "action": "confirm_publish_task",
        "summary": f"确认发布求助任务「{title}」",
        "detail": {
            "draft_id": state.get("task_draft_id"),
            "task_fields": fields,
        },
        "message": f"是否确认发布求助任务「{title}」？",
    })

    if isinstance(decision, dict) and decision.get("decision") == "approve":
        state["confirmation_id"] = "confirmed"
        return state
    state["confirmation_id"] = "cancelled"
    state["response"] = "好的，已取消发布。还有其他需要帮助的吗？"
    state["actions"] = [{"type": "task_cancelled", "draft_id": state.get("task_draft_id")}]
    return state


def route_after_confirm_publish(state: CommunityAgentState) -> Literal["publish_task", "return_cancelled"]:
    if state.get("confirmation_id") == "confirmed":
        return "publish_task"
    return "return_cancelled"


async def node_publish_task(state: CommunityAgentState) -> CommunityAgentState:
    fields = state.get("task_fields", {})
    if state.get("confirmation_id") != "confirmed":
        state["response"] = "发布求助任务前需要先获得用户确认。"
        state["actions"] = [{"type": "confirmation_required", "action": "confirm_publish_task"}]
        return state
    try:
        result = await publish_help_task(
            title=fields.get("title", "求助任务"),
            description=fields.get("description", ""),
            external_user_id=state["external_user_id"],
            category=fields.get("category"),
            idempotency_key=state.get("task_draft_id"),
        )
        state["response"] = f"你的求助任务已成功发布！任务 ID：{result.task_id}"
        state["actions"] = [{"type": "task_published", "task_id": result.task_id}]
    except Exception as e:
        state["error"] = str(e)
        state["response"] = public_error_message()
    return state


async def node_create_task_error(state: CommunityAgentState) -> CommunityAgentState:
    state["response"] = state.get("error", "处理求助任务时出错")
    return state


# === 删除求助任务流程 ===

async def node_delete_task_search(state: CommunityAgentState) -> CommunityAgentState:
    try:
        results = await search_my_help_tasks(state["external_user_id"])
        state["search_results"] = [
            {
                "task_id": t.task_id,
                "title": t.title,
                "description": t.description,
                "category": t.category,
                "status": t.status,
                "created_at": t.created_at,
            }
            for t in results
        ]
        if not state["search_results"]:
            state["response"] = "你目前没有发布过求助任务。"
        else:
            lines = ["你当前发布的求助任务："]
            for t in state["search_results"]:
                lines.append(f"- [{t['task_id']}] {t['title']}（{t['status']}）")
            lines.append("\n请告诉我你想删除哪个任务？可以告诉任务 ID 或标题。")
            state["response"] = "\n".join(lines)
    except Exception as e:
        state["error"] = str(e)
    return state


async def node_delete_task_execute(state: CommunityAgentState) -> CommunityAgentState:
    if state.get("error"):
        state["response"] = public_error_message()
        return state

    tasks = state.get("search_results", [])
    if not tasks:
        state["response"] = "未找到可以删除的任务。"
        return state

    # 尝试从消息中匹配 task_id 或标题关键词
    msg = state["user_message"].lower()
    matched = None
    for t in tasks:
        task_id = t["task_id"].lower()
        title = t["title"].lower()
        if task_id in msg or title in msg or any(part and part in msg for part in title.split()):
            matched = t
            break

    if not matched:
        state["response"] = "请确认你想删除哪个任务，可以告诉我任务 ID 或标题。"
        return state

    decision = interrupt({
        "action": "confirm_delete_task",
        "summary": f"确认删除任务「{matched['title']}」",
        "detail": {
            "task_id": matched["task_id"],
            "task_title": matched["title"],
        },
        "message": f"是否确认删除任务「{matched['title']}」？",
    })

    if isinstance(decision, dict) and decision.get("decision") == "approve":
        state["confirmation_id"] = "confirmed"
    else:
        state["confirmation_id"] = "cancelled"
        state["response"] = "好的，已取消删除。还有其他需要帮助的吗？"
        state["actions"] = [{"type": "task_delete_cancelled", "task_id": matched["task_id"]}]
        return state

    try:
        result = await delete_help_task(state["external_user_id"], matched["task_id"])
        state["response"] = f"任务「{matched['title']}」已成功删除。"
        state["actions"] = [{"type": "task_deleted", "task_id": matched["task_id"]}]
    except Exception as e:
        state["error"] = str(e)
        state["response"] = public_error_message()
    return state


# === 查找求助任务流程 ===

async def node_search_task_execute(state: CommunityAgentState) -> CommunityAgentState:
    try:
        query = HelpTaskSearchQuery(keyword=state["user_message"], limit=10)
        results = await search_help_tasks(query)

        if not results:
            state["response"] = "没有找到相关的求助任务。你可以尝试换个关键词搜索。"
            return state

        lines = ["找到以下相关求助任务：\n"]
        for i, t in enumerate(results, 1):
            lines.append(
                f"{i}. **{t.title}** — {t.category or '未分类'}\n"
                f"   {t.description[:80]}...\n"
                f"   状态：{t.status} | 任务 ID：{t.task_id}\n"
            )
        state["response"] = "\n".join(lines)
        state["actions"] = [{"type": "search_results", "count": len(results)}]
    except Exception as e:
        state["error"] = str(e)
        state["response"] = public_error_message()
    return state


async def node_return_error(state: CommunityAgentState) -> CommunityAgentState:
    state["response"] = public_error_message()
    return state


def build_community_agent_subgraph() -> StateGraph:
    workflow = StateGraph(CommunityAgentState)

    # 入口与路由
    workflow.add_node("community_entry", node_community_entry)

    # 创建任务流程
    workflow.add_node("create_help_task_extract", node_create_task_extract)
    workflow.add_node("ask_missing_fields", node_ask_missing_fields)
    workflow.add_node("create_task_draft", node_create_task_draft)
    workflow.add_node("confirm_publish", node_confirm_publish)
    workflow.add_node("publish_task", node_publish_task)
    workflow.add_node("create_task_error", node_create_task_error)

    # 删除任务流程
    workflow.add_node("delete_help_task_search", node_delete_task_search)
    workflow.add_node("delete_help_task_execute", node_delete_task_execute)

    # 查找任务流程
    workflow.add_node("search_help_task_execute", node_search_task_execute)

    # 通用错误
    workflow.add_node("return_error", node_return_error)

    workflow.set_entry_point("community_entry")

    workflow.add_conditional_edges("community_entry", route_community_intent, {
        "create_help_task_extract": "create_help_task_extract",
        "delete_help_task_search": "delete_help_task_search",
        "search_help_task_execute": "search_help_task_execute",
    })

    # 创建任务条件分支
    workflow.add_conditional_edges("create_help_task_extract", should_ask_or_draft, {
        "ask_missing_fields": "ask_missing_fields",
        "create_draft": "create_task_draft",
        "return_error": "create_task_error",
    })
    workflow.add_edge("ask_missing_fields", END)
    workflow.add_edge("create_task_draft", "confirm_publish")
    workflow.add_conditional_edges("confirm_publish", route_after_confirm_publish, {
        "publish_task": "publish_task",
        "return_cancelled": END,
    })
    workflow.add_edge("publish_task", END)
    workflow.add_edge("create_task_error", END)

    # 删除任务
    workflow.add_edge("delete_help_task_search", "delete_help_task_execute")
    workflow.add_edge("delete_help_task_execute", END)

    # 查找任务
    workflow.add_edge("search_help_task_execute", END)

    # 错误
    workflow.add_edge("return_error", END)

    return workflow.compile()


community_agent_subgraph = build_community_agent_subgraph()
