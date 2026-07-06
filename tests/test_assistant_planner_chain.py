from unittest.mock import AsyncMock, patch

import pytest

from app.chains.assistant_planner_chain import AssistantPlan, plan_assistant_action


class TestAssistantPlannerFallback:
    @pytest.mark.asyncio
    async def test_non_json_output_falls_back_to_direct_chat(self):
        with patch(
            "app.chains.assistant_planner_chain.llm_structured_output",
            new=AsyncMock(return_value="not json"),
        ):
            plan = await plan_assistant_action("hello")
            assert isinstance(plan, AssistantPlan)
            assert plan.intent == "direct_chat"
            assert plan.execution_mode == "direct"
            assert plan.route == "direct_chat_with_product_rag"
            assert plan.confidence == 0.3
            assert "fell back" in plan.reason

    @pytest.mark.asyncio
    async def test_empty_string_output_falls_back(self):
        with patch(
            "app.chains.assistant_planner_chain.llm_structured_output",
            new=AsyncMock(return_value=""),
        ):
            plan = await plan_assistant_action("hello")
            assert isinstance(plan, AssistantPlan)
            assert plan.intent == "direct_chat"
            assert plan.route == "direct_chat_with_product_rag"
            assert "fell back" in plan.reason

    @pytest.mark.asyncio
    async def test_markdown_json_output_parses_correctly(self):
        with patch(
            "app.chains.assistant_planner_chain.llm_structured_output",
            new=AsyncMock(
                return_value=(
                    "```json\n"
                    '{"intent": "direct_chat", "execution_mode": "direct", '
                    '"confidence": 0.9, "need_confirmation": false, '
                    '"target_agent": null, "slots": {}, "reason": "simple greeting"}'
                    "\n```"
                )
            ),
        ):
            plan = await plan_assistant_action("hello")
            assert isinstance(plan, AssistantPlan)
            assert plan.intent == "direct_chat"
            assert plan.execution_mode == "direct"
            assert plan.route == "direct_chat_with_product_rag"
            assert plan.confidence == 0.9

    @pytest.mark.asyncio
    async def test_professional_handoff_plan_derives_route(self):
        with patch(
            "app.chains.assistant_planner_chain.llm_structured_output",
            new=AsyncMock(
                return_value=(
                    '{"intent": "professional_consult", "execution_mode": "handoff", '
                    '"target_agent": "postgraduate_agent", "confidence": 0.8, '
                    '"slots": {}, "reason": "user asks postgraduate planning"}'
                )
            ),
        ):
            plan = await plan_assistant_action("我想保研，但是不知道怎么规划")
            assert plan.intent == "professional_consult"
            assert plan.execution_mode == "handoff"
            assert plan.target_agent == "postgraduate_agent"
            assert plan.route == "professional_agent_dispatch"
            assert plan.need_clarification is False
            assert plan.clarification_question is None

    @pytest.mark.asyncio
    async def test_community_create_plan_derives_workflow_fields(self):
        with patch(
            "app.chains.assistant_planner_chain.llm_structured_output",
            new=AsyncMock(
                return_value=(
                    '{"intent": "community_create_task", "execution_mode": "workflow", '
                    '"target_agent": null, "need_confirmation": true, "confidence": 0.86, '
                    '"slots": {"task": "取快递"}, "reason": "user wants to publish a help task"}'
                )
            ),
        ):
            plan = await plan_assistant_action("帮我发个求助，明天找人帮我取快递")
            assert plan.intent == "community_create_task"
            assert plan.execution_mode == "workflow"
            assert plan.route == "community_agent"
            assert plan.community_intent == "create_help_task"
            assert plan.need_confirmation is True

    @pytest.mark.asyncio
    async def test_legacy_route_output_is_still_supported(self):
        with patch(
            "app.chains.assistant_planner_chain.llm_structured_output",
            new=AsyncMock(
                return_value=(
                    '{"route": "community_agent", "community_intent": "search_help_task", '
                    '"intent": "legacy text", "confidence": 0.7, "reason": "legacy planner format"}'
                )
            ),
        ):
            plan = await plan_assistant_action("有没有人今晚一起拼车")
            assert plan.intent == "community_search_task"
            assert plan.execution_mode == "workflow"
            assert plan.route == "community_agent"
