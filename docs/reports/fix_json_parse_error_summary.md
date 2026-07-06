# JSON 解析错误修复总结

## 1. 修复背景

调用 `POST /api/assistant/chat` 时，接口返回：

```json
{
  "content": "处理请求时出错：Expecting value: line 1 column 1 (char 0)"
}
```

错误来自 `json.loads("")` — 大模型输出不是合法 JSON 时，Planner 链直接崩溃。

## 2. 主要原因

1. **`assistant_planner_chain.py`** — `json.loads(raw)` 无保护直接解析，未传 `output_schema` 启用 JSON mode
2. **`assistant_graph.py`** — 节点只捕获 `LLMNotConfiguredError`，不捕获 `JSONDecodeError` / `ValidationError`
3. **7 个 chain 文件** — 全部直接调用 `json.loads(raw)`，无安全解析保护
4. **4 个专业 Agent** — `create_run()` 调用使用位置参数，与函数签名 `(db, graph_name, input_data, conversation_id)` 不匹配

## 3. 本次修改内容

| 文件 | 修改 |
|------|------|
| `app/utils/__init__.py` | 新增 |
| `app/utils/json_utils.py` | 新增 — `safe_json_loads()` + `extract_json_text()` |
| `app/chains/assistant_planner_chain.py` | 传入 `output_schema`，使用 `safe_json_loads`，增加 fallback 降级 |
| `app/graphs/assistant_graph.py` | `node_assistant_planner` 增加通用 `except Exception` 兜底 |
| `app/chains/agent_recommend_chain.py` | `json.loads(raw)` → `safe_json_loads(raw, source="agent_recommend")` |
| `app/chains/intent_router_chain.py` | `json.loads(raw)` → `safe_json_loads(raw, source="intent_router")` |
| `app/chains/post_analysis_chain.py` | `json.loads(raw)` → `safe_json_loads(raw, source="post_analysis")` |
| `app/chains/safety_check_chain.py` | `json.loads(raw)` → `safe_json_loads(raw, source="safety_check")` |
| `app/chains/task_fields_extract_chain.py` | `json.loads(raw)` → `safe_json_loads` + Pydantic fallback |
| `app/chains/task_draft_chain.py` | `json.loads(raw)` → `safe_json_loads(raw, source="task_draft")` |
| `app/chains/reminder_fields_extract_chain.py` | `json.loads(raw)` → `safe_json_loads` + Pydantic fallback |
| `app/agents/teaching_agent.py` | `create_run` 位置参数 → 关键字参数 |
| `app/agents/postgraduate_agent.py` | 同上 |
| `app/agents/science_agent.py` | 同上 |
| `app/agents/life_agent.py` | 同上 |
| `app/api/assistant.py` | 增加 `logging` + `traceback.format_exc()` |
| `tests/test_json_utils.py` | 新增 — 16 个单元测试 |
| `tests/test_assistant_planner_chain.py` | 新增 — 4 个 fallback 测试 |

## 4. LangGraph 流程优化点

- **State**: planner 失败时 `state["errors"]` 记录错误，`state["assistant_plan"]` 写入降级路由
- **Node**: `node_assistant_planner` 只负责规划，错误不向外抛
- **Conditional Edge**: `route_by_plan` 已能识别 `error` 状态和 fallback route
- **Fallback**: 结构化输出失败 → 日志记录 → 降级为 `direct_chat_with_product_rag` → 正常返回

## 5. 验证结果

- `python -m compileall app` — 全部编译通过
- `pytest tests/` — 41/41 通过（新增 20 个 + 原有 21 个，无回归）
- 全局搜索 `json.loads(raw)` — 0 结果（已全部替换）
- 全局搜索位置参数 `create_run(` — 4 个专业 Agent 已全部改为关键字参数

未能运行接口级端到端测试，原因：项目需要真实 LLM 配置（`LLM_API_KEY`、`LLM_API_BASE`、`LLM_MODEL_NAME`）才能启动 `/api/assistant/chat` 的完整流程。已完成所有可离线验证的静态检查和单元测试。

## 6. 后续建议

- 接入真实 LLM 后，用 Swagger 或 curl 测试 `/api/assistant/chat` 确认不再返回 `Expecting value`
- 继续接入数据库 session，实现真正的会话持久化（`node_load_memory`、`node_save_user_message`、`node_save_assistant_message` 当前为 stub）
- 恢复 `pending_state` 机制，使社区任务创建/删除的多轮确认流程可用
- 为 `llm_structured_output()` 引入 Pydantic `with_structured_output()` 以进一步减少手写 JSON 解析
