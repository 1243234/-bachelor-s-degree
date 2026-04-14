import json
import re

import httpx

from app.domain.models import JobCreateBody, SlideDeckModel


SYSTEM_PROMPT = """你是教学课件设计助手。根据用户给出的主题与受众，输出**仅包含 JSON**（不要 Markdown 围栏），结构如下：
{
  "slides": [
    {
      "title": "本页标题",
      "bullets": ["要点1", "要点2"],
      "notes": "讲稿/备注，可空字符串"
    }
  ]
}
要求：slides 数量与用户要求的页数一致（不含封面时可少 1 页，由你决定）；每页 bullets 2–5 条；语言简洁适合课堂讲解。"""


async def generate_slide_deck(body: JobCreateBody, timeout_s: float) -> SlideDeckModel:
    user_content = (
        f"主题：{body.topic}\n受众：{body.audience}\n需要约 {body.slide_count} 页幻灯片内容。"
    )
    base = body.api_base_url.rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    url = base + "/chat/completions"
    payload: dict = {
        "model": body.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.6,
    }
    # OpenAI-compatible JSON mode（部分网关支持；不支持时仍尝试解析 content）
    payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {body.api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()

    content = data["choices"][0]["message"]["content"]
    if not content or not isinstance(content, str):
        raise ValueError("LLM 返回内容为空")

    text = content.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError("无法解析 LLM 返回的 JSON") from None
        obj = json.loads(m.group(0))

    deck = SlideDeckModel.model_validate(obj)
    if not deck.slides:
        raise ValueError("LLM 未生成任何幻灯片")
    return deck
