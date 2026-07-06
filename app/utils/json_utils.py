import json
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_json_text(raw: Any, source: str = "unknown") -> str:
    if raw is None:
        raise ValueError(f"{source} 返回 None，无法解析 JSON")

    if not isinstance(raw, str):
        raise ValueError(f"{source} 返回类型不是字符串：{type(raw)}")

    text = raw.strip()

    if not text:
        raise ValueError(f"{source} 返回空字符串，无法解析 JSON")

    # 处理 ```json ... ``` 或 ``` ... ``` 包裹
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    # 如果模型前后输出了解释文字，尝试截取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text


def safe_json_loads(raw: Any, source: str = "unknown") -> dict:
    text = extract_json_text(raw, source=source)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("%s 返回的原始内容不是合法 JSON：%r", source, raw)
        raise ValueError(f"{source} 返回内容不是合法 JSON：{e}") from e
