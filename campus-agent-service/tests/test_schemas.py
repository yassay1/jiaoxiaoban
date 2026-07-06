import pytest
from pydantic import ValidationError

from app.chains.assistant_planner_chain import AssistantPlan
from app.schemas.agent import AgentChatRequest, AgentRecommendRequest
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.confirmation import ConfirmationRequest
from app.schemas.rag import RAGSearchRequest
from app.schemas.safety import SafetyCheckRequest


def test_chat_request_validation():
    req = ChatRequest(message="hello", external_user_id="u001")
    assert req.message == "hello"
    assert req.external_user_id == "u001"


def test_chat_request_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="", external_user_id="u001")


def test_agent_recommend_request():
    req = AgentRecommendRequest(message="need help", external_user_id="u001")
    assert req.message == "need help"


def test_agent_chat_request():
    req = AgentChatRequest(agent_name="teaching_agent", message="course selection", external_user_id="u001")
    assert req.agent_name == "teaching_agent"


def test_safety_check_request():
    req = SafetyCheckRequest(action_type="create_task", content="test", external_user_id="u001")
    assert req.action_type == "create_task"


def test_confirmation_request():
    req = ConfirmationRequest(
        external_user_id="u001",
        action_type="create_task",
        action_summary="create task",
    )
    assert req.action_type == "create_task"


def test_rag_search_request():
    req = RAGSearchRequest(query="test query")
    assert req.query == "test query"
    assert req.top_k == 5


def test_chat_response_schema():
    response = ChatResponse(
        conversation_id="c001",
        message_id="m001",
        content="ok",
        actions=[],
        created_at="2026-07-04T00:00:00Z",
    )
    assert response.role == "assistant"


def test_assistant_plan_schema():
    plan = AssistantPlan(
        intent="direct_chat",
        execution_mode="direct",
        confidence=0.9,
        reason="user greeting",
    )
    assert plan.intent == "direct_chat"
    assert plan.execution_mode == "direct"
    assert plan.route == "direct_chat_with_product_rag"
    assert plan.confidence == 0.9


def test_assistant_plan_invalid_route():
    with pytest.raises(ValidationError):
        AssistantPlan(
            intent="direct_chat",
            execution_mode="direct",
            route="invalid_route",
            confidence=0.5,
            reason="test",
        )
