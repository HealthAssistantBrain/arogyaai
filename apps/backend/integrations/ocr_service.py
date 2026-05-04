"""OCR provider abstraction for scanned reports.

The service prefers Google Vision when credentials and the optional SDK are
available, then falls back to local Tesseract.  All OCR dependencies are loaded
inside provider methods so digital-PDF uploads still work in lean environments.
"""
from __future__ import annotations

import logging
import mimetypes
import os
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Protocol

logger = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class OCRInput:
    filename: str
    content: bytes
    content_type: str | None = None

    @property
    def mime_type(self) -> str:
        return self.content_type or mimetypes.guess_type(self.filename)[0] or "application/octet-stream"

    @property
    def extension(self) -> str:
        return Path(self.filename or "").suffix.lower()

    @property
    def is_pdf(self) -> bool:
        return self.mime_type == "application/pdf" or self.extension == ".pdf"


@dataclass(frozen=True)
class OCRWord:
    text: str
    bbox: dict[str, object] | None = None
    confidence: float | None = None
    page_number: int | None = None


@dataclass(frozen=True)
class OCRLine:
    text: str
    bbox: dict[str, object] | None = None
    confidence: float | None = None
    page_number: int | None = None
    words: list[OCRWord] = field(default_factory=list)


@dataclass(frozen=True)
class OCRPage:
    page_number: int
    text: str
    confidence: float | None = None
    width: int | None = None
    height: int | None = None
    words: list[OCRWord] = field(default_factory=list)
    lines: list[OCRLine] = field(default_factory=list)


@dataclass(frozen=True)
class OCRResult:
    text: str
    provider: str
    source_type: str
    confidence: float | None = None
    page_count: int | None = None
    pages: list[OCRPage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return bool((self.text or "").strip())

    @property
    def words(self) -> list[OCRWord]:
        return [word for page in self.pages for word in page.words]

    @property
    def lines(self) -> list[OCRLine]:
        return [line for page in self.pages for line in page.lines]


class OCRProvider(Protocol):
    name: str

    def extract_text(self, file: OCRInput) -> OCRResult:
        ...


class GoogleVisionOCRProvider:
    name = "google-vision"

    def extract_text(self, file: OCRInput) -> OCRResult:
        if os.getenv("OCR_GOOGLE_VISION_ENABLED", "true").strip().lower() in {"0", "false", "no"}:
            raise RuntimeError("Google Vision OCR is disabled")

        try:
            from google.cloud import vision
        except ModuleNotFoundError as exc:
            raise RuntimeError("google-cloud-vision is not installed") from exc

        client = vision.ImageAnnotatorClient()
        if file.is_pdf:
            return self._extract_pdf(client, vision, file)
        return self._extract_image(client, vision, file)

    def _extract_image(self, client: object, vision: object, file: OCRInput) -> OCRResult:
        image = vision.Image(content=file.content)
        response = client.document_text_detection(image=image)
        error = getattr(response, "error", None)
        if error and getattr(error, "message", ""):
            raise RuntimeError(getattr(error, "message"))

        annotation = getattr(response, "full_text_annotation", None)
        text = (getattr(annotation, "text", "") or "").strip()
        confidence = _google_annotation_confidence(annotation)
        pages = _google_pages(annotation, start_page=1)
        return OCRResult(
            text=text,
            provider=self.name,
            source_type="ocr_google_vision",
            confidence=confidence,
            page_count=len(pages) or (1 if text else None),
            pages=pages,
        )

    def _extract_pdf(self, client: object, vision: object, file: OCRInput) -> OCRResult:
        feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
        input_config = vision.InputConfig(content=file.content, mime_type="application/pdf")
        request = vision.AnnotateFileRequest(input_config=input_config, features=[feature])
        response = client.batch_annotate_files(requests=[request])

        text_parts: list[str] = []
        confidences: list[float] = []
        responses = getattr(response, "responses", []) or []
        pages: list[OCRPage] = []
        for file_response in responses:
            page_responses = getattr(file_response, "responses", []) or []
            for page_response in page_responses:
                error = getattr(page_response, "error", None)
                if error and getattr(error, "message", ""):
                    raise RuntimeError(getattr(error, "message"))
                annotation = getattr(page_response, "full_text_annotation", None)
                annotation_pages = _google_pages(annotation, start_page=len(pages) + 1)
                page_text = "\n\n".join(page.text for page in annotation_pages if page.text).strip()
                if page_text:
                    text_parts.append(page_text)
                confidence = _google_annotation_confidence(annotation)
                if confidence is not None:
                    confidences.append(confidence)
                pages.extend(annotation_pages)

        text = "\n\n".join(text_parts).strip()
        return OCRResult(
            text=text,
            provider=self.name,
            source_type="ocr_google_vision",
            confidence=_mean(confidences),
            page_count=len(pages) or None,
            pages=pages,
        )


class TesseractOCRProvider:
    name = "tesseract"

    def extract_text(self, file: OCRInput) -> OCRResult:
        images = _render_pdf_pages(file.content) if file.is_pdf else [_open_image(file.content)]
        text_parts: list[str] = []
        page_results: list[OCRPage] = []
        confidences: list[float] = []
        warnings: list[str] = []

        try:
            import pytesseract
        except ModuleNotFoundError as exc:
            raise RuntimeError("pytesseract is not installed") from exc

        for page_index, image in enumerate(images, start=1):
            page_confidences: list[float] = []
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                ocr_words, ocr_lines = _tesseract_lines_from_data(data, page_index)
                words: list[str] = [word.text for word in ocr_words]
                for word in ocr_words:
                    if word.confidence is None:
                        continue
                    confidences.append(word.confidence)
                    page_confidences.append(word.confidence)
                page_text = " ".join(words).strip()
                if not page_text:
                    page_text = (pytesseract.image_to_string(image) or "").strip()
                if page_text:
                    text_parts.append(page_text)
                    page_results.append(
                        OCRPage(
                            page_number=page_index,
                            text=page_text,
                            confidence=_mean(page_confidences),
                            words=ocr_words,
                            lines=ocr_lines,
                        )
                    )
            except Exception as exc:  # pragma: no cover - depends on local OCR binary
                warnings.append(str(exc))

        return OCRResult(
            text="\n\n".join(text_parts).strip(),
            provider=self.name,
            source_type="ocr_tesseract",
            confidence=_mean(confidences),
            page_count=len(images),
            pages=page_results,
            warnings=warnings,
        )


class OCRService:
    """Provider orchestrator: Google Vision first, Tesseract fallback."""

    def __init__(self, providers: list[OCRProvider] | None = None) -> None:
        self.providers = providers or [GoogleVisionOCRProvider(), TesseractOCRProvider()]

    def extract_text(self, file: OCRInput) -> OCRResult:
        warnings: list[str] = []
        try:
            low_confidence_threshold = float(os.getenv("OCR_LOW_CONFIDENCE_THRESHOLD", "0.55"))
        except ValueError:
            low_confidence_threshold = 0.55
        low_confidence_result: OCRResult | None = None

        for index, provider in enumerate(self.providers):
            try:
                result = provider.extract_text(file)
            except Exception as exc:
                logger.info("OCR provider %s unavailable: %s", provider.name, exc)
                warnings.append(f"{provider.name}: {exc}")
                continue
            if result.usable:
                normalized_result = OCRResult(
                    text=result.text,
                    provider=result.provider,
                    source_type=result.source_type,
                    confidence=result.confidence,
                    page_count=result.page_count,
                    pages=result.pages,
                    warnings=[*warnings, *result.warnings],
                )
                if (
                    provider.name == "google-vision"
                    and normalized_result.confidence is not None
                    and normalized_result.confidence < low_confidence_threshold
                    and index + 1 < len(self.providers)
                ):
                    low_confidence_result = normalized_result
                    warnings.append(
                        f"{provider.name}: low confidence {normalized_result.confidence:.3f}; trying fallback"
                    )
                    continue
                return normalized_result
            warnings.append(f"{provider.name}: no text returned")

        if low_confidence_result is not None:
            return OCRResult(
                text=low_confidence_result.text,
                provider=low_confidence_result.provider,
                source_type=low_confidence_result.source_type,
                confidence=low_confidence_result.confidence,
                page_count=low_confidence_result.page_count,
                pages=low_confidence_result.pages,
                warnings=list(dict.fromkeys([*low_confidence_result.warnings, *warnings])),
            )

        return OCRResult(
            text="",
            provider="none",
            source_type="ocr_unavailable",
            confidence=0.0,
            pages=[],
            warnings=warnings,
        )


def _open_image(content: bytes):
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pillow is not installed") from exc

    image = Image.open(BytesIO(content))
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    return image


def _render_pdf_pages(content: bytes):
    try:
        from pdf2image import convert_from_bytes

        return convert_from_bytes(content, dpi=int(os.getenv("OCR_PDF_DPI", "220")))
    except ModuleNotFoundError:
        pass
    except Exception as exc:
        logger.info("pdf2image PDF rendering failed: %s", exc)

    try:
        import fitz
    except ModuleNotFoundError as exc:
        raise RuntimeError("pdf2image or PyMuPDF is required for scanned PDF OCR") from exc

    images = []
    document = fitz.open(stream=content, filetype="pdf")
    zoom = float(os.getenv("OCR_PDF_ZOOM", "2.2"))
    matrix = fitz.Matrix(zoom, zoom)
    for page in document:
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        images.append(_open_image(pixmap.tobytes("png")))
    return images


def _google_annotation_confidence(annotation: object | None) -> float | None:
    pages = getattr(annotation, "pages", None) if annotation is not None else None
    if not pages:
        return None

    scores: list[float] = []
    for page in pages:
        for block in getattr(page, "blocks", []) or []:
            confidence = getattr(block, "confidence", None)
            if confidence is not None:
                scores.append(float(confidence))
    return _mean(scores)


def _google_pages(annotation: object | None, *, start_page: int = 1) -> list[OCRPage]:
    raw_pages = getattr(annotation, "pages", None) if annotation is not None else None
    if not raw_pages:
        text = (getattr(annotation, "text", "") or "").strip() if annotation is not None else ""
        return [OCRPage(page_number=start_page, text=text)] if text else []

    pages: list[OCRPage] = []
    multiple_pages = len(raw_pages) > 1
    for page_offset, raw_page in enumerate(raw_pages):
        page_number = start_page + page_offset
        words: list[OCRWord] = []
        for block in getattr(raw_page, "blocks", []) or []:
            for paragraph in getattr(block, "paragraphs", []) or []:
                for raw_word in getattr(paragraph, "words", []) or []:
                    symbols = getattr(raw_word, "symbols", []) or []
                    word_text = "".join(getattr(symbol, "text", "") or "" for symbol in symbols).strip()
                    if not word_text:
                        continue
                    words.append(
                        OCRWord(
                            text=word_text,
                            bbox=_bounding_poly_to_dict(getattr(raw_word, "bounding_box", None)),
                            confidence=_safe_confidence(getattr(raw_word, "confidence", None)),
                            page_number=page_number,
                        )
                    )

        lines = _group_words_into_lines(words)
        page_text = "\n".join(line.text for line in lines).strip()
        if not multiple_pages:
            page_text = (getattr(annotation, "text", "") or "").strip() or page_text
        pages.append(
            OCRPage(
                page_number=page_number,
                text=page_text,
                confidence=_mean([word.confidence for word in words if word.confidence is not None]),
                width=getattr(raw_page, "width", None),
                height=getattr(raw_page, "height", None),
                words=words,
                lines=lines,
            )
        )
    return pages


def _tesseract_lines_from_data(data: dict[str, list[object]], page_number: int) -> tuple[list[OCRWord], list[OCRLine]]:
    rows: dict[tuple[object, object, object], list[OCRWord]] = {}
    all_words: list[OCRWord] = []
    texts = data.get("text", []) or []
    confidences = data.get("conf", []) or []
    lefts = data.get("left", []) or []
    tops = data.get("top", []) or []
    widths = data.get("width", []) or []
    heights = data.get("height", []) or []
    block_nums = data.get("block_num", []) or []
    par_nums = data.get("par_num", []) or []
    line_nums = data.get("line_num", []) or []

    for index, text in enumerate(texts):
        word_text = str(text or "").strip()
        if not word_text:
            continue
        word = OCRWord(
            text=word_text,
            bbox=_box_from_xywh(_list_get(lefts, index), _list_get(tops, index), _list_get(widths, index), _list_get(heights, index)),
            confidence=_safe_confidence(_list_get(confidences, index), scale_100=True),
            page_number=page_number,
        )
        all_words.append(word)
        key = (_list_get(block_nums, index), _list_get(par_nums, index), _list_get(line_nums, index))
        rows.setdefault(key, []).append(word)

    lines: list[OCRLine] = []
    for row_words in rows.values():
        sorted_words = sorted(row_words, key=lambda word: (_bbox_value(word.bbox, "y_min"), _bbox_value(word.bbox, "x_min")))
        lines.append(
            OCRLine(
                text=" ".join(word.text for word in sorted_words).strip(),
                bbox=_union_word_boxes(sorted_words),
                confidence=_mean([word.confidence for word in sorted_words if word.confidence is not None]),
                page_number=page_number,
                words=sorted_words,
            )
        )
    lines.sort(key=lambda line: (_bbox_value(line.bbox, "y_min"), _bbox_value(line.bbox, "x_min")))
    return all_words, lines


def _group_words_into_lines(words: list[OCRWord]) -> list[OCRLine]:
    rows: list[list[OCRWord]] = []
    for word in sorted(words, key=lambda item: (_bbox_center(item.bbox, "y"), _bbox_value(item.bbox, "x_min"))):
        center_y = _bbox_center(word.bbox, "y")
        height = max(_bbox_value(word.bbox, "y_max") - _bbox_value(word.bbox, "y_min"), 1.0)
        target: list[OCRWord] | None = None
        for row in rows:
            row_center = _bbox_center(_union_word_boxes(row), "y")
            if abs(center_y - row_center) <= max(height * 0.65, 8.0):
                target = row
                break
        if target is None:
            rows.append([word])
        else:
            target.append(word)

    lines: list[OCRLine] = []
    for row in rows:
        sorted_words = sorted(row, key=lambda item: _bbox_value(item.bbox, "x_min"))
        lines.append(
            OCRLine(
                text=" ".join(word.text for word in sorted_words).strip(),
                bbox=_union_word_boxes(sorted_words),
                confidence=_mean([word.confidence for word in sorted_words if word.confidence is not None]),
                page_number=sorted_words[0].page_number if sorted_words else None,
                words=sorted_words,
            )
        )
    lines.sort(key=lambda line: (_bbox_value(line.bbox, "y_min"), _bbox_value(line.bbox, "x_min")))
    return lines


def _bounding_poly_to_dict(bounding_poly: object | None) -> dict[str, object] | None:
    vertices = getattr(bounding_poly, "vertices", None) if bounding_poly is not None else None
    if not vertices:
        return None
    points = [
        {"x": getattr(vertex, "x", None), "y": getattr(vertex, "y", None)}
        for vertex in vertices
    ]
    xs = [point["x"] for point in points if point["x"] is not None]
    ys = [point["y"] for point in points if point["y"] is not None]
    if not xs or not ys:
        return {"vertices": points}
    return {
        "x_min": min(xs),
        "y_min": min(ys),
        "x_max": max(xs),
        "y_max": max(ys),
        "vertices": points,
    }


def _box_from_xywh(left: object, top: object, width: object, height: object) -> dict[str, object] | None:
    try:
        x_min = float(left)
        y_min = float(top)
        x_max = x_min + float(width)
        y_max = y_min + float(height)
    except (TypeError, ValueError):
        return None
    return {
        "x_min": x_min,
        "y_min": y_min,
        "x_max": x_max,
        "y_max": y_max,
        "vertices": [
            {"x": x_min, "y": y_min},
            {"x": x_max, "y": y_min},
            {"x": x_max, "y": y_max},
            {"x": x_min, "y": y_max},
        ],
    }


def _union_word_boxes(words: list[OCRWord]) -> dict[str, object] | None:
    boxes = [word.bbox for word in words if word.bbox]
    if not boxes:
        return None
    x_values = [float(box[key]) for box in boxes for key in ("x_min", "x_max") if box.get(key) is not None]
    y_values = [float(box[key]) for box in boxes for key in ("y_min", "y_max") if box.get(key) is not None]
    if not x_values or not y_values:
        return None
    return {
        "x_min": min(x_values),
        "y_min": min(y_values),
        "x_max": max(x_values),
        "y_max": max(y_values),
        "vertices": [
            {"x": min(x_values), "y": min(y_values)},
            {"x": max(x_values), "y": min(y_values)},
            {"x": max(x_values), "y": max(y_values)},
            {"x": min(x_values), "y": max(y_values)},
        ],
    }


def _bbox_value(bbox: dict[str, object] | None, key: str) -> float:
    try:
        return float((bbox or {}).get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bbox_center(bbox: dict[str, object] | None, axis: str) -> float:
    if axis == "x":
        return (_bbox_value(bbox, "x_min") + _bbox_value(bbox, "x_max")) / 2.0
    return (_bbox_value(bbox, "y_min") + _bbox_value(bbox, "y_max")) / 2.0


def _safe_confidence(value: object, *, scale_100: bool = False) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0:
        return None
    if scale_100:
        score = score / 100.0
    return max(0.0, min(1.0, score))


def _list_get(values: list[object], index: int) -> object | None:
    return values[index] if index < len(values) else None


def _mean(values: list[float]) -> float | None:
    cleaned = [max(0.0, min(1.0, float(value))) for value in values if value is not None]
    if not cleaned:
        return None
    return round(sum(cleaned) / len(cleaned), 3)
