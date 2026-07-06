import logging
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.services.llm_service import llm_structured_output
from app.utils.json_utils import safe_json_loads

logger = logging.getLogger(__name__)


AssistantIntent = Literal[
    "direct_chat",
    "professional_consult",
    "community_create_task",
    "community_search_task",
    "community_delete_task",
    "unknown",
]
ExecutionMode = Literal["direct", "handoff", "workflow", "clarify"]
TargetAgent = Literal[
    "teaching_agent",
    "postgraduate_agent",
    "science_agent",
    "life_agent",
]
LegacyRoute = Literal[
    "direct_chat_with_product_rag",
    "professional_agent_dispatch",
    "community_agent",
]
CommunityIntent = Literal[
    "create_help_task",
    "delete_own_help_task",
    "search_help_task",
]

_INTENT_TO_ROUTE: dict[str, str] = {
    "direct_chat": "direct_chat_with_product_rag",
    "professional_consult": "professional_agent_dispatch",
    "community_create_task": "community_agent",
    "community_search_task": "community_agent",
    "community_delete_task": "community_agent",
    "unknown": "direct_chat_with_product_rag",
}
_ROUTE_TO_PLAN: dict[str, tuple[str, str]] = {
    "direct_chat_with_product_rag": ("direct_chat", "direct"),
    "professional_agent_dispatch": ("professional_consult", "handoff"),
    "community_agent": ("community_search_task", "workflow"),
}
_INTENT_TO_COMMUNITY_INTENT: dict[str, str | None] = {
    "community_create_task": "create_help_task",
    "community_search_task": "search_help_task",
    "community_delete_task": "delete_own_help_task",
}
_COMMUNITY_INTENT_TO_INTENT: dict[str, str] = {
    "create_help_task": "community_create_task",
    "search_help_task": "community_search_task",
    "delete_own_help_task": "community_delete_task",
}


class AssistantPlan(BaseModel):
    intent: AssistantIntent
    execution_mode: ExecutionMode
    target_agent: Optional[TargetAgent] = None
    need_confirmation: bool = False
    confidence: float = Field(ge=0, le=1)
    slots: dict[str, Any] = Field(default_factory=dict)
    reason: str

    # Compatibility fields used by the current assistant graph and frontend adapter.
    route: LegacyRoute
    need_clarification: bool = False
    clarification_question: Optional[str] = None
    community_intent: Optional[CommunityIntent] = None
    planned_tools: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def fill_compatibility_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        data = dict(data)
        route = data.get("route")
        community_intent = data.get("community_intent")

        if community_intent and data.get("intent") not in _INTENT_TO_ROUTE:
            data["intent"] = _COMMUNITY_INTENT_TO_INTENT.get(community_intent, "community_search_task")

        if data.get("intent") not in _INTENT_TO_ROUTE and route in _ROUTE_TO_PLAN:
            intent, execution_mode = _ROUTE_TO_PLAN[route]
            data["intent"] = intent
            data.setdefault("execution_mode", execution_mode)

        intent = data.get("intent", "unknown")
        if data.get("execution_mode") is None:
            if intent == "professional_consult":
                data["execution_mode"] = "handoff"
            elif str(intent).startswith("community_"):
                data["execution_mode"] = "workflow"
            elif intent == "unknown":
                data["execution_mode"] = "clarify"
            else:
                data["execution_mode"] = "direct"

        if data.get("route") is None:
            data["route"] = _INTENT_TO_ROUTE.get(intent, "direct_chat_with_product_rag")
        if data.get("community_intent") is None:
            data["community_intent"] = _INTENT_TO_COMMUNITY_INTENT.get(intent)

        data["need_clarification"] = data.get("execution_mode") == "clarify"
        if intent in {"community_create_task", "community_delete_task"}:
            data["need_confirmation"] = True
        elif intent in {"community_search_task", "professional_consult", "direct_chat"}:
            data.setdefault("need_confirmation", False)

        data.setdefault("slots", {})
        data.setdefault("planned_tools", [])
        data.setdefault("reason", "assistant planner produced a structured execution plan")
        return data


ASSISTANT_PLANNER_PROMPT = """你是“交小伴”校园生活智能体平台的私人助理编排器。

你的任务不是直接回答所有问题，而是输出下一步执行计划。请优先表达架构意图：
- 普通问候、产品介绍、轻量校园问题：direct_chat + direct
- 教务、保研、理科学习、校园生活服务咨询：professional_consult + handoff，并选择 target_agent
- 社区互助任务创建、搜索、删除：对应 community_*_task + workflow
- 意图或关键信息不足：unknown + clarify

专业 Agent:
- teaching_agent: 教务规则、培养方案、选课、考试、办事流程
- postgraduate_agent: 保研规划、竞赛科研、简历、升学时间线
- science_agent: 高数、线代、大物、编程、课程学习辅导
- life_agent: 宿舍、食堂、校医院、后勤、校园生活服务

社区任务 Workflow:
- community_create_task: 帮我发求助、发布任务、找人帮我做具体事情
- community_search_task: 搜索/查找互助任务、有没有人一起拼车/组队/互助
- community_delete_task: 删除/取消我自己的求助任务

创建和删除社区内容需要确认；搜索、普通聊天、专业咨询通常不需要确认。
提醒功能不是当前主线。不要把提醒作为主路由；用户明确要提醒时返回 unknown + clarify，并说明当前主线不处理提醒。

只返回 JSON，不要返回 Markdown。格式如下：
{
  "intent": "direct_chat | professional_consult | community_create_task | community_search_task | community_delete_task | unknown",
  "execution_mode": "direct | handoff | workflow | clarify",
  "target_agent": null 或 "teaching_agent"/"postgraduate_agent"/"science_agent"/"life_agent",
  "need_confirmation": true/false,
  "confidence": 0.0-1.0,
  "slots": {"可选": "从用户输入中抽取的结构化信息"},
  "reason": "简短说明判断依据",
  "clarification_question": null 或 "需要追问的问题"
}"""


async def plan_assistant_action(user_message: str) -> AssistantPlan:
    raw = await llm_structured_output(
        system_prompt=ASSISTANT_PLANNER_PROMPT,
        user_message=user_message,
        output_schema={
            "intent": "direct_chat | professional_consult | community_create_task | community_search_task | community_delete_task | unknown",
            "execution_mode": "direct | handoff | workflow | clarify",
            "target_agent": "teaching_agent | postgraduate_agent | science_agent | life_agent | null",
            "need_confirmation": "boolean",
            "confidence": "number between 0 and 1",
            "slots": "object",
            "reason": "string",
            "clarification_question": "string or null",
        },
        temperature=0.3,
    )

    logger.info("assistant_planner raw output: %r", raw)

    try:
        data = safe_json_loads(raw, source="assistant_planner")
        return AssistantPlan(**data)
    except (ValueError, ValidationError) as e:
        logger.exception("assistant_planner output parse failed; falling back to direct chat. raw=%r", raw)

        return AssistantPlan(
            intent="direct_chat",
            execution_mode="direct",
            target_agent=None,
            need_confirmation=False,
            confidence=0.3,
            slots={},
            reason=f"planner output parse failed; fell back to direct chat: {e}",
            route="direct_chat_with_product_rag",
            need_clarification=False,
            clarification_question=None,
            community_intent=None,
            planned_tools=[],
        )
