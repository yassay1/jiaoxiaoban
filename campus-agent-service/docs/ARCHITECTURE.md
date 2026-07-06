# 交小伴项目架构说明

## 1. 最终项目定位

交小伴是一个面向高校场景的校园生活智能体平台。

它不是单纯的 AI 聊天机器人，也不是普通校园墙，而是：

```text
校园社区入口
  + 私人助理调度
  + 专业 Agent 咨询
  + 社区求助任务流程
  + RAG / 记忆 / 确认 / 运行日志
```

对外表达：

> 交小伴是一个面向高校学生的校园生活智能体平台，围绕学习、教务、保研、生活服务和校园互助等场景，提供 AI 辅助咨询、社区求助任务和智能化校园服务入口。

技术表达：

> 本项目是校园 Agent Service 中台，以 FastAPI 提供统一后端接口，以 LangGraph 编排多智能体流程，以 PostgreSQL/pgvector/Redis 支撑会话、记忆、RAG、运行日志和状态恢复。

## 2. 核心架构结论

本项目采用混合式多智能体架构：

```text
Custom Workflow 总骨架
  + Router 意图分发
  + Professional Agent Handoff
  + Community Task Workflow
```

不要设计成多个 Agent 平铺互聊。

正确关系是：

```text
私人助理 = 总控入口 / 意图路由 / 能力调度
专业 Agent = 垂直咨询角色 / 多轮对话
社区求助任务 Agent = 业务流程子图 / 操作型工作流
```

## 3. 总体分层

```text
Frontend
  ↓
API Adapter Layer
  ↓
FastAPI Router Layer
  ↓
Agent Orchestration Layer
  ↓
Capability Graph Layer
  ↓
Service Layer
  ↓
Data and External Service Layer
```

### 3.1 Frontend

前端可以有以下入口：

- 私人助理入口。
- 专业 Agent 页面。
- 社区帖子页面。
- AI 辅助发帖入口。
- 我的任务 / 我的记录页面。

### 3.2 API Adapter Layer

前端可使用友好的 agent id：

- `personal-assistant`
- `academic-teacher`
- `postgraduate-agent`
- `science-tutor`
- `life-teacher`

后端映射为：

- `personal-assistant` → `assistant_graph`
- `academic-teacher` → `teaching_agent`
- `postgraduate-agent` → `postgraduate_agent`
- `science-tutor` → `science_agent`
- `life-teacher` → `life_agent`

### 3.3 FastAPI Router Layer

主要接口方向：

- 私人助理聊天接口。
- 专业 Agent 聊天接口。
- 前端 Agent 适配接口。
- 社区帖子接口。
- 社区任务 Agent 接口。
- RAG 查询接口。
- Agent run 日志接口。

### 3.4 Agent Orchestration Layer

主要图：

```text
assistant_graph
professional_agent_graph
community_agent_subgraph
community_task_graph
safety_graph
```

`reminder_graph` 不作为当前主要架构目标。

## 4. 私人助理架构

私人助理是总控型 Agent。

它不是普通聊天专家，而是校园智能体平台的入口层和调度层。

### 4.1 私人助理职责

```text
用户输入
  ↓
加载上下文
  ↓
意图识别
  ↓
路由判断
  ├── direct_chat
  ├── professional_agent_handoff
  ├── community_task_workflow
  └── clarification
```

### 4.2 推荐状态结构

建议让 planner 输出更清晰的结构：

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

### 4.3 私人助理不应该做的事

- 不要承担所有专业问题的最终回答。
- 不要把社区任务发布逻辑塞进普通聊天回复。
- 不要绕过确认直接执行创建/删除任务。
- 不要为了兜底规则把架构复杂化。

私人助理的第一目标是让能力分发清晰，而不是写大量规则兜底。

## 5. 专业 Agent 架构

专业 Agent 是垂直咨询型 Agent。

### 5.1 支持直接进入

用户可以直接进入专业 Agent 页面，例如直接找“保研学长阿泽”。

这条路径是产品上的明确入口，不需要私人助理每次先转发。

```text
用户
  ↓
专业 Agent 页面
  ↓
professional_agent_graph
  ↓
RAG + LLM Answer
```

### 5.2 支持私人助理推荐进入

用户也可以从私人助理进入专业 Agent。

```text
用户问私人助理
  ↓
assistant_planner 判断为专业咨询
  ↓
生成推荐 / handoff action
  ↓
创建 professional_agent_session
  ↓
进入对应专业 Agent 会话
```

### 5.3 不采用 B 作为第一阶段主线

之前选项里的 B 是：

```text
私人助理把专业 Agent 当工具调用
  ↓
专业 Agent 返回结果
  ↓
私人助理统一总结回复用户
```

这属于 Supervisor / Subagents-as-tools 模式。

这种模式适合后期处理复杂问题，比如同时问保研、学习规划和生活时间管理时，由私人助理并行调用多个专业 Agent，再综合回复。

但第一阶段不建议把 B 当主线，因为你的专业 Agent 更适合直接和用户多轮对话。

### 5.4 专业 Agent 图结构

```text
load_session_or_context
  ↓
select_agent_profile
  ↓
retrieve_domain_knowledge
  ↓
llm_answer
  ↓
boundary_reminder
  ↓
save_message
```

### 5.5 四个专业 Agent

```text
teaching_agent
  教务规则、培养方案、选课、考试、办事流程

postgraduate_agent
  保研规划、竞赛科研、简历、时间线、经验建议

science_agent
  高数、线代、大物、编程、课程学习辅导

life_agent
  宿舍、食堂、校医院、后勤、校园生活服务
```

## 6. 社区求助任务 Agent 架构

社区求助任务 Agent 是任务型 Workflow，不是长期聊天 Agent。

它适合被私人助理调用，也可以被社区页面中的 AI 发帖功能调用。

### 6.1 第一阶段功能

```text
创建求助任务
搜索求助任务
删除自己的求助任务
```

暂不扩展：

- 修改任务。
- 接单/认领。
- 完成确认。
- 积分奖励。
- 举报审核。

### 6.2 创建任务流程

```text
用户描述需求
  ↓
extract_task_fields
  ↓
check_missing_fields
  ├── ask_missing_fields
  └── generate_task_draft
        ↓
     safety_check
        ↓
     user_confirm
        ↓
     publish_task
        ↓
     return_result
```

### 6.3 搜索任务流程

```text
用户搜索需求
  ↓
rewrite_or_extract_search_query
  ↓
search_help_tasks
  ↓
rank_and_format_results
  ↓
return_result
```

### 6.4 删除任务流程

```text
用户请求删除
  ↓
list_my_tasks / search_my_tasks
  ↓
match_target_task
  ↓
user_confirm_delete
  ↓
delete_help_task
  ↓
return_result
```

## 7. RAG 架构

第一阶段 RAG 重点服务专业 Agent。

推荐优先级：

```text
P0: 专业 Agent RAG
P1: 私人助理平台说明 RAG
P2: 社区任务政策/安全 RAG
```

不要一开始把 RAG 做成全局万能知识库。不同专业 Agent 应该有相对独立的知识范围。

推荐知识划分：

```text
agent_name = teaching_agent
agent_name = postgraduate_agent
agent_name = science_agent
agent_name = life_agent
agent_name = platform
```

## 8. 架构演进路线

### 阶段一：定架构

目标：

- 明确项目定位。
- 明确私人助理、专业 Agent、社区任务 Agent 的边界。
- 清理提醒 Agent 的优先级。
- 写好 Codex 指令文件。

### 阶段二：改 Planner

目标：

- 将 assistant planner 输出从简单 route 升级为 intent + execution_mode + target_agent。
- 减少规则兜底堆积。
- 让路由结果可解释、可测试。

### 阶段三：改专业 Agent

目标：

- 保证专业 Agent 支持直接进入。
- 保证私人助理可 handoff 到专业 Agent。
- 补充 session 状态和 handoff 上下文。

### 阶段四：改社区任务流程

目标：

- 打通 assistant_graph 到 community_agent_subgraph。
- 创建、搜索、删除流程清晰可测。
- 所有发布/删除操作都有确认。

### 阶段五：增强 RAG

目标：

- 专业 Agent 的知识库分域。
- 检索结果可解释。
- 没有知识时不编造。
- 支持后续导入学校政策、培养方案、办事流程等资料。

## 9. 最终一句话架构

本项目采用“私人助理总控 + 专业 Agent 咨询 + 社区任务工作流”的混合多智能体架构。私人助理负责意图识别和能力调度，专业 Agent 支持直接进入和 handoff 进入，社区求助任务 Agent 作为任务型 Workflow 完成创建、搜索和删除操作，RAG、记忆、确认和运行日志作为底层支撑。
