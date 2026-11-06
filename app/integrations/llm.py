import hashlib
import json
import re
from datetime import datetime, timezone

import requests

from app.schemas import AIGenerateIn


def extract_llama_server_text(data):
    if not isinstance(data, dict):
        return None

    choices = data.get('choices')
    if isinstance(choices, list) and choices:
        first_choice = choices[0] or {}
        message = first_choice.get('message') or {}
        content = message.get('content') or first_choice.get('text')
        if content:
            return sanitize_ai_output(content)

    content = data.get('content')
    if content:
        return sanitize_ai_output(content)

    response = data.get('response')
    return sanitize_ai_output(response) if response else response


def sanitize_ai_output(text: str):
    if not text:
        return ''
    cleaned = re.sub(r'<think\b[^>]*>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r'^\s*</?think>\s*$', '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    return cleaned.strip()


def build_ai_generation_prompt(payload: AIGenerateIn, generation_nonce: str, allow_thinking: bool = False):
    content_type_name = '短视频脚本' if payload.type == 'video_script' else '海报文案'
    thinking_prefix = '' if allow_thinking else '/no_think\n'
    thinking_rule = (
        '9. 可以在模型 reasoning_content 中组织分析过程；最终 content 只输出可直接使用的正式文案。'
        if allow_thinking
        else '9. 不要输出 <think>、推理过程、reasoning_content 或内部分析，只输出最终可用内容。'
    )
    return f"""{thinking_prefix}你是资深演出行业营销策划和票务转化专家。请为以下演出生成一份可直接用于运营投放的完整宣发方案。

    本次创作批次：{generation_nonce}
    内容类型：{content_type_name}
    演出名称：{payload.show_name}
    艺人：{payload.artist}
    城市：{payload.city}

    输出要求：
    1. 使用中文，语气专业、有现场感、有转化力。
    2. 内容要丰富，不要只输出一句口号。
    3. 必须包含以下小标题：传播定位、核心文案、社交平台短文案、短视频脚本、投放建议。
    4. 海报文案要包含主标题、副标题、卖点 bullet、行动号召。
    5. 短视频脚本要包含 3-5 个镜头、画面、口播/字幕、节奏提示。
    6. 避免空泛形容词，尽量围绕艺人、城市、现场体验和购票转化展开。
    7. 本次必须重新创作，不要复用上一次生成的句式、标题和行动号召；允许在传播角度、开场钩子、短视频节奏和投放建议上做变化。
    8. 禁止编造用户未提供的日期、场馆、票价、技术参数、效果提升比例或销售成绩；必要时使用“待确认”或提出补充建议。
    {thinking_rule}
    """.strip()


def sse_event(event: str, data: dict):
    return f"data: {json.dumps({'event': event, **data}, ensure_ascii=False)}\n\n"


def extract_stream_delta(data):
    if not isinstance(data, dict):
        return '', ''
    choices = data.get('choices')
    if not isinstance(choices, list) or not choices:
        return '', ''
    delta = choices[0].get('delta') or choices[0].get('message') or {}
    content = delta.get('content') or choices[0].get('text') or ''
    reasoning = delta.get('reasoning_content') or ''
    return content, reasoning


def split_think_content(text: str):
    if not text:
        return '', ''
    thought_parts = re.findall(r'<think\b[^>]*>(.*?)</think>', text, flags=re.IGNORECASE | re.DOTALL)
    visible = re.sub(r'<think\b[^>]*>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
    visible = re.sub(r'^\s*</?think>\s*$', '', visible, flags=re.IGNORECASE | re.MULTILINE)
    thought = '\n'.join(part.strip() for part in thought_parts if part.strip())
    return visible, thought


def find_final_output_start(text: str):
    match = re.search(r'(?:#{1,3}\s*)?(?:传播定位|核心文案|演出宣发方案|社交平台短文案|短视频脚本|投放建议)', text)
    return match.start() if match else -1


def ai_generation_cache_key(payload: AIGenerateIn, generation_nonce: str):
    raw = json.dumps(
        {
            "type": payload.type,
            "show_name": payload.show_name,
            "artist": payload.artist,
            "city": payload.city,
            "generation_nonce": generation_nonce,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f"ai:generation:{digest}"


def completed_generation_cache_payload(result: str, thought: str = ''):
    return {
        "status": "completed",
        "result": result,
        "thought": thought,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
