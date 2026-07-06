# 开发者上手指南 — campus-agent-service

## 一、代码全景地图（从哪里看起）

```
用户请求
  → app/main.py              ← FastAPI 入口，注册路由
  → app/api/*.py              ← 路由层：接收请求、参数校验、调用 Agent
  → app/agents/*.py           ← Agent 层：调用 Graph 执行智能流程
  → app/graphs/*.py           ← 流程编排层：LangGraph 状态机，控制节点顺序
  → app/chains/*.py           ← 智能决策层：每个 Chain 是一个 LLM 调用任务
  → app/services/llm_service.py ← LLM 调用底层封装
  → app/services/*.py         ← 横向服务（RAG、安全、缓存、社区 client）
  → app/db/models.py          ← 12 张表，日志和状态落库
  → app/schemas/*.py          ← 输入输出校验（Pydantic）
```

**看代码的建议路径**：
1. `app/main.py` → 了解有哪些路由
2. `app/api/assistant.py` → 看一个最简单的 API 怎么写的
3. `app/agents/assistant_agent.py` → 看 Agent 怎么调用 Graph
4. `app/graphs/assistant_graph.py` → 看 LangGraph 的节点和边怎么定义
5. `app/chains/intent_router_chain.py` → 看 LLM 调用具体怎么写
6. `app/services/llm_service.py` → 看底层 LLM 封装

---

## 二、核心架构决策（为什么这么写）

### 原则：LLM-driven Agent, API-constrained Execution

```
┌─────────────────────────────────────────┐
│  LLM 负责决策（chains/ + graphs/）        │
│  - 意图识别、Agent 推荐、帖子分析          │
│  - 任务草稿生成、安全检查                  │
│  - 不会被 if/else 关键词规则替代           │
├─────────────────────────────────────────┤
│  后端负责约束（api/ + schemas/ + db/）     │
│  - Pydantic 参数校验                      │
│  - 数据库状态记录                          │
│  - 用户确认机制                            │
│  - Tool 调用日志                           │
│  - 外部接口失败处理                         │
└─────────────────────────────────────────┘
```

### 数据流：从 HTTP 到 LLM 再回来

```
POST /api/assistant/chat {"message": "我高数不会"}
  → assistant.py: 用 ChatRequest schema 校验
  → assistant_agent.py: run_assistant()
  → assistant_graph.py: assistant_graph.ainvoke(initial_state)
     → node_understand_intent: 调用 intent_router_chain
        → llm_service.llm_structured_output()   ← 真正调用 LLM
        → 返回 {"intent": "recommend_agent", ...}
     → route_by_intent: 根据 intent 选择下一个节点
     → node_recommend_agent: 生成推荐响应
  → 返回 ChatResponse schema 格式的 JSON
```

---

## 三、如何扩展和修改

### 场景 1：添加新的专业 Agent

假设要加一个"就业指导张老师" Agent，需要改 3 个地方：

**① `app/graphs/professional_agent_graph.py`** — 添加 Agent Profile：
```python
AGENT_PROFILES["career_agent"] = {
    "system_prompt": "你是就业指导张老师，负责...",
    "boundary": "以上为经验分享，具体请咨询学校就业指导中心。",
}
```
不需要新建 Graph，所有专业 Agent 共用一个 `professional_agent_graph`，靠 `agent_name` 参数切换 Profile。

**② `app/agents/`** — 新建 `career_agent.py`（复制 `teaching_agent.py`，改 agent_name 即可）

**③ `app/api/agents.py`** — 在 `_AGENT_RUNNER` 字典中注册：
```python
from app.agents.career_agent import run_career_agent
_AGENT_RUNNER["career_agent"] = run_career_agent
```

### 场景 2：修改 Agent 的回复风格

直接改 `AGENT_PROFILES` 字典中的 `system_prompt` 字段，不需要动其他代码。例如让石老师更亲切一点：
```python
"teaching_agent": {
    "system_prompt": "你是教学科石老师，语气亲切但严谨...",
    "boundary": "...",
}
```

### 场景 3：添加新的 API 接口

1. `app/schemas/` 中新建 Schema 文件（Request + Response）
2. `app/api/` 中新建路由文件
3. `app/main.py` 中 `app.include_router()`

### 场景 4：接入真实向量数据库

当前 RAG 返回占位结果。要接入真实向量数据库（如 pgvector），改：
- `app/services/rag_service.py` 的 `search_knowledge()` 函数
- `app/data_processing/import_knowledge_docs.py` 添加 embedding 生成和写入

---

## 四、关键文件速查

| 文件 | 作用 | 什么时候改 |
|------|------|-----------|
| `.env.example` | 环境变量模板 | 新增配置项 |
| `app/config/settings.py` | 配置类 | 新增配置项 |
| `app/main.py` | 路由注册 | 新增 API 模块 |
| `app/db/models.py` | 12 张表定义 | 新增字段或表 |
| `app/schemas/*.py` | 接口输入输出 | 修改接口参数 |
| `app/api/*.py` | 接口实现 | 修改接口逻辑 |
| `app/agents/*.py` | Agent 入口 | 新增 Agent |
| `app/graphs/*.py` | 流程编排 | 修改决策流 |
| `app/chains/*.py` | LLM 提示词 | 调整 AI 行为 |
| `app/services/llm_service.py` | LLM 调用 | 换模型/提供商 |
| `app/services/community_client.py` | 社区 API | 对接真实社区 |
| `app/services/memory_service.py` | Redis 缓存 | 会话/缓存逻辑 |

---

## 五、本地开发命令

```bash
# 安装依赖
pip install -e ".[dev]"

# 启动服务（需要先配好 .env）
uvicorn app.main:app --reload --port 8000

# Swagger 文档
open http://localhost:8000/docs

# 只测健康检查（不需要 LLM）
curl http://localhost:8000/api/health

# 用 Docker 启动全家桶（API + PostgreSQL + Redis）
docker-compose up -d
docker-compose logs -f api
```

---

## 六、未配置 LLM 时的行为

所有涉及 LLM 的接口被调用时会返回：
```json
{
  "content": "当前未配置真实 LLM 参数，无法执行 Agent 智能判断。请在 .env 中配置 LLM_API_KEY、LLM_API_BASE 和 LLM_MODEL_NAME。"
}
```

**不影响**的接口：
- `GET /api/health` — 永远可用
- `GET /api/agent-runs/{run_id}` — 查运行记录

---

## 七、社区服务接入准备

1. 社区服务启动后，配置 `.env` 中的 `COMMUNITY_SERVICE_BASE_URL`
2. Agent Service 调用社区 API 的记录会存在 `external_api_calls` 表
3. 社区服务与 Agent Service 通过 HTTP API 传参，不走跨模块数据库直连
4. ID 关联约定见社区服务接口文档

---

## 八、常见问题

**Q: 为什么专业 Agent 用一个 graph 而不是每个建一个？**
4 个专业 Agent 的流程完全一样：选 Profile → RAG 检索 → LLM 回答 → 边界提醒。区别只在 system_prompt。共用一个 graph 避免重复代码。

**Q: 帖子分析后一定要转任务吗？**
不一定。`analyze_post` 只做分析，返回 `has_help_intent` 和 `suggested_action`。前端可以决定要不要调 `convert-post-to-task`。

**Q: task_drafts 和社区服务的 help_tasks 什么关系？**
`task_drafts` 是 Agent 生成的草稿（存在我的数据库）。用户确认后通过 CommunityClient 创建正式 `help_tasks`。草稿的 `created_task_id` 存社区服务返回的正式任务 ID。

**Q: Polars 用在哪里？**
三个离线脚本在 `app/data_processing/`，用于：批量导入知识库（CSV/Excel）、清洗文档（去重/过滤）、分析 Agent 运行日志。不在实时 API 中使用。

---

## 九、下一步建议（按优先级排序）

### 第一优先：让 LLM 跑通

当前骨架已就绪，但需要配置真实 LLM 才能验证完整链路。

1. **获取 API Key**：推荐使用 OpenAI 兼容接口（阿里百炼、DeepSeek、智谱等都兼容），成本低适合开发
2. **配置 .env**：
   ```
   LLM_PROVIDER=openai
   LLM_API_KEY=sk-xxxxx
   LLM_API_BASE=https://api.deepseek.com/v1   # 示例
   LLM_MODEL_NAME=deepseek-chat
   ```
3. **验证链路**：启动服务后用 Swagger 逐个测试接口，看 LLM 是否正常返回

### 第二优先：接入数据库

当前为了快速启动，`agent_run_service.py` 用的是内存字典。正式开发需要：

1. **启动 PostgreSQL**（docker-compose 已包含，直接 `docker-compose up -d postgres`）
2. **创建表**：用 Alembic 初始化迁移
   ```bash
   pip install alembic
   alembic init -t async app/db/migrations
   # 配置 alembic.ini 指向 models.Base
   alembic revision --autogenerate -m "init"
   alembic upgrade head
   ```
3. **替换内存存储**：将 `agent_run_service.py` 和 `api/confirmations.py` 中的 `_run_store`、`_confirmations` 字典替换为数据库读写

### 第三优先：完善 RAG 知识库

1. **准备知识文档**：收集教务规则、培养方案、校园地图、保研经验等文本
2. **写 CSV 导入**：
   ```csv
   title,content,agent_name
   "通识选修课要求","通识选修课分为...","teaching_agent"
   ```
3. **运行导入脚本**：`python -m app.data_processing.import_knowledge_docs`
4. **接入向量数据库**：pgvector（已在 docker-compose 中使用 pgvector/pgvector:pg16 镜像）或 FAISS
5. **修改 `rag_service.py`**：将占位返回替换为真实向量检索

### 第四优先：接入社区服务

1. **约定 API 格式**：在本项目社区服务接口文档中明确请求和响应结构
2. **配置 `COMMUNITY_SERVICE_BASE_URL`**
3. **接入 `CommunityClient`**：在社区 API 可用后测试 `create_task()`、`get_user_info()` 等方法
4. **查看 `external_api_calls` 表**：每次调用社区 API 都会记录，方便排查

### 第五优先：完善和打磨

- **数据库模型正式化**：当前 `models.py` 定义了表结构但 API 层用模拟存储，需要打通
- **Redis 实际使用**：当前 `memory_service.py` 写了完整实现，但 API 层还没调用，需要接入会话管理
- **提示词迭代**：各 Chain 的 system_prompt 需要根据实际效果持续调优
- **日志系统**：接入 Python logging，记录 Agent 运行和 Tool 调用
- **异常处理增强**：当前基本骨架已处理 LLM 未配置的情况，但其他异常边界（数据库断开、Redis 超时等）需要补充

### 最小可行验证路径（今天就跑通）

```bash
# 1. 配好 LLM 的 .env
# 2. 启动服务
uvicorn app.main:app --reload

# 3. 浏览器打开 Swagger
open http://localhost:8000/docs

# 4. 测试三个核心接口:
#    - POST /api/health           → 确认服务活着 + LLM 已配置
#    - POST /api/assistant/chat   → 发"你好"，看私人助理回复
#    - POST /api/agents/recommend → 发"我想学高数"，看推荐结果
```


