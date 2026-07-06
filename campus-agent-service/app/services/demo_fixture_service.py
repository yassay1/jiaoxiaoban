from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_run_service import create_run, update_run
from app.utils.shared import AGENT_DISPLAY_NAMES, now_iso


def _task_draft_fixture() -> dict[str, Any]:
    return {
        "type": "CREATE_TASK_DRAFT",
        "payload": {
            "title": "找学习搭子复习高数",
            "content": "今晚 7 点在图书馆二楼一起复习高数，主要看极限、导数和积分题型。",
            "postType": "任务帖子",
            "taskStatus": "待接单",
            "taskCategory": "学习搭子",
            "taskLocation": "图书馆二楼",
            "taskTimeText": "今晚7点",
            "taskRewardType": "无偿",
            "taskRewardText": "互助学习",
            "taskMaxParticipants": 2,
            "tags": ["学习搭子", "高数"],
            "isAiAssisted": True,
            "sourceAgent": "DEMO fixture",
            "status": "draft",
        },
    }


_PROFESSIONAL_FIXTURES: dict[str, str] = {
    "postgraduate-agent": (
        "这是 DEMO fixture：保研准备建议按成绩排名、科研竞赛、材料整理、导师沟通四条线推进。"
        "真实模式下该回答会由 professional_agent_graph + RAG + LLM 生成。"
    ),
    "academic-teacher": "这是 DEMO fixture：选课退课和培养方案问题应以教务系统与学院最新通知为准，真实模式会走教学科石老师 Agent。",
    "science-tutor": "这是 DEMO fixture：学习题目会在真实模式下交给理科学霸小林按步骤讲解。",
    "life-teacher": "这是 DEMO fixture：校园生活问题会在真实模式下交给生活辅导员友老师给出下一步建议。",
}


def _professional_fixture(agent_id: str) -> str:
    return _PROFESSIONAL_FIXTURES.get(
        agent_id, "这是 DEMO fixture：真实模式下会调用对应 Agent 图。"
    )


async def build_demo_fixture_response(
    db: AsyncSession,
    agent_id: str,
    message: str,
    external_user_id: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    run_id = await create_run(
        db=db,
        graph_name=f"demo_fixture:{agent_id}",
        input_data={
            "agent_id": agent_id,
            "message": message,
            "external_user_id": external_user_id,
            "conversation_id": conversation_id,
            "note": "DEMO_MODE fixture, not Agent reasoning",
        },
        conversation_id=None,
    )

    if agent_id == "personal-assistant":
        reply = "当前未配置真实 LLM，已返回固定 DEMO fixture。真实模式会调用 assistant_graph。"
        actions = [_task_draft_fixture()]
    else:
        reply = _professional_fixture(agent_id)
        actions = []

    result = {
        "agentId": agent_id,
        "reply": reply,
        "actions": actions,
        "metadata": {
            "source": "demo_fixture",
            "run_id": run_id,
            "agent_display_name": AGENT_DISPLAY_NAMES.get(agent_id, agent_id),
            "is_agent_reasoning": False,
            "created_at": now_iso(),
        },
    }
    await update_run(run_id, db=db, output_data=result, status="completed")
    return result
