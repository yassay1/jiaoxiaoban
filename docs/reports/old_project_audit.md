# 旧项目审计报告

审计日期：2026-05-24

## 整体评价

v1.0 是一个可编译的架构良好的骨架项目。核心设计方向正确（LLM-driven Agent, API-constrained Execution），模块划分清晰，但距离 spec 要求有显著差距。

## 编译状态

✅ `python -m compileall app` — 全部通过

## 保留模块

| 模块 | 评级 | 说明 |
|------|------|------|
| `app/main.py` | 良 | FastAPI 入口，路由注册合理 |
| `app/config/settings.py` | 优 | Pydantic Settings，llm_configured 属性设计好 |
| `app/db/session.py` | 良 | Async SQLAlchemy，需补充 init_db |
| `app/db/models.py` | 良 | 13 个模型，覆盖核心表，缺少 reminder 相关 |
| `app/schemas/*` | 优 | Pydantic schema 定义完整，可复用 |
| `app/services/llm_service.py` | 优 | LLMNotConfiguredError 设计正确，需扩展 |
| `app/services/memory_service.py` | 良 | Redis 封装，需补充 pending_state 方法 |
| `app/services/community_client.py` | 良 | HTTP adapter 模式正确，需补充 mock 实现 |
| `app/chains/*` | 良 | LLM prompt 链完整，可复用 |
| `app/graphs/professional_agent_graph.py` | 良 | 流程正确，可保留 |
| `app/graphs/safety_graph.py` | 良 | 流程正确，需补充条件路由 |
| `app/data_processing/*` | 良 | Polars 脚本完整，可保留 |
| `app/api/health.py` | 优 | 健康检查正确 |
| `docs/*.md` | 良 | 文档覆盖齐全 |

## 需重构模块

| 模块 | 问题 | 行动 |
|------|------|------|
| `app/graphs/assistant_graph.py` | 节点不完整，缺少 load_memory、save_message、reminder/community 路由 | 按架构契约完整重写 |
| `app/graphs/community_task_graph.py` | 仅覆盖帖子转任务，缺少 chat 驱动的创建/删除/查找 | 重构为 community_agent_subgraph |
| `app/services/agent_run_service.py` | 使用内存 dict，未接入 PostgreSQL | 接入 DB，补充 tool_call_log |
| `app/api/confirmations.py` | 使用内存 dict，未接入 DB | 接入 confirmation_service |
| `app/agents/assistant_agent.py` | 直接调用 graph，缺少 message/run/conversation 持久化 | 补充完整 service 层 |
| `app/tools/*` | 全部为占位实现 | 接入真实 service |

## 缺失模块（需新建）

| 模块 | 说明 |
|------|------|
| `app/graphs/reminder_graph.py` | 提醒创建流程 |
| `app/api/reminders.py` | 提醒 API |
| `app/services/pending_state_service.py` | Redis pending_state 管理 |
| `app/services/message_service.py` | 消息持久化 |
| `app/services/confirmation_service.py` | 确认记录 DB 操作 |
| `app/services/tool_call_service.py` | Tool call 日志 |
| `app/services/conversation_service.py` | 会话管理 |
| `app/services/mock_community_adapter.py` | Mock 社区接口 |
| `tests/` | 测试目录 |
| `app/db/seed_data/` | RAG seed 数据 |

## 数据库模型缺失

- `reminders` 表
- `reminder_drafts` 表
- `professional_agent_sessions` 表
- `handoff_records` 表

## 结论

项目 v1.0 是一个良好的起点。核心架构方向正确，代码可编译。需要：
1. 补充缺失的模型和 API
2. 将内存数据迁移到 PostgreSQL
3. 重构 assistant_graph 为完整流程
4. 新建 reminder/community 子图
5. 补充测试

**策略：保留 70% 现有代码，重构 20%，新建 10%。**
