from app.config import LLAMA_SERVER_MODEL
from app.config import LLAMA_SERVER_TIMEOUT_SECONDS
from app.config import LLAMA_SERVER_URL
from app.core.responses import json_ok
from app.database import get_db
from app.infrastructure.cache import redis_get_json
from app.infrastructure.cache import redis_set_json
from app.integrations import llm as llm_integration
from app.models import AIGeneration
from app.schemas import AIGenerateIn
from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import os
import random
import uuid


router = APIRouter()


def fallback_ai_generate_result(payload: AIGenerateIn, db: Session):
    response = ai_generate(payload, db)
    try:
        body = json.loads(response.body.decode('utf-8'))
        return ((body.get('data') or {}).get('result') or '').strip()
    except Exception:
        return ''

@router.post('/ai/generate')
def ai_generate(payload: AIGenerateIn, db: Session = Depends(get_db)):
    generation_nonce = payload.generation_nonce or uuid.uuid4().hex
    generation_seed = random.randint(1, 2_147_483_647)
    prompt = llm_integration.build_ai_generation_prompt(payload, generation_nonce)
    cache_key = llm_integration.ai_generation_cache_key(payload, generation_nonce)
    cached_generation = redis_get_json(cache_key)
    if cached_generation and cached_generation.get('status') == 'completed' and cached_generation.get('result'):
        return json_ok({"result": cached_generation.get('result'), "cache_hit": True})

    result_text = None
    llama_server_url = os.environ.get('LLAMA_SERVER_URL', LLAMA_SERVER_URL)
    llama_server_model = os.environ.get('LLAMA_SERVER_MODEL', LLAMA_SERVER_MODEL)

    if llama_server_url:
        try:
            resp = llm_integration.requests.post(
                llama_server_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": llama_server_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.95,
                    "top_p": 0.92,
                    "presence_penalty": 0.6,
                    "frequency_penalty": 0.35,
                    "seed": generation_seed,
                    "chat_template_kwargs": {"enable_thinking": False},
                    "max_tokens": 1200,
                },
                timeout=LLAMA_SERVER_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            result_text = llm_integration.extract_llama_server_text(resp.json())
        except Exception as exc:
            print('Local llama_server error:', exc)

    api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('DASHSCOPE_API_TOKEN')

    if not result_text and api_key:
        try:
            resp = llm_integration.requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "qwen-turbo",
                    "input": {"messages": [{"role": "user", "content": prompt}]},
                    "parameters": {"temperature": 0.95, "top_p": 0.92, "max_tokens": 1200},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data.get('output', {}).get('text') if isinstance(data, dict) else None
            if not result_text:
                result_text = data.get('data', [{}])[0].get('content', '') if isinstance(data, dict) else None
        except Exception as exc:
            print('AI API error:', exc)
            result_text = None

    result_text = llm_integration.sanitize_ai_output(result_text or '')
    if not result_text:
        if payload.type == 'poster':
            result_text = f"""
传播定位
面向{payload.city or '目标城市'}核心乐迷与高频演出消费人群，突出{payload.artist or '艺人'}到场带来的稀缺现场体验，将{payload.show_name or '本场演出'}包装为城市级音乐事件。

核心文案
主标题：{payload.artist or '实力唱将'}登陆{payload.city or '城市'}，把熟悉旋律唱成这一晚的共同记忆
副标题：{payload.show_name or '年度现场'}正式开启，经典作品、沉浸舞美与万人合唱一次集结。
卖点：
- 代表作品现场演绎，覆盖歌迷高期待曲目
- 城市限定氛围，适合社交平台打卡传播
- 适合好友、情侣、家庭共同参与的高情绪价值现场
行动号召：锁定开票时间，提前预约提醒，抢占更佳观演位置。

社交平台短文案
这一晚，把耳机里的歌带到现场。{payload.artist or 'TA'}来到{payload.city or '你的城市'}，和你一起完成一次真正属于现场的合唱。

短视频脚本
镜头1：城市地标快切，字幕“{payload.city or '这座城市'}今晚有一场重要相遇”
镜头2：歌迷入场、灯牌亮起，字幕“熟悉的旋律，终于在现场响起”
镜头3：舞台灯光与人群合唱，口播“{payload.artist or '艺人'}的歌，不只适合听，也适合和万人一起唱”
镜头4：票务信息露出，字幕“立即预约，不错过开票提醒”

投放建议
优先投放给本地演出兴趣、音乐综艺兴趣、艺人粉丝和近 30 天票务浏览用户；开票前强化预约，开票当天强化倒计时和余票紧迫感。
            """.strip()
        elif payload.type == 'video_script':
            result_text = f"""
传播定位
以“城市相遇 + 现场合唱”为核心，把{payload.show_name or '演出'}塑造成{payload.city or '本地'}用户近期最值得预约的线下娱乐选择。

核心文案
主标题：{payload.artist or '艺人'}来了，下一次大合唱就在{payload.city or '这座城市'}
副标题：从耳机到现场，把熟悉旋律变成真实相遇。
行动号召：立即预约开票提醒，锁定现场席位。

社交平台短文案
别只在歌单里循环了。{payload.artist or '艺人'}来到{payload.city or '你的城市'}，这一次把副歌交给全场一起唱。

短视频脚本
镜头1｜0-3s：城市夜景与场馆外观快切；字幕“{payload.city or '这座城市'}，准备好了吗？”
镜头2｜3-8s：歌迷检票、灯牌、周边细节；口播“那些陪你通勤、熬夜、长大的歌，要在现场响起了。”
镜头3｜8-15s：舞台灯光、人群挥手、合唱氛围；字幕“{payload.artist or '艺人'} · {payload.show_name or '专属现场'}”
镜头4｜15-22s：票务页和预约按钮；口播“现在预约开票提醒，别把遗憾留到下一轮巡演。”
镜头5｜22-25s：演出信息定格；字幕“立即预约｜一起去现场”

投放建议
短视频首 3 秒必须露出城市和艺人名；达人素材侧重“我为什么一定要去现场”；信息流素材侧重开票时间、场馆和预约按钮。
            """.strip()
        else:
            result_text = f"""
传播定位
围绕{payload.artist or '艺人'}、{payload.show_name or '演出'}与{payload.city or '城市'}建立明确传播主题，服务预约、转化与二次扩散。

核心文案
{payload.show_name or '本场演出'}即将在{payload.city or '目标城市'}开启，用现场声浪连接真实情绪与城市夜晚。

社交平台短文案
把期待留给现场，把位置提前锁定。{payload.artist or '艺人'}与你在{payload.city or '这座城市'}见。

短视频脚本
镜头1：城市与场馆建立期待
镜头2：艺人代表元素引发识别
镜头3：现场氛围和购票信息完成转化

投放建议
按照预约期、开票期、临演期分层投放，分别强化关注、抢票和到场决策。
            """.strip()

    try:
        generation = AIGeneration(type=payload.type, prompt=prompt, result=result_text)
        db.add(generation)
        db.commit()
        redis_set_json(cache_key, llm_integration.completed_generation_cache_payload(result_text))
    except Exception as exc:
        print('Failed to save AI generation:', exc)

    return json_ok({"result": result_text})

@router.post('/ai/generate/stream')
def ai_generate_stream(payload: AIGenerateIn, db: Session = Depends(get_db)):
    generation_nonce = payload.generation_nonce or uuid.uuid4().hex
    generation_seed = random.randint(1, 2_147_483_647)
    prompt = llm_integration.build_ai_generation_prompt(payload, generation_nonce, allow_thinking=True)
    cache_key = llm_integration.ai_generation_cache_key(payload, generation_nonce)
    llama_server_url = os.environ.get('LLAMA_SERVER_URL', LLAMA_SERVER_URL)
    llama_server_model = os.environ.get('LLAMA_SERVER_MODEL', LLAMA_SERVER_MODEL)

    def event_stream():
        chunks = []
        thought_chunks = []
        preamble_buffer = ''
        final_started = False
        saved_by_fallback = False
        cached_generation = redis_get_json(cache_key)
        if cached_generation and cached_generation.get('status') == 'completed' and cached_generation.get('result'):
            yield llm_integration.sse_event('progress', {"message": "命中 Redis 生成缓存"})
            if cached_generation.get('thought'):
                yield llm_integration.sse_event('thought', {"content": cached_generation.get('thought')})
            yield llm_integration.sse_event('final', {"result": cached_generation.get('result'), "cache_hit": True})
            return

        yield llm_integration.sse_event('progress', {"message": "正在连接本地模型服务"})
        if not llama_server_url:
            fallback = fallback_ai_generate_result(payload, db)
            yield llm_integration.sse_event('final', {"result": fallback})
            return

        try:
            with llm_integration.requests.post(
                llama_server_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": llama_server_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.95,
                    "top_p": 0.92,
                    "presence_penalty": 0.6,
                    "frequency_penalty": 0.35,
                    "seed": generation_seed,
                    "chat_template_kwargs": {"enable_thinking": True},
                    "max_tokens": 1200,
                    "stream": True,
                },
                timeout=LLAMA_SERVER_TIMEOUT_SECONDS,
                stream=True,
            ) as resp:
                resp.raise_for_status()
                yield llm_integration.sse_event('progress', {"message": "模型正在生成内容"})
                for line in resp.iter_lines(decode_unicode=False):
                    if not line:
                        continue
                    text_line = line.decode('utf-8', errors='replace') if isinstance(line, bytes) else line
                    if not text_line.startswith('data:'):
                        continue
                    payload_text = text_line.removeprefix('data:').strip()
                    if payload_text == '[DONE]':
                        break
                    try:
                        data = json.loads(payload_text)
                    except json.JSONDecodeError:
                        continue
                    content, reasoning = llm_integration.extract_stream_delta(data)
                    if reasoning:
                        thought_chunks.append(reasoning)
                        yield llm_integration.sse_event('thought', {"content": reasoning})
                    if content:
                        visible_content, tagged_thought = llm_integration.split_think_content(content)
                        if tagged_thought:
                            thought_chunks.append(tagged_thought)
                            yield llm_integration.sse_event('thought', {"content": tagged_thought})
                        if visible_content:
                            if final_started:
                                chunks.append(visible_content)
                                yield llm_integration.sse_event('delta', {"content": visible_content})
                            else:
                                preamble_buffer += visible_content
                                start_index = llm_integration.find_final_output_start(preamble_buffer)
                                if start_index >= 0:
                                    thought_text = preamble_buffer[:start_index].strip()
                                    final_content = preamble_buffer[start_index:]
                                    if thought_text:
                                        thought_chunks.append(thought_text)
                                        yield llm_integration.sse_event('thought', {"content": thought_text})
                                    if final_content:
                                        chunks.append(final_content)
                                        yield llm_integration.sse_event('delta', {"content": final_content})
                                    preamble_buffer = ''
                                    final_started = True
                                elif len(preamble_buffer) > 24:
                                    thought_text = preamble_buffer[:-16]
                                    if thought_text.strip():
                                        thought_chunks.append(thought_text)
                                        yield llm_integration.sse_event('thought', {"content": thought_text})
                                    preamble_buffer = preamble_buffer[-16:]
                result_text = llm_integration.sanitize_ai_output(''.join(chunks) or preamble_buffer)
        except Exception as exc:
            yield llm_integration.sse_event('progress', {"message": f"流式生成不可用，已切换为后端兜底内容：{exc}"})
            result_text = ''

        if not result_text:
            result_text = fallback_ai_generate_result(payload, db)
            saved_by_fallback = True
        if not saved_by_fallback:
            try:
                generation = AIGeneration(type=payload.type, prompt=prompt, result=result_text)
                db.add(generation)
                db.commit()
                redis_set_json(cache_key, llm_integration.completed_generation_cache_payload(result_text, ''.join(thought_chunks)))
            except Exception as exc:
                print('Failed to save AI generation stream:', exc)
        yield llm_integration.sse_event('progress', {"message": "内容已整理完成"})
        yield llm_integration.sse_event('final', {"result": result_text})

    return StreamingResponse(event_stream(), media_type='text/event-stream; charset=utf-8')
