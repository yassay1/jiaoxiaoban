from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.assistant import assistant_chat
from app.api.agents import agent_chat
from app.config.settings import get_settings
from app.schemas.agent import AgentChatRequest
from app.schemas.chat import ChatRequest
from app.services.demo_fixture_service import build_demo_fixture_response
from app.services.llm_service import check_llm_configured, LLM_NOT_CONFIGURED_MSG
from app.utils.shared import (
    AGENT_DISPLAY_NAMES,
    BACKEND_TO_FRONTEND_AGENT,
    FRONTEND_TO_BACKEND_AGENT,
    now_iso,
)

_message_store: dict[str, list[dict[str, Any]]] = {}
_MAX_MESSAGES_PER_AGENT = 100


def _append_message(agent_id: str, role: str, content: str, image_urls: list[str] | None = None) -> None:
    now = now_iso()
    bucket = _message_store.setdefault(agent_id, [])
    bucket.append({
        "id": f"msg_{len(bucket) + 1}_{now}",
        "agentId": agent_id,
        "role": role,
        "content": content,
        "imageUrls": image_urls or [],
        "createdAt": now,
    })
    if len(bucket) > _MAX_MESSAGES_PER_AGENT:
        del bucket[:-_MAX_MESSAGES_PER_AGENT]


def get_frontend_agent_messages(agent_id: str) -> list[dict[str, Any]]:
    return list(_message_store.get(agent_id, []))


def clear_frontend_agent_messages(agent_id: str) -> int:
    deleted = len(_message_store.get(agent_id, []))
    _message_store[agent_id] = []
    return deleted


def _task_draft_from_message(message: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    detail = detail or {}
    fields = detail.get("task_fields") if isinstance(detail.get("task_fields"), dict) else detail
    title = fields.get("title") or detail.get("title") or detail.get("message") or message or "校园互助任务"
    title = str(title).strip()[:40] or "校园互助任务"
    return {
        "type": "CREATE_TASK_DRAFT",
        "payload": {
            "title": title,
            "content": str(fields.get("description") or detail.get("message") or message or title),
            "postType": "任务帖子",
            "taskStatus": "待接单",
            "taskCategory": fields.get("category") or detail.get("category") or "校园问答",
            "taskLocation": fields.get("location") or detail.get("location") or "校内",
            "taskTimeText": fields.get("expected_time") or detail.get("expected_time") or "待协商",
            "taskRewardType": fields.get("reward_type") or detail.get("reward_type") or "无偿",
            "taskRewardText": fields.get("reward_text") or detail.get("reward_text") or "互助优先",
            "taskMaxParticipants": fields.get("task_max_participants") or detail.get("task_max_participants") or 1,
            "tags": fields.get("tags") or detail.get("tags") or ["校园生活"],
            "isAiAssisted": True,
            "sourceAgent": "assistant_graph",
            "status": detail.get("status") or "draft",
            "draftId": detail.get("draft_id"),
            "confirmationAction": detail.get("action"),
        },
    }


def _reminder_draft_from_detail(detail: dict[str, Any] | None = None) -> dict[str, Any]:
    detail = detail or {}
    message = str(detail.get("message") or "校园事项提醒")
    title = str(detail.get("title") or message.replace("提醒我", "").strip("：:，, ") or "校园事项提醒")[:40]
    return {
        "type": "CREATE_REMINDER_DRAFT",
        "payload": {
            "title": title,
            "description": message,
            "remindAt": detail.get("remind_at") or detail.get("remindAt"),
            "repeatType": detail.get("repeat_rule") or detail.get("repeatType") or "none",
            "sourceAgent": "assistant_graph",
            "status": detail.get("status") or "draft",
            "draftId": detail.get("draft_id"),
            "confirmationAction": detail.get("action"),
        },
    }


def _confirmation_action(summary: str, detail: dict[str, Any], action: str | None = None) -> dict[str, Any]:
    return {
        "type": "AGENT_CONFIRMATION_REQUIRED",
        "payload": {
            "summary": summary,
            "detail": detail,
            "action": action,
            "status": "pending",
        },
    }


def _map_backend_action(action: dict[str, Any], user_message: str = "") -> dict[str, Any] | None:
    action_type = action.get("type")
    if action_type == "handoff":
        target = BACKEND_TO_FRONTEND_AGENT.get(action.get("target_agent", ""))
        if not target:
            return None
        confirmed = bool(action.get("confirmed"))
        needs_confirm = bool(action.get("needs_confirm")) and not confirmed
        return {
            "type": "RECOMMEND_AGENT",
            "payload": {
                "targetAgentId": target,
                "targetAgentName": AGENT_DISPLAY_NAMES.get(target, target),
                "reason": action.get("reason") or "私人助理建议转交专业 Agent 处理。",
                "confidence": action.get("confidence", 0.8),
                "suggestedActionText": f"去问{AGENT_DISPLAY_NAMES.get(target, target)}",
                "agentSessionId": action.get("agent_session_id"),
                "requiresConfirmation": needs_confirm,
                "status": "confirmed" if confirmed else ("pending" if needs_confirm else "ready"),
                "confirmationAction": "handoff_professional_agent" if needs_confirm else None,
            },
        }
    if action_type == "interrupt":
        interrupt_data = action.get("interrupt_data") or {}
        confirm_action = interrupt_data.get("action")
        detail = interrupt_data.get("detail") or {}
        if confirm_action == "create_reminder":
            return _reminder_draft_from_detail(detail)
        if confirm_action in {"confirm_publish_task", "community_create_help_task"} or (
            isinstance(confirm_action, str) and confirm_action.startswith("community_create_help_task")
        ):
            draft_detail = dict(detail)
            draft_detail["action"] = confirm_action
            draft_detail["status"] = "pending_confirmation"
            return _task_draft_from_message(user_message, draft_detail)
        if confirm_action == "handoff_professional_agent":
            target = BACKEND_TO_FRONTEND_AGENT.get(detail.get("target_agent", ""))
            if target:
                return {
                    "type": "RECOMMEND_AGENT",
                    "payload": {
                        "targetAgentId": target,
                        "targetAgentName": detail.get("display_name") or AGENT_DISPLAY_NAMES.get(target, target),
                        "reason": interrupt_data.get("summary") or "私人助理建议转交专业 Agent 处理。",
                        "confidence": 0.8,
                        "suggestedActionText": f"去问{detail.get('display_name') or AGENT_DISPLAY_NAMES.get(target, target)}",
                        "requiresConfirmation": True,
                        "status": "pending",
                        "confirmationAction": confirm_action,
                    },
                }
        return _confirmation_action(
            summary=interrupt_data.get("summary", "需要确认"),
            detail=detail,
            action=confirm_action,
        )
    if action_type == "community_agent":
        intent = action.get("intent")
        if intent == "search_help_task":
            return {"type": "SEARCH_POSTS", "payload": {"keywords": user_message, "scope": "all", "postType": "任务帖子"}}
        return {
            "type": "START_COMMUNITY_WORKFLOW",
            "payload": {
                "intent": intent,
                "status": "running",
                "requiresConfirmation": False,
            },
        }
    if action_type == "reminder_create":
        return _reminder_draft_from_detail({"message": user_message})
    if action_type == "confirm_create_task":
        fields = action.get("task_fields") or {}
        return _task_draft_from_message(user_message, fields)
    if action_type == "confirm_create_reminder":
        return _reminder_draft_from_detail(action.get("fields") or {})
    if action_type == "search_results":
        return {"type": "SEARCH_POSTS", "payload": {"keywords": user_message, "scope": "all"}}
    if action_type == "ask_clarification":
        return {"type": "AGENT_CLARIFICATION_REQUIRED", "payload": {"missingFields": action.get("missing_fields", [])}}
    if action_type in {"task_cancelled", "task_delete_cancelled", "cancelled"}:
        return {"type": "AGENT_CANCELLED", "payload": action}
    if action_type in {"task_published", "task_deleted"}:
        return {"type": "COMMUNITY_TASK_UPDATED", "payload": action}
    if action_type == "confirmation_required":
        return _confirmation_action("操作需要确认", action, action.get("action"))
    if action_type == "error":
        return {"type": "AGENT_ERROR", "payload": action}
    return None


def _map_backend_actions(actions: list[dict[str, Any]], user_message: str = "") -> list[dict[str, Any]]:
    mapped = []
    for action in actions:
        item = _map_backend_action(action, user_message=user_message)
        if item:
            mapped.append(item)
    return mapped

async def chat_with_frontend_agent(
    request: Request,
    db: AsyncSession,
    agent_id: str,
    message: str,
    user_id: str | None = None,
    conversation_id: str | None = None,
    image_urls: list[str] | None = None,
    context: dict | None = None,
) -> dict[str, Any]:
    external_user_id = user_id or "demo_user"
    _append_message(agent_id, "user", message, image_urls)

    if not check_llm_configured():
        if get_settings().demo_mode:
            result = await build_demo_fixture_response(
                db=db,
                agent_id=agent_id,
                message=message,
                external_user_id=external_user_id,
                conversation_id=conversation_id,
            )
            _append_message(agent_id, "assistant", result["reply"])
            return result
        result = {
            "agentId": agent_id,
            "reply": LLM_NOT_CONFIGURED_MSG,
            "actions": [{"type": "AGENT_ERROR", "payload": {"code": "LLM_CONFIG_MISSING"}}],
            "metadata": {"source": "agent_unavailable", "is_agent_reasoning": False},
        }
        _append_message(agent_id, "assistant", result["reply"])
        return result

    if agent_id == "personal-assistant":
        response = await assistant_chat(
            ChatRequest(
                message=message,
                conversation_id=conversation_id,
                external_user_id=external_user_id,
            ),
            request=request,
            db=db,
        )
        result = {
            "agentId": agent_id,
            "reply": response.content,
            "actions": _map_backend_actions(response.actions, user_message=message),
            "metadata": {
                "source": "assistant_graph",
                "conversation_id": response.conversation_id,
                "message_id": response.message_id,
                "run_id": getattr(response, "run_id", None) or response.message_id,
                "suggested_agent": response.agent_name,
                "is_agent_reasoning": True,
            },
        }
        _append_message(agent_id, "assistant", response.content)
        return result

    backend_agent_name = FRONTEND_TO_BACKEND_AGENT.get(agent_id)
    if not backend_agent_name:
        result = {
            "agentId": agent_id,
            "reply": f"未知 Agent: {agent_id}",
            "actions": [],
            "metadata": {"source": "agent_adapter", "is_agent_reasoning": False},
        }
        _append_message(agent_id, "assistant", result["reply"])
        return result

    response = await agent_chat(
        AgentChatRequest(
            agent_name=backend_agent_name,
            message=message,
            conversation_id=conversation_id,
            external_user_id=external_user_id,
        ),
        db=db,
    )
    result = {
        "agentId": agent_id,
        "reply": response.content,
        "actions": [],
        "metadata": {
            "source": "professional_agent_graph",
            "backend_agent_name": response.agent_name,
            "conversation_id": response.conversation_id,
            "message_id": response.message_id,
            "run_id": getattr(response, "run_id", None) or response.message_id,
            "boundary_reminder": response.boundary_reminder,
            "is_agent_reasoning": True,
        },
    }
    _append_message(agent_id, "assistant", response.content)
    return result




