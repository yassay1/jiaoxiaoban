"""Shared constants and helpers used across service modules."""

from datetime import datetime, timezone


def now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


AGENT_DISPLAY_NAMES: dict[str, str] = {
    "personal-assistant": "私人助理",
    "academic-teacher": "教学科石老师",
    "postgraduate-agent": "保研学长阿泽",
    "science-tutor": "理科学霸小林",
    "life-teacher": "生活辅导员友老师",
}

FRONTEND_TO_BACKEND_AGENT: dict[str, str] = {
    "academic-teacher": "teaching_agent",
    "postgraduate-agent": "postgraduate_agent",
    "science-tutor": "science_agent",
    "life-teacher": "life_agent",
}

BACKEND_TO_FRONTEND_AGENT: dict[str, str] = {
    "teaching_agent": "academic-teacher",
    "postgraduate_agent": "postgraduate-agent",
    "science_agent": "science-tutor",
    "life_agent": "life-teacher",
}
PUBLIC_ERROR_MESSAGE = "当前操作没有完成，请稍后重试；如果连续失败，可以换一种说法或刷新页面后再试。"
PUBLIC_RESUME_ERROR_MESSAGE = "确认操作没有完成，请稍后重试；如果任务已经创建，请到任务大厅或我的任务中查看。"


def public_error_message(resume: bool = False) -> str:
    """Return a stable user-facing error without leaking internal exception details."""
    return PUBLIC_RESUME_ERROR_MESSAGE if resume else PUBLIC_ERROR_MESSAGE


def public_error_action(code: str = "INTERNAL_ERROR") -> dict[str, str]:
    return {"type": "error", "code": code}
