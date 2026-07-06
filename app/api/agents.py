from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.db.session import get_db, AsyncSession
from app.schemas.agent import (
    AgentRecommendRequest,
    AgentRecommendResponse,
    AgentChatRequest,
    AgentChatResponse,
    AgentInfo,
)
from pydantic import BaseModel, Field

from app.chains.agent_recommend_chain import recommend_agent
from app.agents.professional_agent_runner import run_professional_agent
from app.services.handoff_context_service import build_handoff_context
from app.services.rag_service import search_knowledge
from app.services.llm_service import check_llm_configured
from app.services.conversation_service import get_or_create_conversation
from app.services.message_service import save_message, get_recent_messages
from app.db.models import ProfessionalAgentSession

router = APIRouter(prefix="/api/agents", tags=["agents"])


class CreateSessionRequest(BaseModel):
    agent_name: str = Field(..., description="目标 Agent 名称")
    external_user_id: str = Field(..., min_length=1, max_length=128)
    handoff_context: str | None = Field(None, description="交接上下文")


class CreateSessionResponse(BaseModel):
    session_id: str
    agent_name: str
    external_user_id: str
    handoff_context: str | None = None
    status: str = "active"
    created_at: datetime


_VALID_AGENTS = frozenset({
    "teaching_agent",
    "postgraduate_agent",
    "science_agent",
    "life_agent",
})


@router.post("/recommend", response_model=AgentRecommendResponse)
async def agent_recommend(req: AgentRecommendRequest):
    result = await recommend_agent(req.message)
    agents = []
    for a in result.get("recommended_agents", []):
        agents.append(AgentInfo(
            agent_name=a["agent_name"],
            display_name=a.get("display_name", a["agent_name"]),
            description=a.get("reason", ""),
            capabilities=[],
        ))
    return AgentRecommendResponse(
        recommended_agents=agents,
        reason=result.get("overall_reason", ""),
    )


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest, db: AsyncSession = Depends(get_db)):
    if req.agent_name not in _VALID_AGENTS:
        valid = ", ".join(sorted(_VALID_AGENTS))
        return AgentChatResponse(
            conversation_id=req.conversation_id or "new",
            message_id="error",
            agent_name=req.agent_name,
            role="assistant",
            content=f"未找到 Agent: {req.agent_name}。可用的 Agent: {valid}",
            boundary_reminder=None,
            created_at=datetime.now(timezone.utc),
        )

    # 如果提供了 session_id，验证并加载会话上下文
    handoff_context = None
    if req.session_id:
        from sqlalchemy import select
        result = await db.execute(
            select(ProfessionalAgentSession).where(
                ProfessionalAgentSession.id == req.session_id
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            return AgentChatResponse(
                conversation_id=req.conversation_id or "new",
                message_id="error",
                agent_name=req.agent_name,
                role="assistant",
                content=f"未找到会话: {req.session_id}",
                boundary_reminder=None,
                created_at=datetime.now(timezone.utc),
            )
        if session.external_user_id != req.external_user_id:
            return AgentChatResponse(
                conversation_id=req.conversation_id or "new",
                message_id="error",
                agent_name=req.agent_name,
                role="assistant",
                content="无权访问此会话。",
                boundary_reminder=None,
                created_at=datetime.now(timezone.utc),
            )
        if session.agent_name != req.agent_name:
            return AgentChatResponse(
                conversation_id=req.conversation_id or "new",
                message_id="error",
                agent_name=req.agent_name,
                role="assistant",
                content=f"会话 {req.session_id} 属于 {session.agent_name}，不能用于 {req.agent_name}。",
                boundary_reminder=None,
                created_at=datetime.now(timezone.utc),
            )
        handoff_context = session.handoff_context
        if session.conversation_id:
            req.conversation_id = session.conversation_id

    # 获取或创建专业 Agent 专用的 conversation
    conv = await get_or_create_conversation(db, req.external_user_id, req.conversation_id)
    conversation_id = conv.id

    # 加载对话历史（在保存当前消息之前，避免当前消息重复出现）
    recent_msgs = await get_recent_messages(db, conversation_id, limit=10)
    recent_dicts = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent_msgs)
    ]

    await save_message(db, conversation_id, "user", req.message)

    rag_context = []
    if check_llm_configured():
        rag_context = await search_knowledge(
            db=db,
            query=req.message,
            agent_name=req.agent_name,
            top_k=5,
        )

    result = await run_professional_agent(
        agent_name=req.agent_name,
        user_message=req.message,
        external_user_id=req.external_user_id,
        conversation_id=conversation_id,
        rag_context=rag_context,
        recent_messages=recent_dicts,
        handoff_context=handoff_context,
    )

    await save_message(db, conversation_id, "assistant", result.get("content", ""))

    return AgentChatResponse(
        conversation_id=conversation_id,
        message_id=result["message_id"],
        run_id=result.get("run_id", result["message_id"]),
        agent_name=result["agent_name"],
        role=result["role"],
        content=result["content"],
        boundary_reminder=result.get("boundary_reminder"),
        created_at=datetime.now(timezone.utc),
    )


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_agent_session(req: CreateSessionRequest, db: AsyncSession = Depends(get_db)):
    import uuid
    from app.db.models import ProfessionalAgentSession

    if req.agent_name not in _VALID_AGENTS:
        valid = ", ".join(sorted(_VALID_AGENTS))
        return CreateSessionResponse(
            session_id="error",
            agent_name=req.agent_name,
            external_user_id=req.external_user_id,
            handoff_context=f"未找到 Agent: {req.agent_name}。可用的 Agent: {valid}",
            status="error",
            created_at=datetime.now(timezone.utc),
        )

    handoff_context = None
    if req.handoff_context:
        handoff_context = build_handoff_context(
            source="assistant",
            target_agent=req.agent_name,
            user_message=req.handoff_context,
            conversation_id=None,
            external_user_id=req.external_user_id,
            reason="通过会话创建接口进入专业 Agent。",
            summary=req.handoff_context,
        )

    session = ProfessionalAgentSession(
        id=str(uuid.uuid4()),
        external_user_id=req.external_user_id,
        agent_name=req.agent_name,
        handoff_context=handoff_context,
        status="active",
    )
    db.add(session)
    await db.flush()

    return CreateSessionResponse(
        session_id=session.id,
        agent_name=req.agent_name,
        external_user_id=req.external_user_id,
        handoff_context=handoff_context,
        status="active",
        created_at=session.created_at,
    )
