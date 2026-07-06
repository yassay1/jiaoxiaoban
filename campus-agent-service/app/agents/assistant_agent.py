"""私人助理 Agent —— 统一入口，负责需求理解、Agent 推荐、任务草稿生成、工具调用调度。"""

from app.graphs.assistant_graph import assistant_graph
from app.services.agent_run_service import create_run, update_run
from app.utils.shared import public_error_message


async def run_assistant(
    user_message: str,
    external_user_id: str,
    conversation_id: str | None = None,
) -> dict:
    run_id = await create_run(
        db=None,
        graph_name="assistant_graph",
        input_data={
            "user_message": user_message,
            "external_user_id": external_user_id,
            "conversation_id": conversation_id,
        },
    )

    initial_state = {
        "user_message": user_message,
        "external_user_id": external_user_id,
        "conversation_id": conversation_id,
        "intent": None,
        "confidence": None,
        "suggested_agent": None,
        "clarification_question": None,
        "response": None,
        "actions": [],
        "error": None,
        "messages": [],
    }

    try:
        result = await assistant_graph.ainvoke(initial_state)
        await update_run(run_id, output_data=result, status="completed")
        return {
            "conversation_id": conversation_id or "new",
            "message_id": run_id,
            "role": "assistant",
            "content": result.get("response", ""),
            "agent_name": result.get("suggested_agent"),
            "actions": result.get("actions", []),
        }
    except Exception as e:
        await update_run(run_id, error=str(e), status="failed")
        return {
            "conversation_id": conversation_id or "new",
            "message_id": run_id,
            "role": "assistant",
            "content": public_error_message(),
            "agent_name": None,
            "actions": [],
        }
