# 开发注意事项

## 1. 项目当前主线

当前主线不是“把所有功能都做完”，而是先把项目定位和 Agent 架构定稳。

主线：

```text
校园生活智能体平台
  ↓
私人助理总控
  ↓
专业 Agent 咨询
  ↓
社区求助任务 Workflow
  ↓
RAG / 记忆 / 确认 / 日志支撑
```

不要为了局部功能把主架构带偏。

## 2. 不要过度纠结规则兜底

规则兜底可以有，但不是当前重点。

当前重点是：

- Agent 边界清晰。
- 用户入口清晰。
- 专业 Agent 和社区任务 Agent 类型不同。
- Workflow 可解释、可维护。
- 后续能被 Codex 稳定迭代。

不要把主要开发精力放在大量 if/else 规则上。

## 3. 专业 Agent 与社区任务 Agent 的本质区别

专业 Agent 是“人设型咨询 Agent”。

社区任务 Agent 是“业务流程型 Agent”。

```text
专业 Agent:
用户可以持续多轮对话。
适合 handoff 或直接进入。
重点是咨询和解释。

社区任务 Agent:
完成创建、搜索、删除任务。
适合 workflow/subgraph。
重点是字段、确认、发布和结果。
```

不要把社区任务 Agent 做成长期闲聊入口。

## 4. 关于 B 模式

之前讨论里的 B 是：

```text
私人助理调用专业 Agent 作为工具
  ↓
专业 Agent 返回片段答案
  ↓
私人助理统一总结给用户
```

这属于 Supervisor / Subagents-as-tools 模式。

这个模式不是第一阶段主线。

它可以作为后期增强能力，用于复杂综合问题，例如：

```text
我想保研，但绩点一般，还要兼顾竞赛和生活时间，应该怎么安排？
```

后期可以让私人助理并行调用：

- postgraduate_agent
- science_agent
- life_agent

然后由私人助理综合回复。

但第一阶段仍以“直接进入专业 Agent”和“私人助理 handoff 到专业 Agent”为主。

## 5. Reminder Agent 处理原则

提醒 Agent 建议舍弃当前主线。

注意这里的“舍弃”不是必须立刻删除全部代码，而是：

- 不再作为项目核心架构讲述。
- 不再作为当前开发优先级。
- 不再让私人助理优先路由到提醒。
- 如果代码存在但不影响运行，可以暂时保留。
- 如果代码影响架构清晰度，可以逐步移除入口或标记 deprecated。

不要在当前阶段花时间优化 reminder prompt、reminder graph、reminder resume 等流程。

## 6. RAG 处理原则

RAG 第一阶段服务专业 Agent。

不要一开始做成全局万能 RAG。

推荐分域：

```text
platform
teaching_agent
postgraduate_agent
science_agent
life_agent
community_policy
```

优先导入：

- 学校教务规则。
- 培养方案。
- 保研政策和经验材料。
- 校园生活服务说明。
- 社区任务规则和安全说明。

## 7. Community Adapter 注意事项

社区服务适配层可能有 mock 和 real 两种模式。

开发时必须明确当前操作是在：

```text
mock mode
```

还是：

```text
real mode
```

如果真实社区接口还没有接好，不要返回假成功。

建议输出明确错误：

```text
真实社区服务搜索接口尚未接入
```

而不是：

```text
搜索成功，结果为空
```

两者含义不同。

## 8. Handoff 注意事项

专业 Agent 支持两种进入方式：

```text
直接进入专业 Agent 页面
私人助理推荐后进入专业 Agent
```

直接进入时，没有 assistant handoff context 也应该能正常工作。

handoff 进入时，应该保存：

- source: assistant
- target_agent
- reason
- summary
- conversation_id
- agent_session_id
- external_user_id

这样后续专业 Agent 能知道用户为什么被转过来。

## 9. Assistant Planner 注意事项

Planner 不应该只返回一个简单 route。

推荐返回：

- intent
- execution_mode
- target_agent
- confidence
- need_confirmation
- slots
- reason

这样后续图路由更稳定，也更容易测试。

## 10. Confirmation 注意事项

以下动作必须确认：

- 创建社区求助任务。
- 删除社区求助任务。
- 发布用户可见内容。
- 执行不可逆或半不可逆操作。

以下动作通常不需要确认：

- 搜索任务。
- 普通聊天。
- 专业 Agent 咨询。
- 查看已有信息。

## 11. 数据库模型注意事项

不要轻易改数据库模型。

如果必须改：

- 说明为什么必须改。
- 同步 schema 和 service。
- 考虑迁移脚本。
- 保证旧数据兼容。

优先通过已有模型完成第一阶段架构改造。

## 12. Graph 修改注意事项

修改 LangGraph 图时，必须同时检查：

- State 字段。
- Node 输入输出。
- Edge。
- Conditional edge。
- Interrupt/resume。
- API 调用入口。
- 前端 action 映射。

不要只改节点，不改路由。

## 13. LLM 结构化输出注意事项

LLM 输出 JSON 时必须考虑失败情况。

但失败兜底应该简单、清晰，不要变成一堆业务规则。

推荐：

- JSON 解析失败 → 返回 clarify 或 fallback direct。
- intent 置信度低 → ask clarification。
- target_agent 不合法 → fallback professional recommendation 或 direct chat。

## 14. 不建议的改法

不要这样改：

- 把所有逻辑塞进 prompt。
- 把所有能力放进私人助理一个 graph。
- 把专业 Agent 做成完全独立的重复代码。
- 把社区任务 Agent 做成长期聊天 Agent。
- 为了演示效果伪造真实发布结果。
- 一次性重构所有目录。
- 同时改数据库、图、API、前端映射、RAG。

## 15. 推荐的改法

推荐这样改：

```text
先定文档
  ↓
改 planner schema
  ↓
改 assistant_graph 路由
  ↓
稳定专业 Agent 双入口
  ↓
打通社区任务 workflow
  ↓
补测试
  ↓
再优化 RAG
```

每次只改一条主线，保证能解释、能回滚、能验证。

## 16. 项目答辩/展示表述

推荐表述：

> 本项目不是普通聊天机器人，而是一个面向高校场景的校园生活智能体平台。系统以私人助理作为智能入口，通过意图识别和路由分发连接专业 Agent 与社区任务工作流。专业 Agent 负责教务、保研、学习和生活等垂直咨询，支持直接进入和私人助理推荐进入；社区求助任务 Agent 则以 Workflow 形式完成任务创建、搜索和删除。底层通过 RAG、会话记忆、用户确认和运行日志保障系统的可控性与可扩展性。
