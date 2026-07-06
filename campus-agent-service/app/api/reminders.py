from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db.session import get_db, AsyncSession
from app.db.models import Reminder, utc_now
from app.graphs.reminder_graph import build_reminder_graph
from app.services.agent_run_service import create_run, update_run
from app.services.llm_service import check_llm_configured, LLM_NOT_CONFIGURED_MSG
from app.config.settings import get_settings
from app.utils.shared import public_error_action, public_error_message
from langgraph.types import Command

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


class ReminderCreateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2048, description="提醒描述")
    external_user_id: str = Field(..., min_length=1, max_length=128)
    conversation_id: str | None = None


class ReminderCreateResponse(BaseModel):
    conversation_id: str
    message_id: str
    response: str
    actions: list[dict]
    draft_id: str | None = None
    reminder_id: str | None = None
    status: str | None = None
    created_at: datetime


class ReminderResumeRequest(BaseModel):
    conversation_id: str = Field(..., description="会话 ID")
    decision: str = Field(..., description="approve | reject")
    payload: dict = Field(default_factory=dict)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return utc_now()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return utc_now()


def _reminder_to_frontend(reminder: Reminder) -> dict:
    return {
        "id": reminder.id,
        "title": reminder.title,
        "description": reminder.description,
        "channel": "app",
        "createdAt": reminder.created_at.isoformat() if reminder.created_at else None,
        "remindAt": reminder.remind_at.isoformat() if reminder.remind_at else None,
        "repeatType": reminder.repeat_rule,
        "sourceAgent": "私人助理",
        "status": reminder.status,
    }


@router.get("")
async def list_reminders(
    db: AsyncSession = Depends(get_db),
    externalUserId: str = "demo_user",
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=100),
):
    result = await db.execute(
        select(Reminder)
        .where(Reminder.external_user_id == externalUserId)
        .order_by(Reminder.created_at.desc())
        .offset(max(page - 1, 0) * pageSize)
        .limit(pageSize)
    )
    return [_reminder_to_frontend(r) for r in result.scalars().all()]


@router.post("")
async def create_reminder(req: Request, db: AsyncSession = Depends(get_db)):
    body = await req.json()

    # Frontend business API: create a confirmed reminder.
    if "title" in body and "message" not in body:
        reminder = Reminder(
            id=str(uuid.uuid4()),
            external_user_id=body.get("externalUserId") or body.get("external_user_id") or "demo_user",
            title=body.get("title") or "提醒",
            remind_at=_parse_dt(body.get("remindAt") or body.get("remind_at")),
            repeat_rule=body.get("repeatType") or body.get("repeat_rule"),
            description=body.get("description"),
            status=body.get("status") or "active",
        )
        db.add(reminder)
        await db.flush()
        return _reminder_to_frontend(reminder)

    # Existing Agent graph API, kept for backward compatibility.
    req_model = ReminderCreateRequest(**body)
    if not check_llm_configured() and not get_settings().demo_mode:
        return ReminderCreateResponse(
            conversation_id=req_model.conversation_id or "new",
            message_id="error",
            response=LLM_NOT_CONFIGURED_MSG,
            actions=[{"type": "error", "code": "LLM_CONFIG_MISSING"}],
            created_at=datetime.now(timezone.utc),
        )

    if get_settings().demo_mode and not check_llm_configured():
        title = req_model.message.replace("提醒我", "").strip("：:，, ") or "校园事项提醒"
        return ReminderCreateResponse(
            conversation_id=req_model.conversation_id or "demo_reminder",
            message_id=f"demo_{uuid.uuid4().hex[:12]}",
            response=f"提醒草稿：{title}。请确认后创建。",
            actions=[{"type": "confirm_create_reminder", "fields": {"title": title}}],
            draft_id=f"rdraft_{uuid.uuid4().hex[:12]}",
            created_at=datetime.now(timezone.utc),
        )

    run_id = await create_run(
        db=db,
        graph_name="reminder_graph",
        input_data={"message": req_model.message, "external_user_id": req_model.external_user_id},
        conversation_id=req_model.conversation_id,
    )

    conversation_id = req_model.conversation_id or f"rem_{run_id[:12]}"

    initial_state = {
        "user_message": req_model.message,
        "external_user_id": req_model.external_user_id,
        "conversation_id": conversation_id,
        "messages": [],
    }

    try:
        graph = build_reminder_graph(checkpointer=req.app.state.checkpointer)
        config = {"configurable": {"thread_id": conversation_id}}
        result = await graph.ainvoke(initial_state, config)

        if result and result.get("__interrupt__"):
            interrupt_tuple = result["__interrupt__"]
            last_interrupt = interrupt_tuple[-1]
            interrupt_value = last_interrupt.value if hasattr(last_interrupt, "value") else last_interrupt
            msg = interrupt_value.get("message", "请确认") if isinstance(interrupt_value, dict) else str(interrupt_value)
            return ReminderCreateResponse(
                conversation_id=conversation_id,
                message_id=run_id,
                response=msg,
                actions=[{"type": "interrupt", "needs_confirm": True, "interrupt_data": interrupt_value}],
                draft_id=result.get("draft_id"),
                created_at=datetime.now(timezone.utc),
            )

        await update_run(run_id, db=db, output_data=result, status="completed")
        return ReminderCreateResponse(
            conversation_id=conversation_id,
            message_id=run_id,
            response=result.get("response", ""),
            actions=result.get("actions", []),
            draft_id=result.get("draft_id"),
            reminder_id=result.get("reminder_id"),
            created_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        await update_run(run_id, db=db, error=str(e), status="failed")
        return ReminderCreateResponse(
            conversation_id=conversation_id,
            message_id=run_id,
            response=public_error_message(),
            actions=[public_error_action()],
            created_at=datetime.now(timezone.utc),
        )


@router.patch("/{reminder_id}")
async def update_reminder(reminder_id: str, req: Request, db: AsyncSession = Depends(get_db)):
    body = await req.json()
    result = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")
    if "title" in body:
        reminder.title = body["title"]
    if "description" in body:
        reminder.description = body["description"]
    if "remindAt" in body:
        reminder.remind_at = _parse_dt(body.get("remindAt"))
    if "repeatType" in body:
        reminder.repeat_rule = body.get("repeatType")
    if "status" in body:
        reminder.status = body["status"]
    reminder.updated_at = utc_now()
    await db.flush()
    return _reminder_to_frontend(reminder)


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")
    await db.delete(reminder)
    await db.flush()
    return {"detail": "deleted"}


@router.post("/resume", response_model=ReminderCreateResponse)
async def resume_reminder(req: ReminderResumeRequest, request: Request):
    """恢复被 interrupt 暂停的提醒创建。"""

    if not req.conversation_id:
        raise HTTPException(status_code=400, detail="需要有效的 conversation_id")

    run_id = await create_run(
        db=None,
        graph_name="reminder_graph:resume",
        input_data={"decision": req.decision, "payload": req.payload},
        conversation_id=req.conversation_id,
    )
    resume_value = {"decision": req.decision, "payload": req.payload}

    try:
        graph = build_reminder_graph(checkpointer=request.app.state.checkpointer)
        config = {"configurable": {"thread_id": req.conversation_id}}
        result = await graph.ainvoke(Command(resume=resume_value), config)

        await update_run(run_id, output_data=result, status="completed")
        return ReminderCreateResponse(
            conversation_id=req.conversation_id,
            message_id=run_id,
            response=result.get("response", ""),
            actions=result.get("actions", []),
            draft_id=result.get("draft_id"),
            reminder_id=result.get("reminder_id"),
            created_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        await update_run(run_id, error=str(e), status="failed")
        return ReminderCreateResponse(
            conversation_id=req.conversation_id,
            message_id=run_id,
            response=public_error_message(resume=True),
            actions=[public_error_action()],
            status="failed",
            created_at=datetime.now(timezone.utc),
        )
