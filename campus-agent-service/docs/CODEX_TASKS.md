# Codex 开发任务池

本文档用于指导 Codex 分阶段改善项目。不要一次性重构全部模块。优先围绕项目定位和 Agent 架构做大方向调整。

## 总目标

将项目从“能跑的多 Agent Demo”升级为“架构清晰的校园生活智能体平台”。

重点不是堆规则兜底，而是把以下几件事设计清楚：

- 私人助理是什么。
- 专业 Agent 如何进入和持续对话。
- 社区求助任务 Agent 如何作为 workflow 执行业务动作。
- RAG 如何服务专业 Agent。
- 提醒功能如何从当前主线中移除或降级。

## P0：补齐项目文档与开发约束

### 目标

让 Codex 在后续开发前明确项目定位、架构边界和开发原则。

### 涉及文件

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/CODEX_TASKS.md`
- `docs/DEV_NOTES.md`
- `README.md` 可选

### 验收标准

- 文档明确项目定位为“校园生活智能体平台”。
- 文档明确专业 Agent 可直接进入，也可由私人助理 handoff 进入。
- 文档明确社区求助任务 Agent 是 workflow，不是长期聊天 Agent。
- 文档明确 reminder agent 不作为当前开发目标。
- 文档明确不要把主要精力放在规则兜底上。

## P1：重构私人助理 Planner 输出结构

### 目标

将私人助理的意图识别从简单 route 升级为清晰的执行计划。

### 推荐输出结构

```python
class AssistantPlan(BaseModel):
    intent: Literal[
        "direct_chat",
        "professional_consult",
        "community_create_task",
        "community_search_task",
        "community_delete_task",
        "unknown"
    ]
    execution_mode: Literal[
        "direct",
        "handoff",
        "workflow",
        "clarify"
    ]
    target_agent: Optional[
        Literal[
            "teaching_agent",
            "postgraduate_agent",
            "science_agent",
            "life_agent"
        ]
    ]
    need_confirmation: bool
    confidence: float
    slots: dict
    reason: str
```

### 涉及文件

- `app/chains/assistant_planner_chain.py`
- `app/graphs/assistant_graph.py`
- `app/schemas/chat.py` 可选
- `app/services/frontend_agent_adapter_service.py` 可选

### 验收标准

以下输入能得到合理计划：

```text
我想问一下你能做什么
→ direct_chat

我想问培养方案和选课
→ professional_consult + handoff + teaching_agent

我想保研，但是不知道怎么规划
→ professional_consult + handoff + postgraduate_agent

高数极限不会做
→ professional_consult + handoff + science_agent

宿舍报修怎么办
→ professional_consult + handoff + life_agent

帮我发个求助，明天找人帮我取快递
→ community_create_task + workflow

有没有人今晚一起拼车
→ community_search_task + workflow

帮我删掉我刚才发布的快递任务
→ community_delete_task + workflow
```

## P2：专业 Agent 支持双入口

### 目标

专业 Agent 既能由私人助理推荐进入，也能由用户直接从前端页面进入。

### 涉及文件

- `app/api/agents.py`
- `app/api/frontend_agents.py`
- `app/services/frontend_agent_adapter_service.py`
- `app/graphs/professional_agent_graph.py`
- `app/db/models.py`

### 推荐设计

```text
direct entry:
frontend professional page
  ↓
/api/agents/{agent_id}/chat
  ↓
professional_agent_graph

handoff entry:
assistant_graph
  ↓
professional_agent_dispatch
  ↓
create professional_agent_session
  ↓
frontend enters professional agent with session_id
  ↓
professional_agent_graph
```

### 验收标准

- 用户可以直接打开保研 Agent 页面并多轮对话。
- 私人助理推荐保研 Agent 后能创建 session。
- handoff 上下文能传入专业 Agent。
- 专业 Agent 只做咨询，不做社区任务操作。

## P3：打通私人助理到社区任务 Workflow

### 目标

用户通过私人助理发起社区任务时，系统进入 `community_agent_subgraph`，而不是普通聊天兜底。

### 涉及文件

- `app/graphs/assistant_graph.py`
- `app/graphs/community_agent_subgraph.py`
- `app/chains/assistant_planner_chain.py`
- `app/services/community_service_adapter.py`
- `app/api/assistant.py`

### 验收标准

```text
帮我发个求助，明天中午找人帮我拿快递
→ 提取字段
→ 生成草稿
→ 请求确认
→ 确认后发布

有没有人今晚一起拼车去西站
→ 搜索求助任务
→ 返回结果

帮我删掉我发布的快递任务
→ 查找我的任务
→ 匹配目标
→ 请求确认
→ 删除
```

### 注意

创建和删除必须确认。搜索不一定需要确认。

## P4：社区任务 Workflow 完整化

### 目标

完善社区任务 Agent，使它成为可解释、可测试的任务型工作流。

### 涉及文件

- `app/graphs/community_agent_subgraph.py`
- `app/chains/task_fields_extract_chain.py`
- `app/chains/safety_check_chain.py`
- `app/services/community_service_adapter.py`
- `app/services/mock_community_adapter.py`

### 改进点

- 字段提取结构更稳定。
- 缺少字段时追问更自然。
- 草稿内容更像真实校园帖子。
- 搜索结果格式更友好。
- 删除任务时支持通过标题或 task_id 匹配。
- mock 数据自动初始化或提供测试数据入口。

### 验收标准

- create/search/delete 三条路径可单独测试。
- 不依赖真实社区服务也可以 mock 演示。
- real 模式未完成的功能要明确返回“未接入”，不要假装成功。

## P5：专业 Agent RAG 优化

### 目标

优先让专业 Agent 的回答接入可靠知识库。

### 涉及文件

- `app/services/rag_service.py`
- `app/graphs/professional_agent_graph.py`
- `app/data_processing/import_knowledge_docs.py`
- `app/data_processing/clean_docs_with_polars.py`

### 推荐方向

- 按 agent_name 分域检索。
- 检索不到资料时明确说明依据不足。
- embedding 模型配置化，不要硬编码无法兼容的模型。
- 支持导入教务、保研、生活服务等知识文档。

### 验收标准

- 教学 Agent 只优先检索 teaching_agent 相关知识。
- 保研 Agent 只优先检索 postgraduate_agent 相关知识。
- 检索结果可显示来源。
- 无 RAG 结果时不编造官方政策。

## P6：移除或降级 Reminder 主线

### 目标

提醒 Agent 不再占据当前项目主线。

### 涉及文件

- `app/graphs/reminder_graph.py`
- `app/api/reminders.py`
- `app/chains/reminder_fields_extract_chain.py`
- `app/graphs/assistant_graph.py`

### 推荐处理方式

第一阶段不要删除文件，避免影响 import 和启动。

建议：

- 从 assistant planner 的主路径中移除 reminder intent，或降级为“暂不支持提醒”。
- 文档中明确 reminder 不作为当前开发目标。
- 如果前端仍有提醒页面，可以保留普通 CRUD，不把它包装成核心 Agent 能力。

### 验收标准

- 私人助理不会优先路由到 reminder_graph。
- 项目文档不再把 reminder 作为核心 Agent。
- 现有 reminder 代码不影响启动。

## P7：增加轻量测试与验证脚本

### 目标

让 Codex 每次修改后能快速验证核心架构没有坏。

### 涉及文件

- `tests/`
- `scripts/`
- `app/graphs/*`

### 推荐测试点

- assistant planner 分类测试。
- assistant_graph compile 测试。
- professional_agent_graph compile 测试。
- community_agent_subgraph compile 测试。
- professional agent profile 选择测试。
- community create/search/delete 流程测试。

### 验收标准

- 不需要真实 LLM 时可用 mock 或 fixture 做基础测试。
- 测试不依赖真实 API key。
- 至少能发现 import 错误、graph 编译错误和关键路由错误。

## P8：真实社区服务接入

### 目标

将 mock community adapter 逐步替换或扩展为真实社区服务。

### 涉及文件

- `app/services/community_client.py`
- `app/services/community_service_adapter.py`
- `app/api/community.py`

### 前提

必须先明确真实社区服务接口：

- 发布任务接口。
- 搜索任务接口。
- 删除任务接口。
- 用户身份字段。
- 任务状态字段。
- 权限规则。

### 验收标准

- mock/real 模式切换清晰。
- real 模式失败时有明确错误。
- 不把未实现接口伪装成成功。

## 推荐给 Codex 的单次任务写法

```text
请先阅读 AGENTS.md、docs/ARCHITECTURE.md、docs/CODEX_TASKS.md、docs/DEV_NOTES.md。

本次只完成 P1：重构私人助理 Planner 输出结构。

要求：
1. 不要修改 reminder_graph。
2. 不要重构数据库模型。
3. 不要删除现有 API。
4. 修改后说明涉及文件、设计理由和验证方式。
5. 重点保证架构清晰，不要堆大量规则兜底。
```

## 当前最高优先级

建议优先顺序：

```text
P0 → P1 → P2 → P3 → P4 → P5 → P7 → P8
```

提醒 Agent 相关的 P6 可以在 P1/P3 时顺手降级，不需要单独大改。
