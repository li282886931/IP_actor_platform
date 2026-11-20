import os
import threading
import time
from pathlib import Path


MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_IMAGE_PIXELS = 25_000_000
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_TEXT_SCORE = 0.5
DEFAULT_CPU_THREADS = 2
_OCR_ENGINE = None
_OCR_ENGINE_CONFIG = None
_OCR_ENGINE_LOCK = threading.Lock()


class DocumentExtractionError(RuntimeError):
    pass


def extract_text_with_ocr(
    path: Path,
    file_kind: str,
    *,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    language=None,
):
    path = Path(path)
    _validate_file_size(path)
    deadline = time.monotonic() + timeout_seconds
    if file_kind == "pdf":
        return _extract_pdf(path, deadline, language)
    if file_kind == "image":
        return _extract_image(path, deadline, language)
    raise DocumentExtractionError(f"不支持 OCR 文件类型：{file_kind}")


def _extract_pdf(path: Path, deadline: float, language: str):
    try:
        document = _open_pdf(path)
    except ImportError as exc:
        raise DocumentExtractionError("缺少 PDF OCR 依赖 PyMuPDF，需人工录入") from exc
    try:
        page_count = document.page_count
        if page_count > MAX_PDF_PAGES:
            raise DocumentExtractionError(f"PDF 超过 {MAX_PDF_PAGES} 页限制")
        texts = []
        pages = []
        ocr_pages = []
        used_text = False
        for index in range(page_count):
            _remaining_seconds(deadline)
            page = document[index]
            text = (page.get_text() or "").strip()
            if text:
                used_text = True
                texts.append(text)
                pages.append({"page": index + 1, "status": "text"})
                continue
            pixmap = page.get_pixmap(dpi=150)
            if pixmap.width * pixmap.height > MAX_IMAGE_PIXELS:
                raise DocumentExtractionError(f"第 {index + 1} 页超过 2500 万像素限制")
            text = _ocr_png_bytes(
                pixmap.tobytes("png"),
                language,
                _remaining_seconds(deadline),
            ).strip()
            texts.append(text)
            ocr_pages.append(index + 1)
            pages.append({
                "page": index + 1,
                "status": "ocr",
                "engine": "rapidocr",
                "model": "PP-OCRv4",
            })
        if ocr_pages and used_text:
            method = "text+ocr"
        elif ocr_pages:
            method = "ocr"
        else:
            method = "text"
        return {
            "extracted_text": "\n".join(text for text in texts if text),
            "extraction_method": method,
            "page_count": page_count,
            "ocr_pages": ocr_pages,
            "pages": pages,
        }
    finally:
        document.close()


def _extract_image(path: Path, deadline: float, language: str):
    width, height = _image_size(path)
    if width * height > MAX_IMAGE_PIXELS:
        raise DocumentExtractionError("图片超过 2500 万像素限制")
    text = _ocr_png_bytes(
        path.read_bytes(),
        language,
        _remaining_seconds(deadline),
    ).strip()
    return {
        "extracted_text": text,
        "extraction_method": "ocr",
        "page_count": 1,
        "ocr_pages": [1],
        "pages": [{
            "page": 1,
            "status": "ocr",
            "engine": "rapidocr",
            "model": "PP-OCRv4",
        }],
    }


def _validate_file_size(path: Path):
    if path.stat().st_size > MAX_FILE_BYTES:
        raise DocumentExtractionError("文件超过 20 MB 限制")


def _remaining_seconds(deadline: float):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise DocumentExtractionError("文档解析超过 120 秒限制")
    return min(remaining, DEFAULT_TIMEOUT_SECONDS)


def _open_pdf(path: Path):
    import fitz

    return fitz.open(str(path))


def _image_size(path: Path):
    from PIL import Image

    with Image.open(path) as image:
        return image.size


def _bounded_int(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


def _bounded_float(name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


def get_ocr_engine():
    global _OCR_ENGINE, _OCR_ENGINE_CONFIG
    config = (
        _bounded_int("OCR_CPU_THREADS", DEFAULT_CPU_THREADS, 1, 8),
        _bounded_float("OCR_TEXT_SCORE", DEFAULT_TEXT_SCORE, 0.0, 1.0),
    )
    if _OCR_ENGINE is not None and _OCR_ENGINE_CONFIG == config:
        return _OCR_ENGINE
    with _OCR_ENGINE_LOCK:
        if _OCR_ENGINE is not None and _OCR_ENGINE_CONFIG == config:
            return _OCR_ENGINE
        try:
            from rapidocr_onnxruntime import RapidOCR

            _OCR_ENGINE = RapidOCR(
                intra_op_num_threads=config[0],
                inter_op_num_threads=1,
                text_score=config[1],
            )
        except Exception:
            raise DocumentExtractionError(
                "RapidOCR PP-OCRv4 模型初始化失败，需人工录入"
            ) from None
        _OCR_ENGINE_CONFIG = config
        return _OCR_ENGINE


def normalize_rapidocr_result(raw_result, text_score=DEFAULT_TEXT_SCORE):
    rows = raw_result[0] if isinstance(raw_result, tuple) else raw_result
    normalized = []
    for row in rows or []:
        if not isinstance(row, (list, tuple)) or len(row) < 3:
            continue
        box, text, score = row[:3]
        try:
            score = float(score)
            points = box.tolist() if hasattr(box, "tolist") else box
            x = min(float(point[0]) for point in points)
            y = min(float(point[1]) for point in points)
        except (TypeError, ValueError, IndexError):
            continue
        text = str(text or "").strip()
        if not text or score < text_score:
            continue
        normalized.append({
            "text": text,
            "score": score,
            "box": points,
            "_x": x,
            "_y": y,
        })
    normalized.sort(key=lambda item: (item["_y"], item["_x"]))
    lines = [
        {key: value for key, value in item.items() if not key.startswith("_")}
        for item in normalized
    ]
    return {
        "text": "\n".join(item["text"] for item in lines),
        "lines": lines,
        "engine": "rapidocr",
        "model": "PP-OCRv4",
    }


def _ocr_png_bytes(image_bytes: bytes, language=None, timeout: float = DEFAULT_TIMEOUT_SECONDS):
    del language
    started = time.monotonic()
    try:
        raw_result = get_ocr_engine()(image_bytes)
    except DocumentExtractionError:
        raise
    except Exception:
        raise DocumentExtractionError(
            "RapidOCR PP-OCRv4 推理失败，需人工录入"
        ) from None
    if time.monotonic() - started > timeout:
        raise DocumentExtractionError("文档解析超过 120 秒限制")
    score = _bounded_float("OCR_TEXT_SCORE", DEFAULT_TEXT_SCORE, 0.0, 1.0)
    return normalize_rapidocr_result(raw_result, score)["text"]
