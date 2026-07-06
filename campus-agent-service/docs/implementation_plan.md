# 实现计划

日期：2026-05-24

## 总体策略

保留现有 70% 代码（settings, schemas, chains, models 基础, services 基础, docs），重构 20%（assistant_graph, community_task_graph → community_agent_subgraph, agent_run_service → DB-backed），新建 10%（reminder 系统, pending_state 服务, 测试, seed data）。

## Phase 0: 审计 ✅

产出 docs/old_project_audit.md 和本文档。

## Phase 1: 工程基础设施

- 补充 `pyproject.toml`（pytest 配置）
- 完善 `Dockerfile`（multistage 可选）
- 添加 logging 配置
- 添加全局异常处理
- 确保 Swagger 可访问

验证: `python -m compileall app && docker compose config`

## Phase 2: 数据库模型补充

- 新增 `ReminderDraft` 模型
- 新增 `Reminder` 模型
- 新增 `ProfessionalAgentSession` 模型
- 新增 `HandoffRecord` 模型
- 补充 `app/db/init_db.py`

验证: 模型可 import

## Phase 3: LLM 服务完善

- 实现 `assistant_planner_chain`（AssistantPlan structured output）
- 实现 `task_fields_extract_chain`
- 实现 `reminder_fields_extract_chain`
- 完善 `direct_chat_chain`

验证: mock LLM 输出可被 Pydantic 校验

## Phase 4: Agent Runtime 服务

- 重构 `agent_run_service` → DB-backed
- 新建 `message_service`
- 新建 `pending_state_service`（Redis）
- 新建 `confirmation_service`（DB）
- 新建 `tool_call_service`
- 新建 `conversation_service`

验证: 调用后可在 DB/Redis 查询

## Phase 5: assistant_graph 重构

按架构契约实现完整流程：
- create_run_and_validate_input
- load_memory_and_context
- save_user_message
- assistant_planner
- route_by_plan（条件边）
- professional_agent_dispatch
- community_agent（子图入口）
- reminder_create_tool_node
- direct_chat_with_product_rag
- execute_lightweight_actions
- save_assistant_message_and_update_run

验证: mock LLM 下各路由正确

## Phase 6: community_agent_subgraph

- community_entry
- community_pending_router
- create_help_task_flow（extract → validate → ask → draft → confirm → publish）
- delete_own_help_task_flow（identify → search → ownership → confirm → delete）
- search_help_task_flow（extract → normalize → search → format）
- MockCommunityServiceAdapter
- 对应 API: search-help-tasks, delete-my-help-task

验证: 创建/删除/查找流程完整

## Phase 7: reminder flow

- reminder_entry
- reminder_pending_router
- extract → validate → draft → confirm → create
- POST /api/reminders

验证: 提醒创建流程完整

## Phase 8: professional_agent 完善

- professional_agent_sessions 模型
- handoff_records 模型
- POST /api/agents/sessions
- assistant_graph 中的 handoff 逻辑完善

验证: 可创建 session 和 handoff

## Phase 9: RAG 与 seed 数据

- 产品说明 seed 数据（JSON/CSV）
- 专业 Agent 知识文档
- 导入脚本
- rag_service 接入

验证: 可搜索产品说明

## Phase 10: 测试

- test_health.py
- test_llm_config_missing.py
- test_assistant_direct_chat.py
- test_professional_handoff.py
- test_community_search.py
- test_community_create_confirmation.py
- test_community_delete_confirmation.py
- test_reminder_create_confirmation.py
- test_agent_runs.py

验证: pytest 通过

## Phase 11: 最终自测

- `python -m compileall app`
- `pytest`
- `ruff check .`
- `docker compose config`
- FastAPI TestClient 集成测试
- 输出最终总结

## 风险点

1. **LLM 已配置真实 API**（ZhiPu GLM-4-Flash），实际调用会消耗 token
2. **无独立测试数据库** — 测试需 mock 或使用 SQLite
3. **Redis 需本地运行** — 或使用 fakeredis for tests
4. **LangGraph 版本兼容性** — Python 3.13 + langgraph 0.2.x 需验证
