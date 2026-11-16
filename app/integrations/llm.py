import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests
from fastapi import HTTPException

from app import config
from app.schemas import AIGenerateIn


@dataclass(frozen=True)
class GenerationConnection:
    provider: str
    url: str
    model: str
    api_key: str = field(default='', repr=False)

    @property
    def cache_namespace(self):
        if self.provider == 'llama-server':
            return None
        return {
            "provider": self.provider, "url": self.url, "model": self.model, "enable_thinking": True,
            "max_tokens": int(os.environ.get('SILICONFLOW_MAX_TOKENS', config.SILICONFLOW_MAX_TOKENS)),
            "thinking_budget": int(os.environ.get('SILICONFLOW_THINKING_BUDGET', config.SILICONFLOW_THINKING_BUDGET)),
            "output_contract": "markdown-final-v2",
        }


def generation_connection(local_url, local_model):
    provider = os.environ.get('LLM_PROVIDER', config.LLM_PROVIDER).strip().lower()
    if provider == 'llama-server':
        return GenerationConnection(provider, local_url, local_model)
    if provider != 'siliconflow':
        raise HTTPException(status_code=503, detail='LLM_PROVIDER 须为 siliconflow 或 llama-server')
    api_key = os.environ.get('SILICONFLOW_API_KEY', config.SILICONFLOW_API_KEY).strip()
    model = os.environ.get('SILICONFLOW_MODEL', config.SILICONFLOW_MODEL).strip()
    base_url = os.environ.get('SILICONFLOW_BASE_URL', config.SILICONFLOW_BASE_URL).strip().rstrip('/')
    try:
        parts = urlsplit(base_url)
        valid_url = (parts.scheme == 'https' and parts.hostname and not parts.username and
                     not parts.password and not parts.query and not parts.fragment)
    except ValueError:
        valid_url = False
    if not api_key or '\r' in api_key or '\n' in api_key:
        raise HTTPException(status_code=503, detail='请配置 SILICONFLOW_API_KEY')
    if not model:
        raise HTTPException(status_code=503, detail='请配置 SILICONFLOW_MODEL')
    if not valid_url:
        raise HTTPException(status_code=503, detail='SILICONFLOW_BASE_URL 须为不含认证信息的 HTTPS 接口地址')
    url = base_url if base_url.endswith('/chat/completions') else base_url + '/chat/completions'
    return GenerationConnection(provider, url, model, api_key)


def generation_request(connection, prompt, seed, max_tokens, *, stream=False):
    headers = {"Content-Type": "application/json"}
    body = {
        "model": connection.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    if connection.provider == 'siliconflow':
        headers["Authorization"] = f"Bearer {connection.api_key}"
        body["enable_thinking"] = True
        body["max_tokens"] = int(os.environ.get('SILICONFLOW_MAX_TOKENS', config.SILICONFLOW_MAX_TOKENS))
        body["thinking_budget"] = int(os.environ.get('SILICONFLOW_THINKING_BUDGET', config.SILICONFLOW_THINKING_BUDGET))
    else:
        body.update(temperature=0.95, top_p=0.92, frequency_penalty=0.35,
                    seed=seed, presence_penalty=0.6, chat_template_kwargs={"enable_thinking": False})
    if stream:
        body["stream"] = True
    return {"headers": headers, "json": body}


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


def sanitize_ai_output(text: str, *, require_markdown: bool = False):
    if not text:
        return ''
    cleaned = re.sub(r'<think\b[^>]*>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r'^\s*</?think>\s*$', '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    if require_markdown:
        start = find_final_output_start(cleaned, require_markdown=True)
        cleaned = cleaned[start:] if start >= 0 else ''
    return cleaned.strip()


def build_ai_generation_prompt(payload: AIGenerateIn, generation_nonce: str, allow_thinking: bool = False):
    content_type_name = '短视频脚本' if payload.type == 'video_script' else '海报文案'
    thinking_prefix = '' if allow_thinking else '/no_think\n'
    thinking_rule = (
        '9. 可以在模型 reasoning_content 中组织分析过程；最终 content 只输出可直接使用的正式文案。'
        '最终正文必须以“# 演出宣发方案”开始，五个模块均使用 Markdown 二级标题；'
        'content 中禁止包含分析、思考、策略推演、输出规划或 reasoning/content 标记。'
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
       未核验的首演、独家曲目、舞台声学技术、嘉宾、周边权益、优惠、售票状态不得写成既定事实。
       禁止使用“余票告急”“即将售罄”“最后席位”“票务通道即将关闭”等无真实依据的促销断言。
       信息缺失时写准备阶段方案：字段统一标注“待确认”，卖点写“待核验后补充”，行动号召为“关注后续已核验信息”。
       建议与事实必须分开；视频镜头、时长与投放安排可作为建议，但不得把预算比例、广告权限或转化效果写成已确认结论。
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


def find_final_output_start(text: str, *, require_markdown: bool = False):
    if require_markdown:
        match = re.search(
            r'^[ \t]*#{1,6}[ \t]+(?:\d+[.、][ \t]*)?'
            r'(?:演出宣发|传播定位|核心文案|社交平台短文案|短视频脚本|投放建议)(?!分析|思考)',
            text, flags=re.MULTILINE,
        )
        return match.start() if match else -1
    match = re.search(
        r'^[ \t]*#{1,6}[ \t]+(?=\S)|(?:#{1,3}\s*)?(?:传播定位|核心文案|演出宣发方案|社交平台短文案|短视频脚本|投放建议)',
        text, flags=re.MULTILINE,
    )
    return match.start() if match else -1


class VisibleContentStream:
    """Filter thinking tags even when upstream splits their delimiters."""

    def __init__(self):
        self.pending = ''
        self.thinking = False

    def feed(self, content: str) -> str:
        self.pending += content
        output = []
        while self.pending:
            if self.thinking:
                close = re.search(r'</think\s*>', self.pending, flags=re.IGNORECASE)
                if not close:
                    break
                self.pending = self.pending[close.end():]
                self.thinking = False
                continue
            start = self.pending.find('<')
            if start < 0:
                output.append(self.pending)
                self.pending = ''
                break
            output.append(self.pending[:start])
            self.pending = self.pending[start:]
            lower = self.pending.lower()
            opening = re.match(r'<think\b[^>]*>', self.pending, flags=re.IGNORECASE)
            if opening:
                self.pending = self.pending[opening.end():]
                self.thinking = True
            elif '<think'.startswith(lower) or re.match(r'<think\b[^>]*$', lower):
                break
            else:
                output.append('<')
                self.pending = self.pending[1:]
        return ''.join(output)


def ai_generation_cache_key(payload: AIGenerateIn, generation_nonce: str, *, tenant_id: int, user_id: int,
                            model_namespace=None):
    values = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "type": payload.type,
        "show_name": payload.show_name,
        "artist": payload.artist,
        "city": payload.city,
        "generation_nonce": generation_nonce,
    }
    if model_namespace is not None:
        values["model_namespace"] = model_namespace
    raw = json.dumps(
        values,
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
