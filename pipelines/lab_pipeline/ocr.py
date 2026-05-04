"""OCR facade for standalone lab-pipeline callers."""
from __future__ import annotations

try:
    from apps.backend.integrations.ocr_service import OCRInput, OCRResult, OCRService
except ImportError:  # pragma: no cover - standalone package without backend path
    from integrations.ocr_service import OCRInput, OCRResult, OCRService

__all__ = ["OCRInput", "OCRResult", "OCRService"]
