# 产品流程说明 — 交小伴 Agent Service v1.0

## 一、私人助理流程

```
用户发送消息
    │
    ▼
私人助理接收 (POST /api/assistant/chat)
    │
    ▼
LLM 意图识别 (intent_router_chain)
    │
    ├── 直接回答 ────────→ 返回回答
    │
    ├── 推荐 Agent ──────→ 返回推荐 + 建议转接
    │
    ├── 创建任务草稿 ────→ 进入任务草稿流程
    │
    ├── 追问澄清 ────────→ 返回追问问题
    │
    └── 安全检查 ────────→ 返回安全提醒
```

## 二、专业 Agent 流程

```
用户选择 Agent (POST /api/agents/chat)
    │
    ▼
选择 Agent Profile (system_prompt + boundary)
    │
    ▼
RAG 知识库检索（如有相关知识）
    │
    ▼
LLM 生成回答（基于 system_prompt + RAG 结果）
    │
    ▼
附加边界提醒 (boundary_reminder)
    │
    ▼
返回结构化回答
```

## 三、帖子转任务流程

```
帖子数据输入
    │
    ▼
帖子理解 (post_analysis_chain)
    │  - 判断帖子类型
    │  - 提取标签
    │  - 生成摘要
    │
    ▼
互助意图识别
    │  - has_help_intent?
    │  - 是 → 继续
    │  - 否 → 返回不建议转任务
    │
    ▼
任务草稿生成 (task_draft_chain)
    │  - 生成标题
    │  - 生成描述
    │  - 标注类型和标签
    │  - 识别缺失信息
    │
    ▼
安全检查 (safety_check_chain)
    │  - risk_level?
    │  - blocked? → 阻止
    │  - high risk? → 需要确认
    │
    ▼
用户确认 (POST /api/confirmations)
    │  - 创建确认记录
    │  - 等待用户 approve/reject
    │
    ▼
调用社区创建任务 API
    │  - CommunityClient.create_task()
    │  - 保存 created_task_id
    │
    ▼
返回任务结果
```

## 四、安全检查流程

```
内容输入 (POST /api/safety/check)
    │
    ▼
LLM 安全语义判断
    │  - 分析违规风险
    │  - 判断风险等级
    │
    ▼
风险等级决策
    ├── low: 直接放行
    ├── medium: 需要用户确认
    ├── high: 需要审核 + 确认
    └── critical: 阻止操作
    │
    ▼
记录安全检查结果 (agent_safety_checks 表)
```

## 五、用户确认流程

```
系统发起确认请求 (POST /api/confirmations)
    │  - 描述将要执行的操作
    │  - 标注风险等级
    │  - 设置过期时间
    │
    ▼
前端展示确认界面给用户
    │
    ▼
用户做出决定 (POST /api/confirmations/resolve)
    ├── approved: true → 继续执行操作
    └── approved: false → 取消操作
    │
    ▼
记录确认结果 (confirmation_records 表)
```

## 六、RAG 知识检索流程

```
用户查询 (POST /api/rag/search)
    │
    ▼
查询向量化
    │
    ▼
向量数据库检索 top_k
    │
    ▼
LLM 基于检索结果生成回答
    │  - 优先基于知识库
    │  - 不知道就说不知道
    │  - 不编造信息
    │
    ▼
返回检索结果 + AI 回答
```

