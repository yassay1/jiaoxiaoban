"""社区管理员 Agent —— 社区 AI 增强能力：帖子分析、互助意图识别、任务草稿生成。"""

from app.graphs.community_task_graph import community_task_graph
from app.services.agent_run_service import create_run, update_run


async def run_community_admin_analyze(
    post_id: str,
    title: str,
    content: str,
    author_external_user_id: str,
    tags: list[str] | None = None,
) -> dict:
    run_id = await create_run(
        db=None,
        graph_name="community_task_graph",
        input_data={
            "post_id": post_id,
            "title": title,
            "content": content,
            "external_user_id": author_external_user_id,
            "tags": tags or [],
        },
    )

    initial_state = {
        "post_id": post_id,
        "title": title,
        "content": content,
        "external_user_id": author_external_user_id,
        "tags": tags or [],
        "post_type": None,
        "summary": None,
        "has_help_intent": False,
        "task_draft": None,
        "safety_result": None,
        "needs_confirmation": False,
        "confirmed": False,
        "created_task_id": None,
        "response": None,
        "error": None,
        "messages": [],
    }

    try:
        result = await community_task_graph.ainvoke(initial_state)
        await update_run(run_id, output_data=result, status="completed")
        return {
            "post_id": post_id,
            "post_type": result.get("post_type", "other"),
            "summary": result.get("summary", ""),
            "extracted_tags": result.get("tags", tags or []),
            "has_help_intent": result.get("has_help_intent", False),
            "suggested_action": "convert_to_task" if result.get("has_help_intent") else "none",
            "safety_notes": result.get("safety_result", {}).get("risk_reason", "").split("\n") if result.get("safety_result") else [],
        }
    except Exception as e:
        await update_run(run_id, error=str(e), status="failed")
        return {"error": str(e)}
