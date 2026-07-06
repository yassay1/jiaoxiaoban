from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graphs.community_agent_subgraph import community_agent_subgraph
from app.services.agent_run_service import create_run, update_run
from app.services.llm_service import check_llm_configured, LLM_NOT_CONFIGURED_MSG
from app.utils.shared import public_error_action, public_error_message

router = APIRouter(prefix="/api/community-agent", tags=["community-agent"])

# 保留旧 schema 导入以兼容
from app.schemas.post import (
    PostAnalyzeRequest,
    PostAnalyzeResponse,
    ConvertPostToTaskRequest,
    ConvertPostToTaskResponse,
)
from app.agents.community_admin_agent import run_community_admin_analyze
from app.graphs.community_task_graph import community_task_graph


class CommunityChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    external_user_id: str = Field(..., min_length=1, max_length=128)
    conversation_id: str | None = None
    intent: str = Field(default="search_help_task", description="create_help_task / delete_own_help_task / search_help_task")


class CommunityChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    response: str
    actions: list[dict]
    created_at: datetime


@router.post("/analyze-post", response_model=PostAnalyzeResponse)
async def analyze_post(req: PostAnalyzeRequest):
    result = await run_community_admin_analyze(
        post_id=req.post_id,
        title=req.title,
        content=req.content,
        author_external_user_id=req.author_external_user_id,
        tags=req.tags,
    )
    if "error" in result:
        return PostAnalyzeResponse(
            post_id=req.post_id,
            post_type="other",
            summary="分析失败",
            extracted_tags=[],
            has_help_intent=False,
            suggested_action="none",
            safety_notes=[result["error"]],
        )
    return PostAnalyzeResponse(
        post_id=result["post_id"],
        post_type=result["post_type"],
        summary=result["summary"],
        extracted_tags=result["extracted_tags"],
        has_help_intent=result["has_help_intent"],
        suggested_action=result["suggested_action"],
        safety_notes=result["safety_notes"],
    )


@router.post("/convert-post-to-task", response_model=ConvertPostToTaskResponse)
async def convert_post_to_task(req: ConvertPostToTaskRequest):
    initial_state = {
        "post_id": req.post_id,
        "title": req.title,
        "content": req.content,
        "external_user_id": req.external_user_id,
        "tags": req.tags or [],
        "messages": [],
    }
    result = await community_task_graph.ainvoke(initial_state)
    draft = result.get("task_draft", {})
    safety = result.get("safety_result", {})
    return ConvertPostToTaskResponse(
        post_id=req.post_id,
        task_draft_id="draft_" + result.get("post_id", ""),
        title=draft.get("title", req.title),
        description=draft.get("description", req.content),
        task_type=draft.get("task_type"),
        tags=draft.get("tags", req.tags or []),
        deadline_suggestion=None,
        safety_check_passed=not safety.get("is_blocked", False),
        safety_notes=safety.get("risk_reason", "").split("\n") if safety.get("risk_reason") else [],
        needs_confirmation=result.get("needs_confirmation", True),
        created_task_id=result.get("created_task_id"),
    )


@router.post("/search-help-tasks", response_model=CommunityChatResponse)
async def search_help_tasks(req: CommunityChatRequest):
    if not check_llm_configured():
        return CommunityChatResponse(
            conversation_id=req.conversation_id or "new",
            message_id="error",
            response=LLM_NOT_CONFIGURED_MSG,
            actions=[{"type": "error", "code": "LLM_CONFIG_MISSING"}],
            created_at=datetime.now(timezone.utc),
        )

    run_id = await create_run(
        db=None,
        graph_name="community_agent_subgraph",
        input_data={"message": req.message, "external_user_id": req.external_user_id},
        conversation_id=req.conversation_id,
    )

    initial_state = {
        "user_message": req.message,
        "external_user_id": req.external_user_id,
        "conversation_id": req.conversation_id,
        "community_intent": "search_help_task",
        "messages": [],
    }

    try:
        result = await community_agent_subgraph.ainvoke(initial_state)
        await update_run(run_id, output_data=result, status="completed")
        return CommunityChatResponse(
            conversation_id=req.conversation_id or "new",
            message_id=run_id,
            response=result.get("response", ""),
            actions=result.get("actions", []),
            created_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        await update_run(run_id, error=str(e), status="failed")
        return CommunityChatResponse(
            conversation_id=req.conversation_id or "new",
            message_id=run_id,
            response=public_error_message(),
            actions=[public_error_action()],
            created_at=datetime.now(timezone.utc),
        )


@router.post("/delete-my-help-task", response_model=CommunityChatResponse)
async def delete_my_help_task(req: CommunityChatRequest):
    if not check_llm_configured():
        return CommunityChatResponse(
            conversation_id=req.conversation_id or "new",
            message_id="error",
            response=LLM_NOT_CONFIGURED_MSG,
            actions=[{"type": "error", "code": "LLM_CONFIG_MISSING"}],
            created_at=datetime.now(timezone.utc),
        )

    run_id = await create_run(
        db=None,
        graph_name="community_agent_subgraph",
        input_data={"message": req.message, "external_user_id": req.external_user_id},
        conversation_id=req.conversation_id,
    )

    initial_state = {
        "user_message": req.message,
        "external_user_id": req.external_user_id,
        "conversation_id": req.conversation_id,
        "community_intent": "delete_own_help_task",
        "messages": [],
    }

    try:
        result = await community_agent_subgraph.ainvoke(initial_state)
        await update_run(run_id, output_data=result, status="completed")
        return CommunityChatResponse(
            conversation_id=req.conversation_id or "new",
            message_id=run_id,
            response=result.get("response", ""),
            actions=result.get("actions", []),
            created_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        await update_run(run_id, error=str(e), status="failed")
        return CommunityChatResponse(
            conversation_id=req.conversation_id or "new",
            message_id=run_id,
            response=public_error_message(),
            actions=[public_error_action()],
            created_at=datetime.now(timezone.utc),
        )
