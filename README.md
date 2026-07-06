# 交小伴 — 校园生活智能体平台

面向高校场景的 AI 智能体平台，提供**私人助理调度 + 专业 Agent 咨询 + 社区求助任务工作流**的完整校园服务体验。

## 架构

```
React Frontend (Vite + TypeScript)
  ↓
FastAPI API Layer (/api/*)
  ↓
LangGraph Agent Orchestration
  ├── assistant_graph         私人助理总控（意图识别 → 路由分发）
  ├── professional_agent_graph  专业 Agent 咨询（4 位角色）
  ├── community_agent_subgraph  社区求助任务工作流（创建/搜索/删除）
  ├── community_task_graph      社区任务状态管理
  └── safety_graph             内容安全审核
  ↓
Service Layer
  ├── LLM Service (OpenAI-compatible)
  ├── RAG Service (pgvector + OpenAI embeddings, 智能分段)
  ├── Long-term Memory (PostgreSQL, 自动提取)
  ├── Community Adapter (mock | local | real 三种模式)
  └── Agent Run & Tool Call 日志
  ↓
PostgreSQL 16 + pgvector + Redis
```

### 核心设计原则

**LLM-driven Agent, API-constrained Execution** — 大模型驱动决策，接口约束执行。

- LLM 负责意图理解、路由规划、字段提取、内容生成
- 程序负责 Schema 校验、权限边界、用户确认、数据库记录、错误处理
- 所有创建/删除操作不可绕过确认流程

## 项目结构

```
jiaoxiaoban/
├── README.md                    # 本文件
└── campus-agent-service/        # 唯一项目目录
    ├── app/
    │   ├── agents/              # Agent 运行器与配置（assistant / community_admin / professional）
    │   ├── api/                 # FastAPI 路由层（14 个路由模块）
    │   │   ├── assistant.py     # 私人助理聊天 + resume（支持 LangGraph interrupt）
    │   │   ├── agents.py        # 专业 Agent 聊天
    │   │   ├── frontend_agents.py  # 前端友好的 Agent ID 适配层
    │   │   ├── community.py     # 社区帖子 CRUD（帖子/评论/点赞/收藏/举报/审核）
    │   │   ├── community_agent.py  # 社区 Agent 入口
    │   │   ├── rag.py           # 知识库检索与导入
    │   │   ├── memory.py        # 长期用户记忆
    │   │   ├── agent_runs.py    # Agent 运行日志查询
    │   │   ├── confirmations.py # 确认记录管理
    │   │   ├── safety.py        # 安全审核
    │   │   ├── reminders.py     # 提醒（保留，非主线）
    │   │   └── health.py        # 健康检查
    │   ├── chains/              # LLM Prompt Chain（planner / safety / extraction / RAG / chat）
    │   ├── config/              # Settings（pydantic-settings）+ 知识领域定义
    │   ├── data_processing/     # Polars 文档清洗与知识导入
    │   ├── db/                  # SQLAlchemy 2.0 异步模型、Session、Checkpointer、种子数据
    │   ├── graphs/              # LangGraph StateGraph 定义
    │   │   ├── assistant_graph.py          # 私人助理主图（create_run → load_memory → planner → route → confirm → execute）
    │   │   ├── professional_agent_graph.py  # 专业 Agent 图（load → select_profile → RAG → answer → boundary_reminder）
    │   │   ├── community_agent_subgraph.py  # 社区任务子图（extract → draft → confirm → publish/delete/search）
    │   │   ├── community_task_graph.py      # 社区任务状态管理
    │   │   └── safety_graph.py             # 安全审核图
    │   ├── schemas/             # Pydantic 请求/响应模型
    │   ├── services/            # 业务逻辑层
    │   │   ├── llm_service.py              # LLM 调用封装（OpenAI-compatible）
    │   │   ├── rag_service.py              # pgvector 向量检索 + 智能分块
    │   │   ├── long_term_memory_service.py # 长期记忆自动提取与检索
    │   │   ├── community_service_adapter.py # 社区适配器（mock/local/real 统一接口）
    │   │   ├── community_post_service.py   # 社区帖子业务逻辑
    │   │   ├── community_client.py         # 外部社区 HTTP 客户端
    │   │   ├── mock_community_adapter.py   # 内存模拟社区（开发用）
    │   │   ├── handoff_context_service.py  # Agent 交接上下文构建
    │   │   ├── conversation_service.py     # 会话管理
    │   │   ├── message_service.py          # 消息持久化
    │   │   ├── agent_run_service.py        # Agent 运行日志
    │   │   ├── memory_service.py           # 短期记忆
    │   │   ├── confirmation_service.py     # 确认机制
    │   │   ├── pending_state_service.py    # Redis 临时状态
    │   │   ├── tool_call_service.py        # Tool Call 日志
    │   │   ├── frontend_agent_adapter_service.py  # 前端 Agent ID 映射
    │   │   ├── demo_fixture_service.py     # 演示数据
    │   │   └── safety_service.py           # 安全审核
    │   └── utils/               # JSON 解析等工具
    ├── frontend/                # React 19 + Vite 8 + TypeScript 6
    │   └── src/App.tsx          # 单文件全功能前端（8 个页面）
    ├── tests/                   # 测试套件（141+ 用例，pytest-asyncio）
    ├── scripts/                 # 演示数据种子、验收脚本、后端启动
    ├── docs/                    # 架构文档、开发指南、实施计划
    ├── docker-compose.yml       # 本地开发栈（postgres + redis + app）
    ├── Dockerfile               # 生产容器（python:3.11-slim）
    ├── pyproject.toml           # Python 项目配置
    ├── .env.example             # 环境变量模板
    ├── CLAUDE.md                # AI 代理行为规范
    └── AGENTS.md                # 项目架构决策文档
```

## 四个专业 Agent

| Agent | 前端 ID | 领域 | 边界提醒 |
|-------|---------|------|----------|
| 教学科石老师 | `academic-teacher` | 教务规则、选课、考试、培养方案 | 以学校官方通知为准 |
| 保研学长阿泽 | `postgraduate-agent` | 保研规划、科研竞赛、导师联系 | 个人经验分享，政策以学院为准 |
| 理科学霸小林 | `science-tutor` | 高数、线代、大物、编程学习 | 学习思路引导，独立完成作业 |
| 生活辅导员友老师 | `life-teacher` | 宿舍、食堂、校医院、生活服务 | 健康安全问题请联系校医院 |

每个专业 Agent 拥有独立的人设、RAG 知识库范围、边界提醒和推荐问题列表。

## 多智能体架构

### 私人助理（总控入口）

```
用户消息 → 加载上下文(记忆+RAG) → Planner 意图识别
  ├── direct_chat         直接聊天 / 产品问答
  ├── professional_handoff → 确认 → 创建专业 Agent 会话 → 返回前端跳转
  ├── community_workflow  → 社区任务子图（创建/搜索/删除）
  └── clarify             → 追问缺失信息
```

- Planner 输出结构化计划：`intent` + `execution_mode` + `target_agent` + `confidence`
- 专业 Agent 跳转走 interrupt 确认，不可绕过
- 社区任务走子图，创建/删除自带确认流程

### 专业 Agent（垂直咨询）

支持两种进入方式：
1. **直接进入**：用户在前端直接选择专业 Agent 开始对话
2. **Handoff 进入**：私人助理识别意图后推荐并创建会话，携带上下文交接

流程：`load → select_profile → RAG search → LLM answer → boundary_reminder`

### 社区求助任务 Agent（操作型 Workflow）

```
创建任务：extract_fields → ask_missing / generate_draft → confirm_publish → publish
搜索任务：build_query → search → format_results
删除任务：list_my_tasks → match_target → confirm_delete → delete
```

所有写操作均通过 `community_service_adapter` 统一接口，支持三种模式：
- `mock`：纯内存假数据（测试用）
- `local`：本地 CommunityPost 数据库表（集成演示）
- `real`：外部社区 HTTP 服务

## API 端点

### 私人助理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/assistant/chat` | 私人助理聊天（支持 interrupt 暂停） |
| POST | `/api/assistant/resume` | 恢复 interrupt 暂停的会话 |

### 前端 Agent 适配层
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agents/{frontend_id}/chat` | 统一 Agent 聊天入口 |

`frontend_id` 映射：`personal-assistant` → assistant_graph，`academic-teacher` → teaching_agent 等。

### 社区帖子（完整 CRUD）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET / POST | `/api/posts` | 帖子列表 / 创建 |
| GET / DELETE | `/api/posts/{id}` | 详情 / 删除 |
| GET | `/api/posts/tasks` | 任务大厅（支持状态筛选） |
| GET | `/api/posts/mine` | 我的帖子 |
| GET | `/api/posts/mine/tasks` | 我发布的任务 |
| GET | `/api/posts/mine/participated` | 我参与的任务 |
| POST | `/api/posts/{id}/accept` | 接单 |
| POST | `/api/posts/{id}/cancel` | 取消任务 |
| POST | `/api/posts/{id}/complete` | 完成任务 |
| POST | `/api/posts/{id}/like` | 点赞/取消 |
| POST | `/api/posts/{id}/favorite` | 收藏/取消 |
| GET / POST | `/api/posts/{id}/comments` | 评论列表 / 创建 |
| DELETE | `/api/posts/{id}/comments/{cid}` | 删除评论 |
| POST | `/api/posts/{id}/report` | 举报 |
| GET | `/api/reports` | 举报列表 |
| POST | `/api/reports/{id}/resolve` | 处理举报 |
| PATCH | `/api/posts/{id}/moderation` | 审核帖子 |

### RAG 知识库
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rag/search` | 向量检索（pgvector cosine similarity） |
| POST | `/api/rag/import` | 导入知识文档（智能分段） |
| POST | `/api/rag/import-batch` | 批量导入 |
| POST | `/api/rag/seed` | 导入种子知识 |
| GET | `/api/rag/docs` | 文档列表 |
| GET | `/api/rag/stats` | 领域统计 |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/agent-runs` | Agent 运行日志列表 |
| GET | `/api/agent-runs/{run_id}` | 运行详情（含 input/output/error） |
| GET/POST/DELETE | `/api/memory/*` | 用户长期记忆管理 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.11+, FastAPI, Uvicorn |
| Agent 编排 | LangGraph (StateGraph + interrupt + Command resume) |
| LLM 集成 | LangChain + OpenAI-compatible API |
| 数据库 | PostgreSQL 16 + pgvector (向量检索) |
| 缓存 | Redis (临时状态、频率限制) |
| ORM | SQLAlchemy 2.0 (异步 asyncpg) |
| 数据校验 | Pydantic v2 + pydantic-settings |
| 前端 | React 19 + Vite 8 + TypeScript 6 |
| 测试 | pytest + pytest-asyncio (141+ 用例) |
| 数据处理 | Polars (文档清洗) |
| 容器化 | Docker + Docker Compose |

## 快速启动

### 前置条件

- Python 3.11+
- Node.js 18+
- Docker Desktop（或 PostgreSQL 16 + pgvector + Redis 手动安装）

### 1. 配置环境

```bash
cd campus-agent-service
cp .env.example .env
```

编辑 `.env`，填入 LLM 配置（至少三项）：

```env
LLM_API_KEY=your_api_key
LLM_API_BASE=https://api.openai.com/v1   # 或兼容接口
LLM_MODEL_NAME=gpt-4o-mini               # 或其他兼容模型
```

### 2. 启动基础设施

```bash
docker compose up -d postgres redis
```

### 3. 启动后端

```bash
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 导入种子数据

```bash
python scripts/seed_demo_data.py
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：
- **前端**：http://localhost:5173/
- **Swagger 文档**：http://localhost:8000/docs
- **ReDoc**：http://localhost:8000/redoc

### Docker Compose 一键启动

```bash
cp .env.example .env
# 编辑 .env 填入 LLM 配置
docker compose up -d
```

## 验证

```bash
# 编译检查
python -m compileall app

# 运行所有测试
pytest -q

# 关键路径验收
python scripts/verify_key_paths.py

# 架构契约测试
python scripts/verify_architecture.py

# 前端构建检查
cd frontend && npm run build
```

## 开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | Agent 架构稳定（Planner、双入口、确认机制、架构测试） | ✅ |
| Phase 2 | 社区系统补齐（帖子、评论、点赞、收藏、任务大厅、举报审核） | ✅ |
| Phase 3 | 前端完整体验（私人助理、专业 Agent、社区、任务大厅、AI 发帖、用户中心） | ✅ |
| Phase 4 | RAG 与数据能力（分域知识库、智能分段、来源引用、防编造、长期记忆） | ✅ |
| Phase 5 | 产品化与交付（权限依赖、Docker Compose、验收脚本、演示数据、README） | ✅ |

## 设计决策

1. **用户身份**：MVP 阶段通过 `external_user_id` 参数传递。生产需接入真实认证网关。
2. **LLM 依赖**：未配置 LLM 时 Agent 接口返回明确错误，不伪造结果。健康检查和 mock adapter 不受影响。
3. **确认机制**：发布、删除等用户可见操作必须经过 LangGraph `interrupt` + `Command(resume)` 确认流程。
4. **社区模式**：通过 `COMMUNITY_SERVICE_MODE` 环境变量在 mock / local / real 间切换。
5. **前端 Agent ID**：`personal-assistant` / `academic-teacher` / `postgraduate-agent` / `science-tutor` / `life-teacher`，由 `frontend_agent_adapter_service` 映射为后端内部名称。
6. **Reminder Agent**：不作为当前主线，代码保留但不扩展。

## 注意事项

- `.env` 文件包含真实 API Key，已加入 `.gitignore`，不会被提交
- `.pytest_cache/`、`tmp_screenshots/`、`frontend/node_modules/` 均被 `.gitignore` 排除
- 项目处于 MVP 完成阶段，已具备完整的端到端可运行能力
