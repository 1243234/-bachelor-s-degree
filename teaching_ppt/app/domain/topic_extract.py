"""从口语化输入中通过 LLM 信息抽取得到简短课程主题（供课件生成使用）。"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

_MAX_INPUT_CHARS = 500
_MAX_OUTPUT_CHARS = 200

TOPIC_EXTRACT_SYSTEM = """你是信息抽取助手。用户会用口语描述想做的教学课件，你只从中抽出「课程/演讲的核心主题」短语。
要求：
- 只输出一个 JSON 对象，不要 Markdown，不要其它说明，格式严格为：{"topic":"..."}
- topic 为中文或中英混合的简短名词性短语，10～80 字为宜，能直接用作课件标题；不要包含「请生成」「帮我」等指令性措辞
- 若用户已直接给出清晰主题句，可轻度去掉冗余，但不得改变核心含义"""


def _chat_api_base(api_base_url: str) -> str:
    base = api_base_url.rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    return base


def _fallback_topic(raw: str) -> str:
    t = raw.strip()
    if len(t) > _MAX_OUTPUT_CHARS:
        return t[:_MAX_OUTPUT_CHARS]
    return t


async def extract_topic_via_llm(
    raw: str,
    *,
    api_base_url: str,
    model: str,
    api_key: str,
    timeout_s: float,
) -> str:
    """调用聊天补全 API，返回抽取后的主题；无 Key、请求失败或解析失败时退回裁剪后的原文。"""
    text_in = raw.strip()
    if not text_in:
        return ""
    if len(text_in) > _MAX_INPUT_CHARS:
        text_in = text_in[:_MAX_INPUT_CHARS]

    key = (api_key or "").strip()
    if not key:
        return _fallback_topic(text_in)

    url = _chat_api_base(api_base_url) + "/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": TOPIC_EXTRACT_SYSTEM},
            {"role": "user", "content": text_in},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        if not content or not isinstance(content, str):
            return _fallback_topic(text_in)
        text = content.strip()
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                return _fallback_topic(text_in)
            obj = json.loads(m.group(0))
        if not isinstance(obj, dict):
            return _fallback_topic(text_in)
        topic_val = obj.get("topic")
        if not isinstance(topic_val, str):
            return _fallback_topic(text_in)
        topic_val = topic_val.strip()
        if not topic_val:
            return _fallback_topic(text_in)
        if len(topic_val) > _MAX_OUTPUT_CHARS:
            topic_val = topic_val[:_MAX_OUTPUT_CHARS]
        return topic_val
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, IndexError, TypeError):
        return _fallback_topic(text_in)
