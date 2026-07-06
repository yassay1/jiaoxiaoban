# 工程假设记录

本文档记录在实现过程中做出的合理假设。如果实际环境不同，需要相应调整。

## 数据库与存储

1. **agent_run_service 双模存储**：支持 DB session 和内存 fallback。无 DB session 时使用内存存储，方便测试和无数据库环境快速启动。
2. **confirmation_service**：新建 DB-backed 服务，同时保留旧 API 内存版兼容。
3. **pending_state**：使用 Redis，key 格式为 `pending:{external_user_id}:{conversation_id}`。

## LLM

1. **已配置真实 LLM**：.env 中已配置智谱 GLM-4-Flash API Key，project 可直接智能调用。
2. **structured output 使用 JSON mode**：通过 `response_format={"type": "json_object"}` 约束输出，然后 Pydantic 校验。

## 社区接口

1. **mock_community_adapter**：MVP 阶段使用内存 mock，后期替换为 HTTP CommunityClient。
2. **任务 ID 格式**：mock adapter 生成 `task_{uuid_hex_12}` 格式。
3. **外部 ID 关联**：通过 external_user_id 关联本项目用户，通过 created_task_id 关联正式任务。

## Graph 设计

1. **assistant_graph**：使用 LLM planner 输出 `AssistantPlan` 结构化结果，通过 `route_by_plan` 条件边路由到四个分支。
2. **community_agent_subgraph**：独立子图，通过 `community_intent` 字段路由到创建/删除/查找三条路径。
3. **reminder_graph**：独立子图，暂时不连接真实推送服务。
4. **专业 Agent 共用 professional_agent_graph**：通过 agent_name 参数切换 Profile。

## 测试

1. **无需数据库的测试优先**：graph 编译测试、schema 校验测试、mock adapter 测试等不依赖 PostgreSQL/Redis。
2. **需要 LLM 的测试暂不实现**：依赖真实 LLM 调用的集成测试消耗 token，在 CI 中需要 mock。

## 未实现/预留

1. **真实向量数据库**：RAG 当前返回占位结果，pgvector 镜像已在 docker-compose 中。
2. **Alembic 迁移**：models 定义完成但未运行迁移，需要 `alembic revision --autogenerate`。
3. **提醒真实推送**：提醒记录存数据库但不发送通知。
4. **PDF 报告生成**：接口已预留但未实现。
5. **微信/Server酱推送**：预留但未实现。
6. **用户偏好/长期记忆**：memory_service 已定义接口但未深度集成。

