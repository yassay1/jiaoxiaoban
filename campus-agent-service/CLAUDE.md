# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
# 交小伴 Agent Service 项目专用规则

以下内容请追加到项目根目录 `CLAUDE.md` 末尾。若与通用 CLAUDE.md 冲突，以本项目规则为准。

---

## 1. 项目定位

本项目名为 `campus-agent-service`，中文名为“交小伴 Agent Service”。

它不是普通聊天机器人。它是面向校园交流社区与求助任务平台的完整项目，包含 Agent 后端服务、社区业务能力和前端体验，并且所有能力都应服务于“交小伴”校园 Agent 系统。

产品总体定位：

```text
校园交流社区生态
+ AI 任务化互助平台
+ 多 Agent 智能服务层
```

当前开发重点：

```text
面向校园互助平台的完整校园 Agent 系统
```

---

## 2. 职责边界

当前由用户本人单人开发完整项目，范围包括：

```text
前端页面
社区帖子系统
评论点赞收藏
任务大厅
正式求助任务 help_tasks
积分系统
用户系统
社区数据库
社区审核后台
FastAPI Agent Service 后端
私人助理 Agent Graph
专业 Agent 会话与跳转
社区求助任务子代理
提醒创建流程
RAG 与记忆上下文
用户确认机制
Agent run / tool call 日志
PostgreSQL Agent 数据
Redis 临时状态
community_service_adapter
Swagger 与接口文档
Docker 本地运行
```

社区和前端是本项目的一部分。可以通过模块化 adapter 隔离 Agent 层与社区业务层，保持架构清晰。

---

## 3. 核心原则

必须遵守：

```text
LLM-driven Agent, API-constrained Execution
大模型驱动决策，接口约束执行
```

LLM 负责：

```text
用户需求理解
私人助理下一步动作规划
专业 Agent 推荐
缺失信息追问
求助任务字段提取
任务草稿生成
安全语义判断
Tool 调用规划
专业 Agent 回答
```

程序负责：

```text
Pydantic Schema 校验
状态校验
权限边界
用户确认
数据库记录
Redis pending_state
外部 API 调用
错误处理
运行日志
防止 AI 越权执行
```

不要把核心智能判断写成关键词规则，例如：

```python
if "线代" in message:
    return "science_agent"
```

关键词规则只能用于非智能边界，例如字段校验、状态校验、错误处理、权限检查、枚举映射。

---

## 4. 真实 LLM 要求

本项目必须按真实 LLM 接入设计。

不要做模拟大模型主流程。
不要伪造 Agent 判断。
不要在没有真实模型配置时返回假结果。

如果缺少以下配置：

```text
LLM_API_KEY
LLM_API_BASE
LLM_MODEL_NAME
```

所有涉及 LLM 智能判断的接口必须返回清晰错误：

```text
当前未配置真实 LLM 参数，无法执行 Agent 智能判断。请在 .env 中配置 LLM_API_KEY、LLM_API_BASE 和 LLM_MODEL_NAME。
```

健康检查、非智能 mock adapter、文档接口可以正常运行。

---

## 5. 私人助理 Agent 边界

私人助理是轻量入口助手，不是超级总控 Agent。

私人助理负责：

```text
普通聊天
产品说明
功能推荐
默认兜底
创建提醒
创建求助任务
查找求助任务
删除自己的求助任务
推荐专业 Agent
用户确认后创建专业 Agent 会话并返回前端跳转动作
```

私人助理不直接替专业 Agent 回答专业问题。遇到专业问题时，应完成：

```text
识别适合的专业 Agent
询问/确认是否跳转
创建专业 Agent 会话
构造 handoff_context
保存交接记录
返回 navigation_action 给前端
```

---

## 6. 专业 Agent 边界

专业 Agent 是用户可直接选择的独立入口，不是私人助理的普通 tool。

至少包含：

```text
教学科石老师 Agent
保研学长阿泽 Agent
理科学霸小林 Agent
生活辅导员友老师 Agent
```

专业 Agent 应具备独立会话、专业人设、RAG 检索、来源引用预留、报告/PDF 生成预留能力。

---

## 7. 社区子代理边界

`community_agent` 不是直接操作社区数据库的工具，而是一个小型业务子代理或 LangGraph 子图。

MVP+ 阶段聚焦三类求助任务能力：

```text
创建求助任务
删除自己的求助任务
查找求助任务
```

创建与删除必须走确认流程。
查找可以直接返回结果。
所有真实社区操作必须通过：

```text
community_service_adapter
```

前期可以使用 mock community adapter 支撑开发验证，后续替换为本项目真实社区服务接口。

---

## 8. 必须优先实现的 Graph

至少实现：

```text
assistant_graph
community_agent_subgraph
professional_agent_graph
safety_graph
```

推荐增加：

```text
reminder_graph 或 reminder_flow
```

Graph 需要体现：

```text
State
条件边
pending_state
用户确认
工具调用
错误处理
日志记录
```

不要只写普通函数冒充 Graph。

---

## 9. 自我验证要求

每完成一个阶段，必须主动运行可行的验证命令，并根据错误修复。

优先验证：

```text
python -m compileall app
pytest
ruff check .
docker compose config
FastAPI TestClient 测试
Swagger 是否能启动
```

如果某些命令因为环境缺失无法运行，必须说明原因，并提供替代验证方法。

---

## 10. 工作方式

不要每一步都问用户。

只有在以下情况才提问：

```text
需求存在多个会影响产品逻辑的解释
外部接口字段无法合理假设
安全边界不明确
会造成不可逆的数据操作
需要用户提供真实 API Key 或真实外部服务地址
```

如果不是阻塞问题，请做合理假设并写入：

```text
docs/assumptions.md
```

---

## 11. 旧项目处理

如果存在旧项目目录或旧代码，必须先审计再复用。

不要盲目全删，不要盲目全量重写。

流程：

```text
读取旧项目结构
识别可复用模块
识别跑偏模块
给出迁移计划
再实施修改
```

旧项目路径参考：

```text
D:\strive\ssstrive\BJTUOS\campus-agent-service
```

---

## 12. 输出要求

修改完成后必须输出：

```text
修改总览
关键文件清单
已实现功能
未实现/预留功能
运行命令
测试命令
Swagger 测试方法
下一步建议
```


