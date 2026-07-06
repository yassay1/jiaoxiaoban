from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
import httpx

from app.config.settings import get_settings


class LLMNotConfiguredError(Exception):
    """未配置真实 LLM 参数时抛出"""


LLM_NOT_CONFIGURED_MSG = (
    "当前未配置真实 LLM 参数，无法执行 Agent 智能判断。"
    "请在 .env 中配置 LLM_API_KEY、LLM_API_BASE 和 LLM_MODEL_NAME。"
)


def _get_chat_model(temperature: float = 0.7, max_tokens: int = 2048) -> ChatOpenAI:
    settings = get_settings()
    if not settings.llm_configured:
        raise LLMNotConfiguredError(LLM_NOT_CONFIGURED_MSG)

    trust_env = _should_trust_env(settings)
    kwargs = {
        "model": settings.llm_model_name,
        "api_key": settings.llm_api_key,
        "base_url": settings.llm_api_base,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": settings.llm_timeout_seconds,
        "max_retries": settings.llm_max_retries,
        "http_async_client": httpx.AsyncClient(
            timeout=settings.llm_timeout_seconds,
            trust_env=trust_env,
        ),
    }
    return ChatOpenAI(**kwargs)


def _should_trust_env(settings) -> bool:
    """Whether LLM HTTP clients should inherit system proxy env vars."""
    provider = (settings.llm_provider or "").lower()
    base_url = (settings.llm_api_base or "").lower()
    if provider == "zhipu" or "bigmodel.cn" in base_url:
        return False
    return True


async def llm_chat(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    model = _get_chat_model(temperature=temperature, max_tokens=max_tokens)
    lc_messages: list[BaseMessage] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    response = await model.ainvoke(lc_messages)
    return response.content


async def llm_structured_output(
    system_prompt: str,
    user_message: str,
    output_schema: dict | None = None,
    temperature: float = 0.3,
) -> str:
    model = _get_chat_model(temperature=temperature)
    if output_schema:
        model = model.bind(response_format={"type": "json_object"})
        schema_hint = f"\n请严格按照以下 JSON 格式返回，不要输出其他内容：\n{output_schema}"
        full_prompt = system_prompt + schema_hint
    else:
        full_prompt = system_prompt

    messages: list[BaseMessage] = [
        SystemMessage(content=full_prompt),
        HumanMessage(content=user_message),
    ]
    response = await model.ainvoke(messages)
    return response.content


def check_llm_configured() -> bool:
    return get_settings().llm_configured

