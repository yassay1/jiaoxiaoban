from app.services.llm_service import llm_chat

DIRECT_CHAT_PROMPT = """你是"交小伴"校园生活智能体平台的私人助理，友好、简洁、有帮助。

你可以帮用户做的事情：
- 日常聊天、产品介绍
- 推荐合适的专业 Agent（教学科石老师、保研学长阿泽、理科学霸小林、生活辅导员友老师）
- 创建求助任务（找人帮忙取快递、借东西、组队等）
- 查找求助任务
- 创建提醒

当用户问专业问题时，你可以礼貌地推荐对应的专业 Agent。

下面是一些常见问题的回答方向：
- 求助任务：用户可以发布找队友、借东西、代取快递等互助请求
- 专业 Agent：教学科石老师（教务）、保研学长阿泽（保研竞赛）、理科学霸小林（数理化学业）、生活辅导员友老师（生活服务）
- 提醒功能：用户可以设置一次性或周期性提醒

请根据用户的问题提供有帮助的回答。"""


async def direct_chat(
    user_message: str,
    recent_messages: list[dict] | None = None,
    memory_context: dict | None = None,
    product_rag_context: list[dict] | None = None,
) -> str:
    system_parts = [DIRECT_CHAT_PROMPT]

    if memory_context:
        mem_lines = ["\n## 用户长期记忆"]
        for mem_type, content in memory_context.items():
            mem_lines.append(f"- [{mem_type}] {content}")
        system_parts.append("\n".join(mem_lines))

    if product_rag_context:
        rag_lines = ["\n## 相关校园/产品知识"]
        for doc in product_rag_context:
            rag_lines.append(f"- {doc.get('content', '')[:300]}")
        system_parts.append("\n".join(rag_lines))

    system_prompt = "\n".join(system_parts)
    messages = [{"role": "system", "content": system_prompt}]
    if recent_messages:
        messages.extend(recent_messages)
    messages.append({"role": "user", "content": user_message})
    return await llm_chat(messages, temperature=0.7)
