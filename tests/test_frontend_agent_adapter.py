from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.chat import ChatResponse
from app.services import frontend_agent_adapter_service as adapter


@pytest.mark.asyncio
async def test_frontend_personal_assistant_metadata_uses_real_run_id(monkeypatch):
    monkeypatch.setattr(adapter, "check_llm_configured", lambda: True)
    monkeypatch.setattr(adapter, "_append_message", lambda *args, **kwargs: None)

    async def fake_assistant_chat(*args, **kwargs):
        return ChatResponse(
            conversation_id="conv-001",
            message_id="msg-001",
            run_id="run-001",
            role="assistant",
            content="ok",
            agent_name=None,
            actions=[],
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(adapter, "assistant_chat", fake_assistant_chat)

    result = await adapter.chat_with_frontend_agent(
        request=MagicMock(),
        db=MagicMock(),
        agent_id="personal-assistant",
        message="hello",
        user_id="u1",
    )

    assert result["metadata"]["message_id"] == "msg-001"
    assert result["metadata"]["run_id"] == "run-001"
    assert result["metadata"]["run_id"] != result["metadata"]["message_id"]