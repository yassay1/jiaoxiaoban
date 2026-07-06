from datetime import datetime, timezone
import inspect
import logging
import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.session import get_db, AsyncSession
from app.db.models import ProfessionalAgentSession, HandoffRecord
from app.schemas.chat import ChatRequest, ChatResponse
from app.graphs.assistant_graph import build_assistant_graph
from app.services.agent_run_service import create_run, update_run
from app.services.conversation_service import get_or_create_conversation
from app.services.message_service import save_message, get_recent_messages
from app.services.handoff_context_service import build_handoff_context
from app.services.llm_service import check_llm_configured, LLM_NOT_CONFIGURED_MSG
from app.utils.shared import public_error_action, public_error_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


async def _db_add(db: AsyncSession, instance) -> None:
    """Support SQLAlchemy's sync add() and AsyncMock-based tests."""
    result = db.add(instance)
    if inspect.isawaitable(result):
        await result


class ResumeRequest(BaseModel):
    conversation_id: str = Field(..., description="会话 ID")
    decision: str = Field(..., description="approve | reject | revise")
    payload: dict = Field(default_factory=dict, description="附加数据")


class ResumeResponse(BaseModel):
    conversation_id: str
    message_id: str
    run_id: str | None = None
    role: str = "assistant"
    content: str
    agent_name: str | None = None
    actions: list[dict] = []
    status: str = "completed"
    created_at: datetime


@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(req: ChatRequest, request: Request, db: AsyncSession = Depends(get_db)):
    if not check_llm_configured():
        return ChatResponse(
            conversation_id=req.conversation_id or "new",
            message_id="error",
            role="assistant",
            content=LLM_NOT_CONFIGURED_MSG,
            agent_name=None,
            actions=[{"type": "error", "code": "LLM_CONFIG_MISSING"}],
            created_at=datetime.now(timezone.utc),
        )

    conv = await get_or_create_conversation(db, req.external_user_id, req.conversation_id)
    conversation_id = conv.id

    await save_message(db, conversation_id, "user", req.message)

    recent_msgs = await get_recent_messages(db, conversation_id, limit=10)
    recent_dicts = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent_msgs)
    ]

    # 长期用户记忆（加载失败降级为空，不影响主流程）
    try:
        from app.services.long_term_memory_service import get_user_memories
        memories = await get_user_memories(db, req.external_user_id, limit=20)
        memory_context = {m.memory_type: m.content for m in memories}
    except Exception:
        logger.warning("Failed to load long-term memory for user %s", req.external_user_id)
        memory_context = {}

    # 产品知识 RAG 上下文（加载失败降级为空，不影响主流程）
    try:
        from app.services.rag_service import search_knowledge
        product_rag_context = await search_knowledge(
            db, req.message, agent_name="", top_k=5
        )
    except Exception:
        logger.warning("Failed to load RAG context for message: %s", req.message[:50])
        product_rag_context = []

    run_id = await create_run(
        db=db,
        graph_name="assistant_graph",
        input_data={"message": req.message, "external_user_id": req.external_user_id},
        conversation_id=conversation_id,
    )

    initial_state = {
        "user_message": req.message,
        "external_user_id": req.external_user_id,
        "conversation_id": conversation_id,
        "messages": [],
        "recent_messages": recent_dicts,
        "memory_context": memory_context,
        "product_rag_context": product_rag_context,
    }

    try:
        graph = build_assistant_graph(checkpointer=request.app.state.checkpointer)
        config = {"configurable": {"thread_id": conversation_id}}
        result = await graph.ainvoke(initial_state, config)

        # 检查是否被 interrupt 暂停
        if result and result.get("__interrupt__"):
            interrupt_tuple = result["__interrupt__"]
            last_interrupt = interrupt_tuple[-1]
            interrupt_value = last_interrupt.value if hasattr(last_interrupt, "value") else last_interrupt
            if isinstance(interrupt_value, dict):
                msg = interrupt_value.get("message", "请确认此操作。")
            else:
                msg = str(interrupt_value)
            await update_run(
                run_id,
                db=db,
                output_data={"interrupt": interrupt_value, "suggested_agent": result.get("suggested_agent")},
                status="interrupted",
            )
            return ChatResponse(
                conversation_id=conversation_id,
                message_id=run_id,
                run_id=run_id,
                role="assistant",
                content=msg,
                agent_name=result.get("suggested_agent"),
                actions=[{
                    "type": "interrupt",
                    "needs_confirm": True,
                    "interrupt_data": interrupt_value,
                }],
                created_at=datetime.now(timezone.utc),
            )

        await update_run(run_id, db=db, output_data=result, status="completed")

        final_response = result.get("final_response") or result.get("response", "")
        saved_msg = await save_message(db, conversation_id, "assistant", final_response)

        # Phase 4 R5: auto-extract long-term memories from this turn
        try:
            from app.services.long_term_memory_service import auto_save_memories_from_turn
            await auto_save_memories_from_turn(
                db=db,
                external_user_id=req.external_user_id,
                user_message=req.message,
                assistant_response=final_response,
            )
        except Exception:
            logger.debug("Auto memory extraction skipped (non-critical)")

        actions = result.get("actions", [])

        # 处理 handoff：创建真实 session
        nav_action = result.get("navigation_action")
        if nav_action and nav_action.get("action_type") == "navigate":
            target_agent = nav_action.get("target_agent", "")
            handoff_context = build_handoff_context(
                source="assistant",
                target_agent=target_agent,
                user_message=req.message,
                conversation_id=conversation_id,
                external_user_id=req.external_user_id,
                reason="私人助理判断该问题更适合专业 Agent。",
                summary=req.message,
            )
            agent_session = ProfessionalAgentSession(
                id=str(uuid.uuid4()),
                external_user_id=req.external_user_id,
                agent_name=target_agent,
                conversation_id=conversation_id,
                handoff_context=handoff_context,
                status="active",
            )
            await _db_add(db, agent_session)
            await db.flush()

            handoff = HandoffRecord(
                id=str(uuid.uuid4()),
                external_user_id=req.external_user_id,
                agent_run_id=run_id,
                from_agent="assistant",
                to_agent=target_agent,
                agent_session_id=agent_session.id,
                handoff_context=handoff_context,
                status="completed",
            )
            await _db_add(db, handoff)
            await db.flush()

            nav_action["agent_session_id"] = agent_session.id
            nav_action["handoff_context"] = handoff_context
            for action in actions:
                if action.get("type") == "handoff":
                    action["agent_session_id"] = agent_session.id

        return ChatResponse(
            conversation_id=conversation_id,
            message_id=saved_msg.id,
            run_id=run_id,
            role="assistant",
            content=final_response,
            agent_name=result.get("suggested_agent"),
            actions=actions,
            created_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error("assistant_chat 处理失败：%s\n%s", e, traceback.format_exc())
        await db.rollback()
        await update_run(run_id, db=db, error=str(e), status="failed")
        return ChatResponse(
            conversation_id=conversation_id,
            message_id=run_id,
            run_id=run_id,
            role="assistant",
            content=public_error_message(),
            agent_name=None,
            actions=[public_error_action()],
            created_at=datetime.now(timezone.utc),
        )


@router.post("/resume", response_model=ResumeResponse)
async def assistant_resume(req: ResumeRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """恢复被 interrupt 暂停的会话。"""
    from langgraph.types import Command

    conversation_id = req.conversation_id
    if not conversation_id or conversation_id == "new":
        raise HTTPException(status_code=400, detail="需要有效的 conversation_id")

    run_id = await create_run(
        db=db,
        graph_name="assistant_graph_resume",
        input_data={
            "conversation_id": conversation_id,
            "decision": req.decision,
            "payload": req.payload,
        },
        conversation_id=conversation_id,
    )

    resume_value = {
        "decision": req.decision,
        "payload": req.payload,
    }

    try:
        graph = build_assistant_graph(checkpointer=request.app.state.checkpointer)
        config = {"configurable": {"thread_id": conversation_id}}
        result = await graph.ainvoke(
            Command(resume=resume_value),
            config,
        )

        await update_run(run_id, db=db, output_data=result, status="completed")

        final_response = result.get("final_response") or result.get("response", "")
        saved_msg = await save_message(db, conversation_id, "assistant", final_response)

        # Phase 4 R5: auto-extract long-term memories from resumed turn
        try:
            from app.services.long_term_memory_service import auto_save_memories_from_turn
            external_uid = result.get("external_user_id", "resume_user")
            await auto_save_memories_from_turn(
                db=db,
                external_user_id=external_uid,
                user_message=req.payload.get("message", ""),
                assistant_response=final_response,
            )
        except Exception:
            logger.debug("Auto memory extraction skipped in resume (non-critical)")

        actions = result.get("actions", [])

        # 处理 resumed handoff
        nav_action = result.get("navigation_action")
        if nav_action and nav_action.get("action_type") == "navigate":
            target_agent = nav_action.get("target_agent", "")
            external_user_id = result.get("external_user_id", "resume")
            handoff_context = build_handoff_context(
                source="assistant",
                target_agent=target_agent,
                user_message=final_response,
                conversation_id=conversation_id,
                external_user_id=external_user_id,
                reason="用户确认私人助理的专业 Agent 转接。",
                summary=final_response,
            )
            agent_session = ProfessionalAgentSession(
                id=str(uuid.uuid4()),
                external_user_id=external_user_id,
                agent_name=target_agent,
                conversation_id=conversation_id,
                handoff_context=handoff_context,
                status="active",
            )
            await _db_add(db, agent_session)
            await db.flush()
            handoff = HandoffRecord(
                id=str(uuid.uuid4()),
                external_user_id=external_user_id,
                agent_run_id=run_id,
                from_agent="assistant",
                to_agent=target_agent,
                agent_session_id=agent_session.id,
                handoff_context=handoff_context,
                status="completed",
            )
            await _db_add(db, handoff)
            await db.flush()
            nav_action["agent_session_id"] = agent_session.id
            nav_action["handoff_context"] = handoff_context
            for action in actions:
                if action.get("type") == "handoff":
                    action["agent_session_id"] = agent_session.id

        status = "rejected" if req.decision == "reject" else "completed"

        return ResumeResponse(
            conversation_id=conversation_id,
            message_id=saved_msg.id,
            run_id=run_id,
            role="assistant",
            content=final_response,
            agent_name=result.get("suggested_agent"),
            actions=actions,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error("assistant_resume 处理失败：%s\n%s", e, traceback.format_exc())
        await db.rollback()
        await update_run(run_id, db=db, error=str(e), status="failed")
        return ResumeResponse(
            conversation_id=conversation_id,
            message_id=run_id,
            run_id=run_id,
            role="assistant",
            content=public_error_message(resume=True),
            agent_name=None,
            actions=[public_error_action()],
            status="failed",
            created_at=datetime.now(timezone.utc),
        )
