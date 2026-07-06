"""
assistant_graph: 私人助理 Agent 主流程 (LangGraph StateGraph)

流程:
  START → create_run → load_memory → save_user_msg
  → assistant_planner → route_by_plan
    ├─ direct_chat_with_product_rag → END
    ├─ professional_agent_dispatch → confirm_check → END (interrupt) → action → END
    ├─ community_agent → confirm_check → END (interrupt) → action → END
"""

from typing import TypedDict, Annotated, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from app.chains.assistant_planner_chain import plan_assistant_action, AssistantPlan
from app.chains.direct_chat_chain import direct_chat
from app.graphs.community_agent_subgraph import community_agent_subgraph
from app.services.llm_service import LLMNotConfiguredError, LLM_NOT_CONFIGURED_MSG


class AssistantState(TypedDict, total=False):
    run_id: str
    conversation_id: str
    external_user_id: str
    user_message: str

    recent_messages: list[dict]
    memory_context: dict
    product_rag_context: list[dict]
    pending_state: dict | None

    assistant_plan: dict | None
    route_result: dict | None

    final_response: str | None
    navigation_action: dict | None
    confirmations: list[dict]
    tool_calls: list[dict]
    errors: list[dict]
    # 兼容旧版字段
    messages: Annotated[list, add_messages]

    intent: str | None
    confidence: float | None
    execution_mode: str | None
    suggested_agent: str | None
    clarification_question: str | None
    response: str | None
    actions: list
    error: str | None
    community_intent: str | None

    # Interrupt 相关
    needs_confirm: bool
    confirm_action: str | None
    confirm_summary: str | None
    confirm_detail: dict | None


async def node_create_run(state: AssistantState) -> AssistantState:
    import uuid
    state["run_id"] = str(uuid.uuid4())
    state["errors"] = []
    state["confirmations"] = []
    state["tool_calls"] = []
    state["actions"] = []
    state["needs_confirm"] = False
    state["confirm_action"] = None
    state["confirm_summary"] = None
    state["confirm_detail"] = None
    return state


async def node_load_memory(state: AssistantState) -> AssistantState:
    if "recent_messages" not in state or state.get("recent_messages") is None:
        state["recent_messages"] = []
    if "memory_context" not in state or state.get("memory_context") is None:
        state["memory_context"] = {}
    if "product_rag_context" not in state or state.get("product_rag_context") is None:
        state["product_rag_context"] = []
    if "pending_state" not in state or state.get("pending_state") is None:
        state["pending_state"] = None
    return state


async def node_save_user_message(state: AssistantState) -> AssistantState:
    return state


async def node_assistant_planner(state: AssistantState) -> AssistantState:
    try:
        plan: AssistantPlan = await plan_assistant_action(state["user_message"])
        state["assistant_plan"] = {
            "intent": plan.intent,
            "execution_mode": plan.execution_mode,
            "target_agent": plan.target_agent,
            "need_confirmation": plan.need_confirmation,
            "confidence": plan.confidence,
            "slots": plan.slots,
            "reason": plan.reason,
            "route": plan.route,
            "need_clarification": plan.need_clarification,
            "clarification_question": plan.clarification_question,
            "community_intent": plan.community_intent,
            "planned_tools": plan.planned_tools,
        }
        state["intent"] = plan.intent
        state["execution_mode"] = plan.execution_mode
        state["confidence"] = plan.confidence
        state["suggested_agent"] = plan.target_agent
        state["clarification_question"] = plan.clarification_question
        state["community_intent"] = plan.community_intent
    except LLMNotConfiguredError:
        state["error"] = LLM_NOT_CONFIGURED_MSG
        state["assistant_plan"] = {
            "intent": "direct_chat",
            "execution_mode": "direct",
            "route": "direct_chat_with_product_rag",
            "reason": "LLM not configured",
        }
    except Exception as e:
        state["errors"] = state.get("errors", [])
        state["errors"].append({
            "node": "assistant_planner",
            "error": str(e),
        })
        state["assistant_plan"] = {
            "intent": "direct_chat",
            "execution_mode": "direct",
            "route": "direct_chat_with_product_rag",
            "confidence": 0.2,
            "slots": {},
            "need_clarification": False,
            "clarification_question": None,
            "need_confirmation": False,
            "target_agent": None,
            "community_intent": None,
            "planned_tools": [],
            "reason": f"assistant_planner 执行失败，降级为普通聊天：{e}",
        }
        state["intent"] = "direct_chat"
        state["execution_mode"] = "direct"
        state["confidence"] = 0.2
        state["suggested_agent"] = None
        state["clarification_question"] = None
        state["community_intent"] = None
    return state


def route_by_plan(state: AssistantState) -> Literal[
    "direct_chat_with_product_rag",
    "professional_agent_dispatch",
    "community_agent",
]:
    if state.get("error"):
        return "direct_chat_with_product_rag"
    plan = state.get("assistant_plan", {})
    execution_mode = plan.get("execution_mode")
    intent = plan.get("intent")

    if execution_mode == "handoff" and intent == "professional_consult":
        return "professional_agent_dispatch"
    if execution_mode == "workflow" and str(intent).startswith("community_"):
        return "community_agent"
    if execution_mode in {"direct", "clarify"}:
        return "direct_chat_with_product_rag"

    route = plan.get("route", "direct_chat_with_product_rag")
    route_map = {
        "direct_chat_with_product_rag": "direct_chat_with_product_rag",
        "professional_agent_dispatch": "professional_agent_dispatch",
        "community_agent": "community_agent",
    }
    return route_map.get(route, "direct_chat_with_product_rag")


async def node_direct_chat(state: AssistantState) -> AssistantState:
    if state.get("error"):
        state["response"] = state["error"]
        state["final_response"] = state["error"]
        return state
    try:
        recent = state.get("recent_messages", [])
        answer = await direct_chat(
            state["user_message"],
            recent_messages=recent,
            memory_context=state.get("memory_context", {}),
            product_rag_context=state.get("product_rag_context", []),
        )
        state["response"] = answer
        state["final_response"] = answer
    except LLMNotConfiguredError:
        state["response"] = LLM_NOT_CONFIGURED_MSG
        state["final_response"] = LLM_NOT_CONFIGURED_MSG
    return state


async def node_professional_agent_dispatch(state: AssistantState) -> AssistantState:
    target = state.get("suggested_agent", "teaching_agent")
    display_names = {
        "teaching_agent": "教学科石老师",
        "postgraduate_agent": "保研学长阿泽",
        "science_agent": "理科学霸小林",
        "life_agent": "生活辅导员友老师",
    }
    display = display_names.get(target, target)
    state["navigation_action"] = {
        "action_type": "navigate",
        "target_page": "professional_agent_chat",
        "target_agent": target,
        "agent_session_id": None,
        "handoff_context": state.get("user_message", ""),
        "display_name": display,
    }
    state["needs_confirm"] = True
    state["confirm_action"] = "handoff_professional_agent"
    state["confirm_summary"] = f"即将跳转到{display}"
    state["confirm_detail"] = {"target_agent": target, "display_name": display}
    msg = f"我建议让{display}来回答这个问题。是否确认跳转？"
    state["response"] = msg
    state["final_response"] = msg
    state["actions"] = [{"type": "handoff", "target_agent": target, "needs_confirm": True}]
    return state


async def node_community_agent_entry(state: AssistantState) -> AssistantState:
    intent = state.get("community_intent", "")
    # 社区 workflow 自己负责创建/删除的确认；这里不做外层重复确认。
    state["needs_confirm"] = False
    action_labels = {
        "create_help_task": "整理求助任务草稿",
        "delete_own_help_task": "查找待删除的求助任务",
        "search_help_task": "查找求助任务",
    }
    label = action_labels.get(intent, "处理社区任务")
    state["response"] = f"正在为你{label}..."
    state["final_response"] = state["response"]
    state["actions"] = [{"type": "community_agent", "intent": intent}]
    return state


async def node_confirm_check(state: AssistantState) -> AssistantState:
    """Interrupt 确认节点。如果需要确认，暂停等待用户决策。"""
    if not state.get("needs_confirm"):
        return state

    confirm_action = state.get("confirm_action", "unknown")
    confirm_summary = state.get("confirm_summary", "")
    confirm_detail = state.get("confirm_detail") or {}

    decision = interrupt({
        "action": confirm_action,
        "summary": confirm_summary,
        "detail": confirm_detail,
        "message": f"请确认: {confirm_summary}",
    })

    if isinstance(decision, dict):
        approved = decision.get("decision") == "approve"
    else:
        approved = False

    if approved:
        state["needs_confirm"] = False
        state["confirmations"] = state.get("confirmations", [])
        state["confirmations"].append({
            "action": confirm_action,
            "confirmed": True,
            "summary": confirm_summary,
        })
    else:
        state["needs_confirm"] = False
        state["response"] = "好的，已取消该操作。还有其他需要帮助的吗？"
        state["final_response"] = state["response"]
        state["navigation_action"] = None
        state["actions"] = [{"type": "cancelled", "action": confirm_action}]

    return state


async def node_execute_confirmed_action(state: AssistantState) -> AssistantState:
    """根据 plan 执行已确认或无需确认的操作。"""
    plan = state.get("assistant_plan", {})
    intent = plan.get("intent")
    execution_mode = plan.get("execution_mode")

    if execution_mode == "handoff" and intent == "professional_consult":
        confirmations = state.get("confirmations", [])
        if not confirmations or not confirmations[-1].get("confirmed"):
            state["navigation_action"] = None
            state["response"] = "转接专业 Agent 前需要先获得用户确认。"
            state["final_response"] = state["response"]
            state["actions"] = [{"type": "confirmation_required", "action": "handoff_professional_agent"}]
            return state
        target = state.get("suggested_agent", "teaching_agent")
        display_names = {
            "teaching_agent": "教学科石老师",
            "postgraduate_agent": "保研学长阿泽",
            "science_agent": "理科学霸小林",
            "life_agent": "生活辅导员友老师",
        }
        display = display_names.get(target, target)
        state["navigation_action"] = {
            "action_type": "navigate",
            "target_page": "professional_agent_chat",
            "target_agent": target,
            "agent_session_id": None,
            "handoff_context": state.get("user_message", ""),
            "display_name": display,
        }
        msg = f"已为你创建{display}的对话，点击即可继续。"
        state["response"] = msg
        state["final_response"] = msg
        state["actions"] = [{"type": "handoff", "target_agent": target, "confirmed": True}]
    elif execution_mode == "workflow" and str(intent).startswith("community_"):
        intent = state.get("community_intent", "")
        sub_state = {
            "external_user_id": state.get("external_user_id", ""),
            "conversation_id": state.get("conversation_id", ""),
            "community_intent": intent,
            "user_message": state.get("user_message", ""),
            "messages": [],
        }
        sub_result = await community_agent_subgraph.ainvoke(sub_state)
        state["response"] = sub_result.get("response", "社区操作完成。")
        state["final_response"] = state["response"]
        state["actions"] = sub_result.get("actions", [{"type": "community_agent", "intent": intent, "confirmed": True}])
    return state


async def node_save_assistant_message(state: AssistantState) -> AssistantState:
    return state


def route_after_confirm(state: AssistantState) -> Literal[
    "direct_chat_with_product_rag",
    "execute_confirmed_action",
]:
    """确认后路由：如果用户拒绝了，直接结束；如果批准了，执行对应操作。"""
    if state.get("actions") and state["actions"][-1].get("type") == "cancelled":
        return "direct_chat_with_product_rag"

    confirmations = state.get("confirmations", [])
    if confirmations and confirmations[-1].get("confirmed"):
        return "execute_confirmed_action"
    plan = state.get("assistant_plan", {})
    intent = plan.get("intent")
    if plan.get("execution_mode") == "workflow" and str(intent).startswith("community_") and not state.get("needs_confirm"):
        return "execute_confirmed_action"

    return "direct_chat_with_product_rag"

def build_assistant_graph(checkpointer=None) -> StateGraph:
    workflow = StateGraph(AssistantState)

    workflow.add_node("create_run", node_create_run)
    workflow.add_node("load_memory", node_load_memory)
    workflow.add_node("save_user_message", node_save_user_message)
    workflow.add_node("assistant_planner", node_assistant_planner)
    workflow.add_node("direct_chat_with_product_rag", node_direct_chat)
    workflow.add_node("professional_agent_dispatch", node_professional_agent_dispatch)
    workflow.add_node("community_agent", node_community_agent_entry)
    workflow.add_node("confirm_check", node_confirm_check)
    workflow.add_node("execute_confirmed_action", node_execute_confirmed_action)
    workflow.add_node("save_assistant_message", node_save_assistant_message)

    workflow.set_entry_point("create_run")
    workflow.add_edge("create_run", "load_memory")
    workflow.add_edge("load_memory", "save_user_message")
    workflow.add_edge("save_user_message", "assistant_planner")

    workflow.add_conditional_edges("assistant_planner", route_by_plan, {
        "direct_chat_with_product_rag": "direct_chat_with_product_rag",
        "professional_agent_dispatch": "professional_agent_dispatch",
        "community_agent": "community_agent",
    })

    for node in ["professional_agent_dispatch", "community_agent"]:
        workflow.add_edge(node, "confirm_check")

    workflow.add_conditional_edges("confirm_check", route_after_confirm, {
        "direct_chat_with_product_rag": "save_assistant_message",
        "execute_confirmed_action": "execute_confirmed_action",
    })

    workflow.add_edge("execute_confirmed_action", "save_assistant_message")
    workflow.add_edge("direct_chat_with_product_rag", "save_assistant_message")
    workflow.add_edge("save_assistant_message", END)

    return workflow.compile(checkpointer=checkpointer)


assistant_graph = build_assistant_graph()
