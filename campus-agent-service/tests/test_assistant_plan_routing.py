import pytest

from app.chains.assistant_planner_chain import AssistantPlan


class TestAssistantPlanRouting:
    @pytest.mark.parametrize(
        ("message", "plan_data", "expected_intent", "expected_mode", "expected_agent", "expected_route", "expected_community_intent"),
        [
            (
                "我想问一下你能做什么",
                {"intent": "direct_chat", "execution_mode": "direct", "confidence": 0.9, "slots": {}, "reason": "platform question"},
                "direct_chat",
                "direct",
                None,
                "direct_chat_with_product_rag",
                None,
            ),
            (
                "我想问培养方案和选课",
                {"intent": "professional_consult", "execution_mode": "handoff", "target_agent": "teaching_agent", "confidence": 0.9, "slots": {}, "reason": "academic affairs"},
                "professional_consult",
                "handoff",
                "teaching_agent",
                "professional_agent_dispatch",
                None,
            ),
            (
                "我想保研，但是不知道怎么规划",
                {"intent": "professional_consult", "execution_mode": "handoff", "target_agent": "postgraduate_agent", "confidence": 0.9, "slots": {}, "reason": "postgraduate planning"},
                "professional_consult",
                "handoff",
                "postgraduate_agent",
                "professional_agent_dispatch",
                None,
            ),
            (
                "高数极限不会做",
                {"intent": "professional_consult", "execution_mode": "handoff", "target_agent": "science_agent", "confidence": 0.9, "slots": {}, "reason": "course tutoring"},
                "professional_consult",
                "handoff",
                "science_agent",
                "professional_agent_dispatch",
                None,
            ),
            (
                "宿舍报修怎么办",
                {"intent": "professional_consult", "execution_mode": "handoff", "target_agent": "life_agent", "confidence": 0.9, "slots": {}, "reason": "campus life service"},
                "professional_consult",
                "handoff",
                "life_agent",
                "professional_agent_dispatch",
                None,
            ),
            (
                "帮我发个求助，明天找人帮我取快递",
                {"intent": "community_create_task", "execution_mode": "workflow", "confidence": 0.9, "slots": {"task": "取快递"}, "reason": "create help task"},
                "community_create_task",
                "workflow",
                None,
                "community_agent",
                "create_help_task",
            ),
            (
                "有没有人今晚一起拼车",
                {"intent": "community_search_task", "execution_mode": "workflow", "confidence": 0.9, "slots": {"keyword": "拼车"}, "reason": "search help task"},
                "community_search_task",
                "workflow",
                None,
                "community_agent",
                "search_help_task",
            ),
            (
                "帮我删掉我刚才发布的快递任务",
                {"intent": "community_delete_task", "execution_mode": "workflow", "confidence": 0.9, "slots": {"target": "快递任务"}, "reason": "delete own task"},
                "community_delete_task",
                "workflow",
                None,
                "community_agent",
                "delete_own_help_task",
            ),
        ],
    )
    def test_plan_derives_expected_route_fields(
        self,
        message,
        plan_data,
        expected_intent,
        expected_mode,
        expected_agent,
        expected_route,
        expected_community_intent,
    ):
        plan = AssistantPlan(**plan_data)
        assert message
        assert plan.intent == expected_intent
        assert plan.execution_mode == expected_mode
        assert plan.target_agent == expected_agent
        assert plan.route == expected_route
        assert plan.community_intent == expected_community_intent

    def test_route_by_plan_uses_structured_plan_fields(self):
        from app.graphs.assistant_graph import route_by_plan

        assert route_by_plan({"assistant_plan": {"intent": "professional_consult", "execution_mode": "handoff"}}) == "professional_agent_dispatch"
        assert route_by_plan({"assistant_plan": {"intent": "community_search_task", "execution_mode": "workflow"}}) == "community_agent"
        assert route_by_plan({"assistant_plan": {"intent": "direct_chat", "execution_mode": "direct"}}) == "direct_chat_with_product_rag"
        assert route_by_plan({"assistant_plan": {"intent": "unknown", "execution_mode": "clarify"}}) == "direct_chat_with_product_rag"

    @pytest.mark.asyncio
    async def test_community_entry_does_not_duplicate_confirmation(self):
        from app.graphs.assistant_graph import node_community_agent_entry, route_after_confirm

        state = {
            "community_intent": "create_help_task",
            "user_message": "帮我发个求助，明天找人帮我取快递",
            "assistant_plan": {"intent": "community_create_task", "execution_mode": "workflow"},
            "actions": [],
        }

        result = await node_community_agent_entry(state)
        assert result["needs_confirm"] is False
        assert result["actions"] == [{"type": "community_agent", "intent": "create_help_task"}]
        assert route_after_confirm(result) == "execute_confirmed_action"

@pytest.mark.asyncio
async def test_execute_handoff_requires_prior_confirmation():
    from app.graphs.assistant_graph import node_execute_confirmed_action

    state = {
        "assistant_plan": {"intent": "professional_consult", "execution_mode": "handoff"},
        "suggested_agent": "science_agent",
        "user_message": "高数题不会做",
        "confirmations": [],
        "actions": [],
    }

    result = await node_execute_confirmed_action(state)
    assert result["navigation_action"] is None
    assert result["actions"] == [{"type": "confirmation_required", "action": "handoff_professional_agent"}]
    assert "确认" in result["response"]