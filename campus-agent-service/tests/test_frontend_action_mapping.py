from app.services.frontend_agent_adapter_service import _map_backend_action


def test_pending_handoff_action_maps_confirmation_state():
    mapped = _map_backend_action({"type": "handoff", "target_agent": "science_agent", "needs_confirm": True})
    assert mapped["type"] == "RECOMMEND_AGENT"
    payload = mapped["payload"]
    assert payload["targetAgentId"] == "science-tutor"
    assert payload["requiresConfirmation"] is True
    assert payload["status"] == "pending"
    assert payload["confirmationAction"] == "handoff_professional_agent"


def test_confirmed_handoff_action_includes_session_id():
    mapped = _map_backend_action({
        "type": "handoff",
        "target_agent": "postgraduate_agent",
        "confirmed": True,
        "agent_session_id": "session-001",
    })
    payload = mapped["payload"]
    assert payload["targetAgentId"] == "postgraduate-agent"
    assert payload["agentSessionId"] == "session-001"
    assert payload["requiresConfirmation"] is False
    assert payload["status"] == "confirmed"


def test_interrupt_handoff_maps_pending_recommendation():
    mapped = _map_backend_action({
        "type": "interrupt",
        "interrupt_data": {
            "action": "handoff_professional_agent",
            "summary": "即将跳转到保研学长阿泽",
            "detail": {"target_agent": "postgraduate_agent", "display_name": "保研学长阿泽"},
        },
    })
    payload = mapped["payload"]
    assert mapped["type"] == "RECOMMEND_AGENT"
    assert payload["targetAgentId"] == "postgraduate-agent"
    assert payload["requiresConfirmation"] is True
    assert payload["status"] == "pending"


def test_confirm_publish_interrupt_maps_task_draft_fields():
    mapped = _map_backend_action(
        {
            "type": "interrupt",
            "interrupt_data": {
                "action": "confirm_publish_task",
                "summary": "确认发布求助任务",
                "detail": {
                    "draft_id": "draft-001",
                    "task_fields": {
                        "title": "帮忙取快递",
                        "description": "东区快递站，今晚七点前",
                        "category": "生活帮助",
                        "location": "东区快递站",
                        "expected_time": "今晚七点前",
                    },
                },
            },
        },
        user_message="帮我发个求助，今晚取快递",
    )
    assert mapped["type"] == "CREATE_TASK_DRAFT"
    payload = mapped["payload"]
    assert payload["title"] == "帮忙取快递"
    assert payload["content"] == "东区快递站，今晚七点前"
    assert payload["taskCategory"] == "生活帮助"
    assert payload["taskLocation"] == "东区快递站"
    assert payload["taskTimeText"] == "今晚七点前"
    assert payload["draftId"] == "draft-001"
    assert payload["status"] == "pending_confirmation"
    assert payload["confirmationAction"] == "confirm_publish_task"


def test_delete_interrupt_maps_generic_confirmation():
    mapped = _map_backend_action({
        "type": "interrupt",
        "interrupt_data": {
            "action": "confirm_delete_task",
            "summary": "确认删除任务",
            "detail": {"task_id": "task-001", "task_title": "帮忙取快递"},
        },
    })
    assert mapped["type"] == "AGENT_CONFIRMATION_REQUIRED"
    assert mapped["payload"]["action"] == "confirm_delete_task"
    assert mapped["payload"]["status"] == "pending"

def test_community_create_action_starts_workflow_not_draft():
    mapped = _map_backend_action(
        {"type": "community_agent", "intent": "create_help_task"},
        user_message="帮我发个求助，今晚取快递",
    )
    assert mapped["type"] == "START_COMMUNITY_WORKFLOW"
    assert mapped["payload"]["intent"] == "create_help_task"
    assert mapped["payload"]["requiresConfirmation"] is False


def test_task_cancel_actions_map_cancelled_state():
    mapped = _map_backend_action({"type": "task_delete_cancelled", "task_id": "task-001"})
    assert mapped["type"] == "AGENT_CANCELLED"
    assert mapped["payload"]["task_id"] == "task-001"