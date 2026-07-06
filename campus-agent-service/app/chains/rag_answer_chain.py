from app.services.llm_service import llm_chat, LLMNotConfiguredError

RAG_ANSWER_PROMPT = """你是"交小伴"校园生活智能体平台的专业 Agent。

根据以下检索到的知识库内容回答用户问题。要求：
1. 优先基于提供的知识库内容回答
2. 如果知识库内容不足以回答问题，诚实说明
3. 涉及官方规则时提醒用户以学校最新通知为准
4. 回答结构清晰，分点说明
5. 不要在知识库内容之外编造信息

知识库检索结果：
{context}

请基于以上内容回答用户问题。"""


async def generate_rag_answer(query: str, context_chunks: list[str]) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    system_prompt = RAG_ANSWER_PROMPT.format(context=context)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    return await llm_chat(messages, temperature=0.5)
