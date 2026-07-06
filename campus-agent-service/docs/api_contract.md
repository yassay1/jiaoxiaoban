# API Contract — 交小伴 Agent Service v1.0

## 通用说明

- Base URL: `http://localhost:8000`
- Content-Type: `application/json`
- 所有时间字段使用 ISO 8601 格式
- 错误响应格式: `{"error": "错误描述", "detail": "详细信息", "code": "错误码"}`

---

## 1. GET /api/health — 健康检查

**Response 200:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "llm_configured": false
}
```

字段说明:
- `status`: 服务状态，正常为 "ok"
- `llm_configured`: 是否已配置真实 LLM

---

## 2. POST /api/assistant/chat — 私人助理聊天

**Request:**
```json
{
  "message": "我高数作业不会做，有人能帮我吗？",
  "conversation_id": null,
  "external_user_id": "user_123"
}
```

字段说明:
- `message`: 用户消息 (1-4096 字符)
- `conversation_id`: 会话 ID，为空则新建
- `external_user_id`: 本项目用户 ID

**Response 200:**
```json
{
  "conversation_id": "conv_abc123",
  "message_id": "msg_xyz789",
  "role": "assistant",
  "content": "我建议你咨询理科学霸小林，正在为你转接...",
  "agent_name": "science_agent",
  "actions": [{"type": "recommend_agent", "agent_name": "science_agent"}],
  "created_at": "2025-01-15T10:30:00Z"
}
```

错误码:
- 400: 参数校验失败
- 503: LLM 未配置

---

## 3. POST /api/agents/recommend — Agent 推荐

**Request:**
```json
{
  "message": "我想了解一下保研的流程和经验",
  "external_user_id": "user_123"
}
```

**Response 200:**
```json
{
  "recommended_agents": [
    {
      "agent_name": "postgraduate_agent",
      "display_name": "保研学长阿泽",
      "description": "负责保研经验、竞赛经验等",
      "capabilities": []
    }
  ],
  "reason": "用户询问保研相关，推荐保研学长阿泽",
  "conversation_id": null
}
```

---

## 4. POST /api/agents/chat — 专业 Agent 聊天

**Request:**
```json
{
  "agent_name": "teaching_agent",
  "message": "请问培养方案里的通识选修课有什么要求？",
  "conversation_id": null,
  "external_user_id": "user_123"
}
```

**Response 200:**
```json
{
  "conversation_id": "conv_def456",
  "message_id": "msg_ghi789",
  "agent_name": "teaching_agent",
  "role": "assistant",
  "content": "根据培养方案，通识选修课要求...",
  "boundary_reminder": "以上内容基于已有知识库，具体以学校教务处最新通知为准。",
  "created_at": "2025-01-15T10:35:00Z"
}
```

---

## 5. POST /api/community-agent/analyze-post — 帖子分析

**Request:**
```json
{
  "post_id": "post_001",
  "title": "求组队参加数学建模",
  "content": "大三，有编程基础，想找 2-3 个人一起参加美赛...",
  "author_external_user_id": "user_123",
  "tags": ["组队", "竞赛"]
}
```

**Response 200:**
```json
{
  "post_id": "post_001",
  "post_type": "help_request",
  "summary": "大三学生寻找数学建模队友",
  "extracted_tags": ["数学建模", "美赛", "组队"],
  "has_help_intent": true,
  "suggested_action": "convert_to_task",
  "safety_notes": []
}
```

---

## 6. POST /api/community-agent/convert-post-to-task — 帖子转任务草稿

**Request:**
```json
{
  "post_id": "post_001",
  "title": "求组队参加数学建模",
  "content": "大三，有编程基础，想找 2-3 个人一起参加美赛...",
  "external_user_id": "user_123",
  "tags": ["组队", "竞赛"]
}
```

**Response 200:**
```json
{
  "post_id": "post_001",
  "task_draft_id": "draft_post_001",
  "title": "数学建模美赛组队",
  "description": "大三学生寻找队友参加美赛...",
  "task_type": "组队招募",
  "tags": ["数学建模", "美赛", "组队"],
  "deadline_suggestion": null,
  "safety_check_passed": true,
  "safety_notes": [],
  "needs_confirmation": true,
  "created_task_id": null
}
```

---

## 7. POST /api/safety/check — 安全检查

**Request:**
```json
{
  "action_type": "create_task",
  "content": "求代考高数，价格好商量",
  "external_user_id": "user_123",
  "context": {}
}
```

**Response 200:**
```json
{
  "check_id": "sc_20250115103000",
  "risk_level": "critical",
  "risk_reason": "内容涉及代考，属于严重违规",
  "is_blocked": true,
  "requires_confirmation": false,
  "checked_at": "2025-01-15T10:30:00Z"
}
```

---

## 8. POST /api/confirmations — 创建确认请求

**Request:**
```json
{
  "external_user_id": "user_123",
  "action_type": "create_task",
  "action_summary": "将帖子转为互助任务",
  "action_detail": {"post_id": "post_001"},
  "risk_level": "low",
  "expires_in_seconds": 300
}
```

**Response 200:**
```json
{
  "confirmation_id": "confirm_20250115103000000000",
  "status": "pending",
  "action_type": "create_task",
  "action_summary": "将帖子转为互助任务",
  "risk_level": "low",
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": "2025-01-15T10:35:00Z"
}
```

**POST /api/confirmations/resolve — 处理确认:**
```json
{
  "confirmation_id": "confirm_xxx",
  "approved": true
}
```

---

## 9. POST /api/rag/search — RAG 知识库搜索

**Request:**
```json
{
  "query": "通识选修课有哪些要求",
  "agent_name": "teaching_agent",
  "top_k": 5
}
```

**Response 200:**
```json
{
  "query": "通识选修课有哪些要求",
  "results": [
    {
      "doc_id": "doc_001",
      "doc_title": "本科培养方案",
      "chunk_index": 3,
      "content": "通识选修课要求...",
      "score": 0.95
    }
  ],
  "answer": "根据培养方案..."
}
```

---

## 10. GET /api/agent-runs/{run_id} — 查询运行记录

**Response 200:**
```json
{
  "run_id": "run_abc123",
  "graph_name": "assistant_graph",
  "input_data": {...},
  "output_data": {...},
  "status": "completed",
  "error_message": null,
  "started_at": "2025-01-15T10:30:00Z",
  "finished_at": "2025-01-15T10:30:05Z"
}
```

---

## 通用错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数校验失败 |
| 404 | 资源未找到 |
| 422 | Pydantic 校验失败 |
| 500 | 服务器内部错误 |
| 503 | LLM 未配置，无法执行 AI 功能 |

