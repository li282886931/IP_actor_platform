import io
import time
from pathlib import Path


MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_IMAGE_PIXELS = 25_000_000
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_OCR_LANGUAGE = "chi_sim+eng"


class DocumentExtractionError(RuntimeError):
    pass


def extract_text_with_ocr(
    path: Path,
    file_kind: str,
    *,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    language=DEFAULT_OCR_LANGUAGE,
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
            pages.append({"page": index + 1, "status": "ocr"})
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
    text = _ocr_png_bytes(path.read_bytes(), language, _remaining_seconds(deadline)).strip()
    return {
        "extracted_text": text,
        "extraction_method": "ocr",
        "page_count": 1,
        "ocr_pages": [1],
        "pages": [{"page": 1, "status": "ocr"}],
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


def _ocr_png_bytes(image_bytes: bytes, language: str, timeout: float):
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise DocumentExtractionError("OCR 工具未安装，需人工录入") from exc
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            return pytesseract.image_to_string(image, lang=language, timeout=timeout)
    except pytesseract.TesseractNotFoundError as exc:
        raise DocumentExtractionError("Tesseract OCR 未安装，需人工录入") from exc
    except RuntimeError as exc:
        raise DocumentExtractionError(f"OCR 执行失败：{exc}") from exc
