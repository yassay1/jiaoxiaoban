# AGENTS.md

## Project Identity

This repository is the backend service for “交小伴”, a campus life agent platform.

Do not treat this project as a simple chatbot. The correct product positioning is:

- A campus life agent platform.
- A campus community + AI assistant experience.
- A backend Agent Service layer that connects private assistant routing, professional consultation agents, community help-task workflows, RAG, memory, confirmations, and run logs.

The external product description should emphasize “校园生活智能体平台”.
The technical architecture description may use “校园 Agent Service 中台”.

## Architecture Decision

The project should follow this architecture:

```text
Campus App / Web Frontend
  ↓
FastAPI API Layer
  ↓
Assistant Orchestrator Graph
  ↓
Capability Layer
  ├── Direct Chat / Platform QA
  ├── Professional Agent Sessions
  └── Community Help-Task Workflow
  ↓
Service Layer
  ├── LLM Service
  ├── RAG Service
  ├── Conversation / Message Service
  ├── Agent Run Service
  ├── Community Adapter
  └── Database / Cache Services
  ↓
PostgreSQL + pgvector + Redis + external community service
```

The multi-agent architecture should not be a set of equal agents chatting freely with one another.

The correct design is:

- Custom Workflow as the backbone.
- Router-style intent planning in the private assistant.
- Handoff-style transition for professional agents.
- Workflow/subgraph-style execution for community help tasks.
- RAG, memory, confirmation, and run logs as supporting infrastructure.

## User Entry Design

There are two valid user entry paths:

### 1. Private assistant entry

The user asks the private assistant. The private assistant understands intent and decides whether to:

- Answer directly.
- Recommend or route to a professional agent.
- Start a community help-task workflow.
- Ask for missing information.
- Return a frontend action.

### 2. Direct professional agent entry

The user may also enter a professional agent page directly, such as:

- 教学科石老师
- 保研学长阿泽
- 理科学霸小林
- 生活辅导员友老师

Direct entry should not be treated as a violation of the architecture. The assistant is the unified smart entry, but the product may still expose direct professional-agent pages for clarity and usability.

## Professional Agent Design

Professional agents are consultation agents.

Supported agents:

- `teaching_agent`: 教学科石老师
- `postgraduate_agent`: 保研学长阿泽
- `science_agent`: 理科学霸小林
- `life_agent`: 生活辅导员友老师

Professional agents should share one `professional_agent_graph` and differ by profile, prompt, RAG scope, and boundary reminder.

Professional agents should focus on:

- Campus academic consultation.
- Postgraduate recommendation /保研 guidance.
- Study and science tutoring.
- Life service guidance.

Professional agents should not directly publish, delete, or modify community help tasks.

## Private Assistant Design

The private assistant is the orchestrator, not a normal expert agent.

It should be responsible for:

- Intent recognition.
- Route planning.
- User-facing guidance.
- Professional-agent recommendation.
- Handoff initiation.
- Community workflow invocation.
- Context preparation.
- Run logging.

The private assistant may answer directly only when the user asks ordinary questions, product questions, or lightweight campus questions that do not require a professional session.

## Community Help-Task Agent Design

The community help-task agent is not a long-term chat agent.

It should be designed as a workflow/action agent. It is invoked to complete specific community task operations.

First-stage supported operations:

- Create a help task.
- Search help tasks.
- Delete the user's own help task.

The create-task flow should be:

```text
extract fields
  ↓
check missing fields
  ↓
ask for missing fields or generate draft
  ↓
safety / validity check
  ↓
user confirmation
  ↓
publish through community adapter
  ↓
return result
```

The search flow should be:

```text
understand search need
  ↓
build search query
  ↓
call community adapter
  ↓
rank / format results
  ↓
return result
```

The delete flow should be:

```text
list or search my tasks
  ↓
match target task
  ↓
ask for confirmation
  ↓
delete through community adapter
  ↓
return result
```

## Reminder Agent

The reminder agent is no longer a current development target.

Unless a task explicitly asks for reminder functionality:

- Do not modify `reminder_graph`.
- Do not prioritize reminder API.
- Do not design future architecture around reminder functionality.
- Do not spend development effort polishing reminder flows.

If reminder code blocks current startup or tests, make the minimal necessary compatibility fix only.

## RAG Scope

First-stage RAG should mainly serve professional agents.

Priority:

1. Professional agents.
2. Private assistant product/platform explanation.
3. Community task assistant only when needed for task policy or safety rules.

Do not over-engineer RAG before the professional-agent flow is clear.

## Development Rules

1. Do not rewrite the project from scratch.
2. Preserve the current FastAPI + LangGraph + PostgreSQL architecture unless the task explicitly says otherwise.
3. Prefer small, reviewable changes.
4. Before changing a graph, read its state definition, nodes, edges, and API entry path.
5. Before changing an API, check the corresponding schema and service.
6. Do not hide unfinished behavior behind mock data while pretending it is real reasoning.
7. Do not remove existing endpoints unless explicitly requested.
8. Do not add new production dependencies without explaining why.
9. Do not put API keys or secrets in source code.
10. Do not bypass confirmation for actions that create, delete, or publish user-visible community content.
11. Do not make the project overly focused on rule-based fallback logic. The priority is a clean product positioning and agent architecture.

## Preferred Development Direction

The next major development effort should be architecture improvement, not minor fallback polishing.

Recommended order:

1. Finalize documentation and architecture naming.
2. Refactor assistant planning output to make intent, target agent, and execution mode explicit.
3. Strengthen professional-agent direct entry and handoff entry.
4. Fix assistant-to-community-task workflow routing.
5. Improve community task workflow completeness.
6. Improve RAG for professional agents.
7. Add tests or lightweight verification scripts for graph routing.
8. Only later consider productionizing real community-service integration.

## Validation Checklist

After modifying code, check:

- FastAPI imports successfully.
- `assistant_graph` compiles.
- `professional_agent_graph` compiles.
- `community_agent_subgraph` compiles.
- Direct professional-agent API still works.
- Private assistant can still route to professional agents.
- Community create/search/delete flows do not bypass confirmation where confirmation is needed.
- Reminder functionality is not accidentally expanded.
- No API keys or secrets are committed.
