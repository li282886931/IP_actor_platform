"""Download verified creative images from the fixed image service."""
import io
import os
import time
import warnings

import requests
from fastapi import HTTPException
from PIL import Image

IMAGE_ENDPOINT = "https://copilot-cn.bytedance.net/api/ide/v1/text_to_image"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
FORMATS = {"PNG": ("image/png", "png"), "JPEG": ("image/jpeg", "jpg"), "WEBP": ("image/webp", "webp")}


def validate_image(content: bytes):
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(502, "图片文件为空或超过 20 MB，请重试")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                fmt, width, height = image.format, *image.size
                if fmt not in FORMATS or width * height > 25_000_000:
                    raise ValueError("Unsupported image")
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
    except Exception:
        raise HTTPException(502, "生成服务未返回有效的 PNG、JPEG 或 WebP 图片，请重试") from None
    mime, extension = FORMATS[fmt]
    return {"content_type": mime, "extension": extension, "width": width, "height": height}


def generate_image(prompt: str, image_size: str):
    visual_prompt = (
        f"{prompt}. Realistic editorial concert promotional photography, professional lighting, "
        "detailed composition, no text, no logos, no watermarks; "
        "do not invent event dates, ticket prices or technical specifications."
    )
    authorization = os.environ.get('IMAGE_GENERATION_AUTHORIZATION', '').strip()
    headers = {'Authorization': authorization} if authorization else {}
    deadline = time.monotonic() + 240
    try:
        with requests.get(
            IMAGE_ENDPOINT, params={"prompt": visual_prompt, "image_size": image_size},
            headers=headers,
            timeout=(10, 240), stream=True, allow_redirects=False,
        ) as response:
            if getattr(response, 'status_code', 200) in (301, 302, 303, 307, 308, 401, 403):
                raise HTTPException(502, "文生图服务鉴权失败，请检查 IMAGE_GENERATION_AUTHORIZATION 配置")
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                if time.monotonic() > deadline:
                    raise HTTPException(502, "图片生成超时，请稍后重试")
                content.extend(chunk)
                if len(content) > MAX_IMAGE_BYTES:
                    raise HTTPException(502, "生成图片超过 20 MB，请调整尺寸后重试")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "图片生成服务连接失败，请稍后重试") from None
    content = bytes(content)
    return content, validate_image(content)
