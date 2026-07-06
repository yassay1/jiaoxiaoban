"""Test /api/assistant/resume flow correctness.

Focus: verify that resume creates a real AgentRun before using
its ID as a foreign key in HandoffRecord.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_fake_msg(msg_id: str = None, conversation_id: str = None) -> MagicMock:
    msg = MagicMock()
    msg.id = msg_id or str(uuid.uuid4())
    msg.conversation_id = conversation_id or str(uuid.uuid4())
    msg.role = "assistant"
    msg.content = "ok"
    return msg


class TestResumeUsesCreateRun:
    """resume 必须通过 create_run 创建真实的 AgentRun，不能直接用 uuid.uuid4()。"""

    @pytest.mark.asyncio
    async def test_resume_calls_create_run_not_raw_uuid(self):
        """验证 resume 流程调用了 create_run 而不是 uuid.uuid4() 作为 run_id。"""
        from app.services.agent_run_service import create_run

        fake_run_id = "run-resume-001"
        fake_msg = _make_fake_msg("msg-resume-001")

        with patch(
            "app.api.assistant.create_run",
            new=AsyncMock(return_value=fake_run_id),
        ) as mock_create_run, patch(
            "app.api.assistant.build_assistant_graph",
            return_value=MagicMock(),
        ), patch(
            "app.api.assistant.get_or_create_conversation",
            new=AsyncMock(),
        ), patch(
            "app.api.assistant.save_message",
            new=AsyncMock(return_value=fake_msg),
        ), patch(
            "app.api.assistant.get_recent_messages",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.api.assistant.update_run",
            new=AsyncMock(),
        ):
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={
                "final_response": "已跳转",
                "external_user_id": "u001",
                "navigation_action": {
                    "action_type": "navigate",
                    "target_agent": "teaching_agent",
                },
                "actions": [{"type": "handoff"}],
            })

            with patch(
                "app.api.assistant.build_assistant_graph",
                return_value=mock_graph,
            ):
                from app.api.assistant import ResumeRequest, assistant_resume
                from unittest.mock import MagicMock as Mock

                req = ResumeRequest(
                    conversation_id="conv-001",
                    decision="approve",
                    payload={},
                )
                mock_request = Mock()
                mock_request.app.state.checkpointer = None

                mock_db = AsyncMock()
                mock_db.flush = AsyncMock()

                await assistant_resume(req, mock_request, mock_db)

                mock_create_run.assert_called_once()
                call_kwargs = mock_create_run.call_args.kwargs
                assert call_kwargs["graph_name"] == "assistant_graph_resume"
                assert call_kwargs["conversation_id"] == "conv-001"

    @pytest.mark.asyncio
    async def test_handoff_record_uses_persisted_run_id(self):
        """验证 HandoffRecord.agent_run_id 来自 create_run 返回的已持久化 ID。"""
        persisted_run_id = "run-persisted-002"
        fake_msg = _make_fake_msg("msg-002")

        with patch(
            "app.api.assistant.create_run",
            new=AsyncMock(return_value=persisted_run_id),
        ), patch(
            "app.api.assistant.update_run",
            new=AsyncMock(),
        ), patch(
            "app.api.assistant.save_message",
            new=AsyncMock(return_value=fake_msg),
        ), patch(
            "app.api.assistant.get_or_create_conversation",
            new=AsyncMock(),
        ), patch(
            "app.api.assistant.get_recent_messages",
            new=AsyncMock(return_value=[]),
        ):
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={
                "final_response": "已跳转",
                "external_user_id": "u001",
                "navigation_action": {
                    "action_type": "navigate",
                    "target_agent": "teaching_agent",
                },
                "actions": [{"type": "handoff"}],
            })

            with patch(
                "app.api.assistant.build_assistant_graph",
                return_value=mock_graph,
            ):
                from app.api.assistant import ResumeRequest, assistant_resume

                req = ResumeRequest(
                    conversation_id="conv-002",
                    decision="approve",
                    payload={},
                )
                mock_request = MagicMock()
                mock_request.app.state.checkpointer = None
                mock_db = AsyncMock()
                mock_db.flush = AsyncMock()

                await assistant_resume(req, mock_request, mock_db)

                # 检查传入 HandoffRecord 的 agent_run_id 是 create_run 返回的 ID
                handoff_calls = [
                    c for c in mock_db.add.call_args_list
                    if hasattr(c.args[0], "agent_run_id")
                ]
                assert len(handoff_calls) >= 1
                handoff_record = handoff_calls[0].args[0]
                assert handoff_record.agent_run_id == persisted_run_id


class TestResumeMessageIdIsReal:
    """验证 resume 响应的 message_id 是真实的 message ID 而不是 run_id。"""

    @pytest.mark.asyncio
    async def test_resume_response_has_real_message_id(self):
        """resume 成功时 message_id 应为 save_message 返回的 id。"""
        real_run_id = "run-003"
        real_msg_id = "msg-real-003"
        fake_msg = _make_fake_msg(real_msg_id)

        with patch(
            "app.api.assistant.create_run",
            new=AsyncMock(return_value=real_run_id),
        ), patch(
            "app.api.assistant.update_run",
            new=AsyncMock(),
        ), patch(
            "app.api.assistant.save_message",
            new=AsyncMock(return_value=fake_msg),
        ), patch(
            "app.api.assistant.get_or_create_conversation",
            new=AsyncMock(),
        ), patch(
            "app.api.assistant.get_recent_messages",
            new=AsyncMock(return_value=[]),
        ):
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={
                "final_response": "已确认跳转",
                "navigation_action": {
                    "action_type": "navigate",
                    "target_agent": "science_agent",
                },
                "actions": [],
            })

            with patch(
                "app.api.assistant.build_assistant_graph",
                return_value=mock_graph,
            ):
                from app.api.assistant import ResumeRequest, assistant_resume

                req = ResumeRequest(
                    conversation_id="conv-003",
                    decision="approve",
                    payload={},
                )
                mock_request = MagicMock()
                mock_request.app.state.checkpointer = None
                mock_db = AsyncMock()
                mock_db.flush = AsyncMock()

                response = await assistant_resume(req, mock_request, mock_db)

                # message_id 应为 save_message 返回的真实 id，不是 run_id
                assert response.message_id == real_msg_id
                assert response.message_id != real_run_id


class TestResumeErrorHandlerUpdatesRun:
    """resume 失败时必须调用 update_run 将状态标记为 failed。"""

    @pytest.mark.asyncio
    async def test_resume_error_calls_update_run_failed(self):
        """graph.ainvoke 抛出异常时，应调用 update_run(status='failed')。"""
        run_id = "run-error-004"
        fake_msg = _make_fake_msg()

        with patch(
            "app.api.assistant.create_run",
            new=AsyncMock(return_value=run_id),
        ) as mock_create, patch(
            "app.api.assistant.update_run",
            new=AsyncMock(),
        ) as mock_update, patch(
            "app.api.assistant.save_message",
            new=AsyncMock(),
        ), patch(
            "app.api.assistant.get_or_create_conversation",
            new=AsyncMock(),
        ), patch(
            "app.api.assistant.get_recent_messages",
            new=AsyncMock(return_value=[]),
        ):
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("graph error"))

            with patch(
                "app.api.assistant.build_assistant_graph",
                return_value=mock_graph,
            ):
                from app.api.assistant import ResumeRequest, assistant_resume

                req = ResumeRequest(
                    conversation_id="conv-004",
                    decision="approve",
                    payload={},
                )
                mock_request = MagicMock()
                mock_request.app.state.checkpointer = None
                mock_db = AsyncMock()
                mock_db.flush = AsyncMock()

                await assistant_resume(req, mock_request, mock_db)

                # 确认 update_run 被调用且状态为 failed
                update_calls = [
                    c for c in mock_update.call_args_list
                    if c.kwargs.get("status") == "failed"
                ]
                assert len(update_calls) >= 1


class TestCreateRunCalledWithCorrectParams:
    """验证 create_run 被调用时参数正确。"""

    @pytest.mark.asyncio
    async def test_create_run_receives_graph_name_and_input(self):
        """create_run 应接收正确的 graph_name 和 input_data。"""
        from app.services.agent_run_service import create_run as real_create_run

        # 验证 create_run 函数签名接受这些参数
        import inspect
        sig = inspect.signature(real_create_run)
        params = list(sig.parameters.keys())
        assert "graph_name" in params
        assert "input_data" in params
        assert "conversation_id" in params
        assert "db" in params
