from unittest.mock import AsyncMock, patch

import pytest

from app.services.handoff_context_service import (
    build_handoff_context,
    format_handoff_context_for_prompt,
    parse_handoff_context,
)


def test_handoff_context_round_trip_and_prompt_format():
    raw = build_handoff_context(
        source="assistant",
        target_agent="postgraduate_agent",
        user_message="我想保研，但是不知道怎么规划",
        conversation_id="conv-001",
        external_user_id="u001",
        reason="私人助理判断该问题更适合保研 Agent。",
        summary="用户需要保研规划建议。",
    )

    parsed = parse_handoff_context(raw)
    assert parsed["source"] == "assistant"
    assert parsed["target_agent"] == "postgraduate_agent"
    assert parsed["conversation_id"] == "conv-001"
    assert parsed["external_user_id"] == "u001"

    prompt = format_handoff_context_for_prompt(raw)
    assert "来源：assistant" in prompt
    assert "转接原因：私人助理判断该问题更适合保研 Agent。" in prompt
    assert "上下文摘要：用户需要保研规划建议。" in prompt
    assert "用户原问题：我想保研，但是不知道怎么规划" in prompt


def test_plain_text_handoff_context_still_formats():
    prompt = format_handoff_context_for_prompt("用户想咨询培养方案")
    assert prompt == "上下文摘要：用户想咨询培养方案"


@pytest.mark.asyncio
async def test_professional_agent_runner_passes_handoff_context_to_graph():
    from app.agents.professional_agent_runner import run_professional_agent

    captured = {}

    async def fake_ainvoke(initial_state):
        captured.update(initial_state)
        return {
            "response": "ok",
            "boundary_reminder": "boundary",
        }

    fake_graph = AsyncMock()
    fake_graph.ainvoke.side_effect = fake_ainvoke

    with patch("app.agents.professional_agent_runner.create_run", new=AsyncMock(return_value="run-001")), patch(
        "app.agents.professional_agent_runner.update_run", new=AsyncMock()
    ), patch("app.agents.professional_agent_runner.professional_agent_graph", fake_graph):
        result = await run_professional_agent(
            agent_name="postgraduate_agent",
            user_message="继续讲讲",
            external_user_id="u001",
            conversation_id="conv-001",
            handoff_context="ctx-json",
        )

    assert captured["handoff_context"] == "ctx-json"
    assert captured["agent_name"] == "postgraduate_agent"
    assert result["content"] == "ok"
