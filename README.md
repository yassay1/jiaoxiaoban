# 交小伴 Campus Agent Service

面向高校场景的校园生活智能体平台 — Agent 后端服务层。

交小伴不是普通聊天机器人，而是围绕**私人助理调度 + 专业 Agent 咨询 + 社区求助任务工作流**的完整校园智能体系统。

## 架构概览

```
Frontend (React)
  ↓
FastAPI API Layer
  ↓
Assistant Orchestrator Graph (私人助理总控)
  ↓
├── Direct Chat / Platform QA
├── Professional Agent Sessions (4 professional agents)
└── Community Help-Task Workflow (create/search/delete)
  ↓
Service Layer
├── LLM Service (OpenAI-compatible)
├── RAG Service (pgvector + OpenAI embeddings)
├── Long-term Memory (PostgreSQL)
├── Community Adapter (mock/local/real)
└── Run & Tool Call Logs
  ↓
PostgreSQL + pgvector + Redis
```

### 核心设计原则

**LLM-driven Agent, API-constrained Execution** — 大模型驱动决策，接口约束执行。

## 项目结构

```
├── app/
│   ├── agents/          # Agent runner and profile definitions
│   ├── api/             # FastAPI routes (assistant, agents, community, rag, memory, etc.)
│   ├── chains/          # LLM prompt chains (planner, safety, extraction, RAG answer)
│   ├── config/          # Settings, knowledge domains
│   ├── data_processing/ # Polars-based document cleaning and import
│   ├── db/              # SQLAlchemy models, session, checkpointer, seed data
│   ├── graphs/          # LangGraph state graphs (assistant, professional, community, safety)
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic (rag, memory, community, handoff, llm)
│   └── utils/           # Shared utilities (JSON parsing, etc.)
├── frontend/            # React frontend
├── scripts/             # Demo seeding, database init, and verification scripts
├── tests/               # Test suite (141+ tests)
├── docs/
│   ├── architecture/    # ARCHITECTURE.md, API contract, product flow
│   ├── development/     # Developer guide, assumptions, dev notes
│   ├── planning/        # Task plans, findings, progress tracking
│   ├── reports/         # Project audit, evaluation reports
│   └── history/         # Historical implementation plans and summaries
├── docker-compose.yml   # Local development stack
├── Dockerfile           # Production container
├── pyproject.toml       # Python project config
├── .env.example         # Environment template
├── CLAUDE.md            # AI agent behavioral guidelines
└── AGENTS.md            # Project architecture decisions
```

## API 端点

### 私人助理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/assistant/chat` | 私人助理聊天（支持 interrupt 确认流程） |
| POST | `/api/assistant/resume` | 恢复 interrupt 暂停的会话 |

### 专业 Agent
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agents/chat` | 专业 Agent 聊天 |
| POST | `/api/agents/sessions` | 创建专业 Agent 会话 |
| POST | `/api/agents/{agent_id}/chat` | 前端友好 Agent 聊天入口 |

### 社区帖子
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/posts` | 帖子列表 / 创建帖子 |
| GET/DELETE | `/api/posts/{id}` | 帖子详情 / 删除 |
| GET | `/api/posts/tasks` | 任务大厅 |
| GET | `/api/posts/mine` | 我的帖子 |
| GET | `/api/posts/mine/tasks` | 我的任务 |
| GET | `/api/posts/mine/participated` | 我的参与 |
| POST | `/api/posts/{id}/accept` | 接单 |
| POST | `/api/posts/{id}/cancel` | 取消任务 |
| POST | `/api/posts/{id}/complete` | 完成任务 |
| POST | `/api/posts/{id}/like` | 点赞/取消点赞 |
| POST | `/api/posts/{id}/favorite` | 收藏/取消收藏 |
| GET/POST | `/api/posts/{id}/comments` | 评论列表 / 创建评论 |
| DELETE | `/api/posts/{id}/comments/{cid}` | 删除评论 |
| POST | `/api/posts/{id}/report` | 举报帖子 |
| GET | `/api/reports` | 举报列表 |
| POST | `/api/reports/{id}/resolve` | 处理举报 |
| PATCH | `/api/posts/{id}/moderation` | 审核帖子 |

### RAG 知识库
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rag/search` | 知识检索 |
| POST | `/api/rag/import` | 导入知识文档 |
| POST | `/api/rag/import-batch` | 批量导入 |
| POST | `/api/rag/seed` | 导入种子知识 |
| GET | `/api/rag/docs` | 文档列表 |
| GET | `/api/rag/stats` | 领域统计 |

### 记忆系统
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/memory/{user_id}` | 查看用户长期记忆 |
| POST | `/api/memory/` | 手动创建记忆 |
| DELETE | `/api/memory/{memory_id}` | 删除记忆 |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/agent-runs/{run_id}` | Agent 运行日志 |

## 四个专业 Agent

| Agent | 前端 ID | 领域 | 知识库 |
|-------|---------|------|--------|
| 教学科石老师 | `academic-teacher` | 教务规则、选课、考试、培养方案 | teaching_agent |
| 保研学长阿泽 | `postgraduate-agent` | 保研规划、科研竞赛、导师联系 | postgraduate_agent |
| 理科学霸小林 | `science-tutor` | 高数、线代、大物、编程学习 | science_agent |
| 生活辅导员友老师 | `life-teacher` | 宿舍、食堂、校医院、生活服务 | life_agent |

## 快速启动

### 前置条件

- Python 3.11+
- PostgreSQL 16+ (with pgvector extension)
- Node.js 18+ (for frontend)

### 1. 配置环境

```bash
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY、LLM_API_BASE、LLM_MODEL_NAME
```

### 2. 启动基础设施

```bash
docker compose up -d postgres redis
```

### 3. 安装依赖并启动后端

```bash
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 导入种子数据和知识库

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
- 前端：http://localhost:5173/
- Swagger 文档：http://localhost:8000/docs

## 一键启动（Docker Compose）

```bash
cp .env.example .env
# Edit .env with your LLM config

docker compose up -d
# Swagger: http://localhost:8000/docs
```

## 验证

```bash
# 编译检查
python -m compileall app

# 运行所有测试
pytest -q

# 关键路径验收
python scripts/verify_key_paths.py

# 前端构建检查
cd frontend && npm run build
```

## 开发阶段

| 阶段 | 状态 | 内容 |
|------|------|------|
| Phase 1 | ✅ | Agent 架构稳定（Planner、专业 Agent 双入口、社区 Workflow、确认机制、架构测试） |
| Phase 2 | ✅ | 社区系统补齐（帖子、评论、点赞、收藏、任务大厅、我的任务、举报审核） |
| Phase 3 | ✅ | 前端完整体验（私人助理、专业 Agent、社区、任务大厅、AI 发帖、用户中心） |
| Phase 4 | ✅ | RAG 与数据能力（分域知识库、智能分段、来源引用、防编造、长期记忆） |
| Phase 5 | ✅ | 产品化与交付（权限依赖、Docker Compose、验收脚本、演示数据、README） |

## 技术栈

- **Backend**: Python 3.11+, FastAPI, LangGraph, LangChain
- **Database**: PostgreSQL 16 + pgvector (vector search)
- **Cache**: Redis (pending states, rate limiting)
- **LLM**: OpenAI-compatible API (ZhiPu GLM-4-Flash or GPT-4o-mini)
- **Embeddings**: text-embedding-3-small (via OpenAI API)
- **Frontend**: React 18+, Vite, TypeScript
- **Testing**: pytest, pytest-asyncio
- **Data**: Polars (document cleaning), SQLAlchemy 2.0 (async ORM)

## 注意事项

1. **用户身份**: MVP 阶段通过 `external_user_id` 参数或 `X-User-Id` header 传递。生产环境需接入真实认证网关。
2. **社区服务模式**: 支持 `mock`（纯内存假数据）、`local`（本地 DB）、`real`（外部社区服务）三种模式，通过 `COMMUNITY_SERVICE_MODE` 环境变量控制。
3. **LLM 依赖**: 所有 Agent 智能判断需要真实 LLM 配置。未配置时返回明确错误而非假结果。
4. **确认机制**: 发布、删除等用户可见操作必须经过 interrupt 确认流程，不可绕过。
5. **Reminder Agent**: 不作为当前主线开发目标，现有代码保留但不扩展。
