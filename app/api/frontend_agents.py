from fastapi import APIRouter, Depends, Request

from app.db.session import get_db, AsyncSession
from app.schemas.frontend_agent import FrontendAgentChatRequest, FrontendAgentChatResponse, FrontendMessageListResponse
from app.services.frontend_agent_adapter_service import (
    chat_with_frontend_agent,
    clear_frontend_agent_messages,
    get_frontend_agent_messages,
)

router = APIRouter(prefix="/api/agents", tags=["frontend-agents"])


@router.post("/{agent_id}/chat", response_model=FrontendAgentChatResponse)
async def frontend_agent_chat(
    agent_id: str,
    req: FrontendAgentChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await chat_with_frontend_agent(
        request=request,
        db=db,
        agent_id=agent_id,
        message=req.message,
        user_id=req.userId,
        conversation_id=req.conversationId,
        image_urls=req.imageUrls,
        context=req.context,
    )


@router.get("/{agent_id}/messages", response_model=FrontendMessageListResponse)
async def frontend_agent_messages(agent_id: str):
    messages = get_frontend_agent_messages(agent_id)
    return FrontendMessageListResponse(messages=messages, total=len(messages))


@router.delete("/{agent_id}/messages")
async def frontend_agent_clear_messages(agent_id: str):
    deleted = clear_frontend_agent_messages(agent_id)
    return {"detail": "cleared", "deleted": deleted}
