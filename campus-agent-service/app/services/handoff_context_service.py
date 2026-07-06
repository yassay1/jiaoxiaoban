"""Helpers for professional-agent handoff context."""

from __future__ import annotations

import json
from typing import Any


def build_handoff_context(
    *,
    source: str,
    target_agent: str,
    user_message: str,
    conversation_id: str | None,
    external_user_id: str,
    reason: str | None = None,
    summary: str | None = None,
) -> str:
    """Serialize minimal handoff context without changing DB schema."""
    payload = {
        "source": source,
        "target_agent": target_agent,
        "reason": reason or "私人助理建议进入专业 Agent 咨询。",
        "summary": summary or user_message,
        "user_message": user_message,
        "conversation_id": conversation_id,
        "external_user_id": external_user_id,
    }
    return json.dumps(payload, ensure_ascii=False)


def parse_handoff_context(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"summary": raw}
    return data if isinstance(data, dict) else {"summary": str(data)}


def format_handoff_context_for_prompt(raw: str | None) -> str | None:
    data = parse_handoff_context(raw)
    if not data:
        return None
    parts = []
    if data.get("source"):
        parts.append(f"来源：{data['source']}")
    if data.get("reason"):
        parts.append(f"转接原因：{data['reason']}")
    if data.get("summary"):
        parts.append(f"上下文摘要：{data['summary']}")
    if data.get("user_message") and data.get("user_message") != data.get("summary"):
        parts.append(f"用户原问题：{data['user_message']}")
    return "\n".join(parts) if parts else None
