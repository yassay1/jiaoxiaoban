# 下一阶段开发总结

## 1. 修改背景

四个核心任务包需要对 campus-agent-service 进行系统性改造：
- 记忆系统从"假实现"改为真正打通 PostgreSQL
- 专业 Agent 从"空 RAG"改为真实向量检索
- 专业 Agent 会话从"假创建"改为真实落库
- 新增 interrupt 机制支持人机交互确认

## 2. 本次完成内容

### 记忆（Task Package 1）
- 新增 `langgraph-checkpoint-postgres` 和 `psycopg` 依赖
- 创建 `app/db/checkpointer.py`：管理 AsyncPostgresSaver 生命周期
- `/api/assistant/chat` 接入 `Depends(get_db)`，真正创建 conversation 并保存 message
- `conversation_id` = LangGraph `thread_id`，状态通过 PostgresSaver 持久化
- `node_load_memory` 改为使用 API 层传入的 recent_messages（从 PostgreSQL 加载）
- `direct_chat` 链路接收历史消息上下文
- 消息保存统一在 API 层，graph 节点不重复保存
- 新增 `user_memories` 表（`app/db/models.py`）
- 创建 `app/services/long_term_memory_service.py`：按 external_user_id 维度保存/查询长期记忆
- 长期记忆暂不自动写入，等待 interrupt 确认机制（Task Package 4）

### 专业 Agent RAG（Task Package 2）
- 安装 `pgvector` Python 包，添加 `pgvector` 依赖
- KnowledgeChunk 模型新增 `embedding` 列（pgvector Vector 类型）
- `rag_service.py`：重写为真实向量检索，使用 OpenAI embeddings + pgvector 余弦相似度
- `search_knowledge` 按 agent_name 过滤知识库，返回 source_url、section、score
- `import_knowledge_doc` 自动切片并生成 embedding
- `professional_agent_graph.py`：LLM 回答时注入 RAG 上下文和来源信息
- 无检索结果时明确告知用户，不编造
- 每个专业 Agent 的 system_prompt 强调"不知道就说不确定"
- `/api/agents/chat` 在调用 runner 前执行真实 RAG 检索

### 专业 Agent 会话（Task Package 3）
- `/api/agents/sessions` 从生成随机假 ID 改为真实写入 `professional_agent_sessions` 表
- 私人助理 handoff 时，API 层创建 `ProfessionalAgentSession` + `HandoffRecord` 记录
- `navigation_action.agent_session_id` 不再为 None，返回真实 session ID
- `/api/agents/chat` 支持 `session_id` 参数，根据 session 加载：
  - 验证 external_user_id 权限
  - 加载 handoff_context
  - 获取/创建 conversation 并保存消息
  - 无效 session_id 返回清晰错误
- 修复 `create_run()` 参数错位：`community_admin_agent.py` 和 `assistant_agent.py`

### Interrupt（Task Package 4）
- 新增 `node_confirm_check`：调用 LangGraph `interrupt()` 暂停执行
- 新增 `node_execute_confirmed_action`：用户确认后执行对应操作
- 四个确认场景：handoff 跳转、社区任务操作、提醒创建、长期记忆保存
- 新增 `POST /api/assistant/resume`：接收 `decision` (approve/reject/revise)
- 使用 `Command(resume=...)` 恢复执行，同一 `thread_id`
- 确认前不执行副作用，确认后才执行

## 3. 修改文件列表

| 文件 | 变更类型 |
|------|----------|
| `pyproject.toml` | 修改：添加依赖 |
| `app/db/checkpointer.py` | 新增 |
| `app/db/models.py` | 修改：添加 UserMemory, Vector 列 |
| `app/db/session.py` | 未修改 |
| `app/config/settings.py` | 未修改 |
| `app/api/assistant.py` | 重写：接入 DB, real IDs, handoff, resume |
| `app/api/agents.py` | 重写：real sessions, RAG, session_id 加载 |
| `app/api/rag.py` | 修改：添加 db 参数 |
| `app/graphs/assistant_graph.py` | 重写：real memory, interrupt 节点 |
| `app/graphs/professional_agent_graph.py` | 修改：RAG 上下文, 来源链接 |
| `app/services/rag_service.py` | 重写：真实 pgvector 检索 |
| `app/services/long_term_memory_service.py` | 新增 |
| `app/agents/teaching_agent.py` | 修改：接受 rag_context |
| `app/agents/postgraduate_agent.py` | 修改：接受 rag_context |
| `app/agents/science_agent.py` | 修改：接受 rag_context |
| `app/agents/life_agent.py` | 修改：接受 rag_context |
| `app/agents/assistant_agent.py` | 修改：修复 create_run 参数 |
| `app/agents/community_admin_agent.py` | 修改：修复 create_run 参数 |
| `app/schemas/agent.py` | 修改：添加 session_id 字段 |
| `tests/test_assistant_memory.py` | 新增 |
| `tests/test_conversation_persistence.py` | 新增 |

## 4. 数据库变化

- 新增表：`user_memories`（长期记忆，按 external_user_id 索引）
- 修改表：`knowledge_chunks` 新增 `embedding` 列（pgvector Vector(1536)）
- 新增 checkpointer 表：由 `AsyncPostgresSaver.setup()` 自动创建

## 5. 接口变化

- `POST /api/assistant/chat`：现在需要 DB，返回真实 conversation_id
- `POST /api/assistant/resume`：新增，用于恢复 interrupt 暂停的会话
- `POST /api/agents/sessions`：现在真实写入数据库
- `POST /api/agents/chat`：新增 `session_id` 参数，支持根据 session 加载上下文
- `POST /api/rag/search`：新增 `db` 依赖
- 所有接口响应格式兼容，无破坏性变更

## 6. 验证结果

- 46 个测试通过，6 个跳过（需要 PostgreSQL 运行的集成测试）
- `python -m compileall app` 无编译错误
- 所有 graph 编译测试通过
- 所有 schema 验证测试通过

## 7. 未完成和后续建议

1. **PostgresSaver 集成测试**：需要真实 PostgreSQL 运行时验证 checkpoint 读写
2. **知识库数据导入**：需要实际文档和 embedding 生成
3. **长期记忆自动提取**：当前只提供 CRUD，需要 LLM 识别候选记忆的链路
4. **Interrupt 完整 E2E 测试**：需要真实 LLM 配置验证完整中断-恢复流程
5. **pgvector 索引**：建议在 `knowledge_chunks.embedding` 上创建 IVFFlat 或 HNSW 索引
6. **Redis 降级为可选**：`memory_service.py` 中的 Redis 代码保留作为未来 TTL 草稿/限流等用途
