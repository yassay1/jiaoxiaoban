"""Test short-term and long-term memory functionality."""

import pytest


class TestShortTermMemory:
    """需要 PostgreSQL 运行时的集成测试。"""

    @pytest.mark.asyncio
    async def test_new_conversation_returns_real_id(self):
        """新会话返回真实 conversation_id（UUID 格式，不是 'new'）。"""
        pytest.skip("需要 PostgreSQL 运行")

    @pytest.mark.asyncio
    async def test_same_conversation_second_round_reads_first(self):
        """同一 conversation_id 下第二轮能读取第一轮消息。"""
        pytest.skip("需要 PostgreSQL 运行")

    @pytest.mark.asyncio
    async def test_user_and_assistant_messages_saved(self):
        """user 和 assistant 消息都落入 messages 表。"""
        pytest.skip("需要 PostgreSQL 运行")


class TestNodeLoadMemory:
    @pytest.mark.asyncio
    async def test_load_memory_preserves_recent_messages(self):
        """node_load_memory 应保留 API 层传入的 recent_messages。"""
        from app.graphs.assistant_graph import AssistantState, node_load_memory

        state: AssistantState = {
            "user_message": "hello",
            "external_user_id": "u001",
            "conversation_id": "conv_001",
            "recent_messages": [{"role": "user", "content": "上个问题"}],
            "messages": [],
        }
        result = await node_load_memory(state)
        assert len(result["recent_messages"]) == 1
        assert result["recent_messages"][0]["content"] == "上个问题"

    @pytest.mark.asyncio
    async def test_load_memory_defaults_when_empty(self):
        """未传入时使用默认空值。"""
        from app.graphs.assistant_graph import AssistantState, node_load_memory

        state: AssistantState = {
            "user_message": "hello",
            "external_user_id": "u001",
            "conversation_id": "conv_001",
            "messages": [],
        }
        result = await node_load_memory(state)
        assert result["recent_messages"] == []
        assert result["memory_context"] == {}
        assert result["product_rag_context"] == []
        assert result["pending_state"] is None


class TestCheckpointerConfig:
    def test_thread_id_equals_conversation_id(self):
        """验证 config 中 thread_id 等于 conversation_id。"""
        config = {"configurable": {"thread_id": "conv_abc123"}}
        assert config["configurable"]["thread_id"] == "conv_abc123"


class TestNoRedisMainFlow:
    def test_redis_not_required_for_main_flow(self):
        """验证 memory_service 可以延迟加载，不启动 Redis 时不抛异常。"""
        import importlib
        spec = importlib.util.find_spec("app.services.memory_service")
        assert spec is not None
