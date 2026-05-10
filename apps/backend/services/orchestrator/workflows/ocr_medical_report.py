from __future__ import annotations

from typing import Any

from integrations.ocr_service import OCRInput, OCRService
from services.lab_pipeline_service import extract_lab_values, normalize_lab_values
from services.orchestrator.workflow_engine import BaseWorkflow, WorkflowExecutionContext
from services.report_service import ReportService


class OCRMedicalReportWorkflow(BaseWorkflow):
    name = "ocr_medical_report"
    aliases = frozenset({"medical_report_ocr", "ocr_report"})
    timeout_seconds = 18.0
    stage_timeouts = {
        "input_validation": 3.0,
        "provider_inference": 10.0,
        "structured_formatting": 6.0,
    }
    retryable_stages = frozenset({"provider_inference"})

    async def validate_input(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        filename = str(context.payload.get("filename") or context.payload.get("file_name") or "").strip()
        file_bytes = context.payload.get("file_bytes")
        ocr_text = str(context.payload.get("ocr_text") or context.payload.get("full_text") or "").strip()
        if not filename:
            raise ValueError("filename is required for OCR medical report workflow")
        if not isinstance(file_bytes, (bytes, bytearray)) and not ocr_text:
            raise ValueError("file_bytes or pre-extracted OCR text is required")
        return {"filename": filename, "content_type": context.payload.get("content_type")}

    async def build_context(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        if request.db is None:
            return deps.context_manager._empty_context(  # noqa: SLF001
                workflow=self.name,
                metadata=context.metadata,
            )
        return await deps.context_manager.build_workflow_context(
            request.db,
            request.user_id,
            current_user=request.current_user,
            workflow="report_summary",
            metadata=request.metadata,
        )

    async def retrieve_knowledge(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        return {"source": "skipped", "query": "", "summary": [], "documents": []}

    async def generate_response(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
    ) -> dict[str, Any]:
        payload = context.payload
        filename = str(payload.get("filename") or payload.get("file_name") or "report").strip()
        content_type = payload.get("content_type")
        pre_extracted_text = str(payload.get("ocr_text") or payload.get("full_text") or "").strip()
        if pre_extracted_text:
            text_pages = payload.get("text_pages") if isinstance(payload.get("text_pages"), list) else []
            return {
                "text": pre_extracted_text,
                "provider": "pre_extracted_text",
                "source_type": str(payload.get("text_source") or "pre_extracted"),
                "confidence": payload.get("ocr_confidence"),
                "warnings": payload.get("ocr_warnings") if isinstance(payload.get("ocr_warnings"), list) else [],
                "pages": text_pages,
            }

        ocr_result = OCRService().extract_text(
            OCRInput(
                filename=filename,
                content=bytes(payload.get("file_bytes") or b""),
                content_type=content_type,
            )
        )
        return {
            "text": ocr_result.text,
            "provider": ocr_result.provider,
            "source_type": ocr_result.source_type,
            "confidence": ocr_result.confidence,
            "warnings": list(ocr_result.warnings),
            "pages": ReportService._ocr_pages(ocr_result),  # noqa: SLF001
        }

    async def format_output(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        title = str(context.payload.get("title") or context.payload.get("filename") or "Medical Report").strip()
        extracted_text = str(response.get("text") or "").strip()
        text_source = str(response.get("source_type") or "ocr").strip()
        ocr_confidence = response.get("confidence")
        text_pages = response.get("pages") if isinstance(response.get("pages"), list) else []
        raw_values = extract_lab_values(
            extracted_text,
            source_type=text_source,
            source_confidence=ocr_confidence,
            page_metadata=text_pages,
        )
        biomarkers = normalize_lab_values(raw_values)
        abnormal_values = [
            item for item in biomarkers
            if str(item.get("status") or "").strip().lower() in {"high", "low", "abnormal", "critical"}
        ]
        structured_lab_data = {
            "test_type": ReportService._infer_test_type(title, extracted_text, biomarkers),  # noqa: SLF001
            "biomarkers": biomarkers,
            "abnormal_values": abnormal_values,
        }
        summary_lines = ReportService._summarize_text(extracted_text, biomarkers)  # noqa: SLF001
        summary_view = ReportService._build_summary_view(  # noqa: SLF001
            extracted_text,
            summary_lines,
            biomarkers,
            title,
            "ocr-medical-report-workflow",
        )
        return {
            "title": title,
            "summary": summary_lines,
            "patient_summary": " ".join(summary_lines).strip() or ReportService.PROCESSING_SUMMARY,
            "structured_summary": ReportService._structured_summary_from_view(summary_view),  # noqa: SLF001
            "summary_view": summary_view,
            "full_text": extracted_text,
            "ocr_text": extracted_text[:1200],
            "markers": biomarkers[:12],
            "biomarkers": biomarkers,
            "abnormal_values": abnormal_values,
            "structured_lab_data": structured_lab_data,
            "source": "ocr-medical-report-workflow",
            "text_source": text_source,
            "ocr_provider": response.get("provider"),
            "ocr_confidence": ocr_confidence,
            "ocr_warnings": response.get("warnings") or [],
            "text_pages": text_pages,
        }

    async def deterministic_fallback(
        self,
        request: Any,
        deps: Any,
        context: WorkflowExecutionContext,
        error: Exception,
    ) -> dict[str, Any]:
        title = str(context.payload.get("title") or context.payload.get("filename") or "Medical Report").strip()
        return {
            "title": title,
            "summary": ["Readable report text could not be extracted safely."],
            "patient_summary": "Readable report text could not be extracted safely.",
            "structured_summary": {
                "patient": "",
                "test": title or "Medical Report",
                "findings": ["Readable report text could not be extracted safely."],
                "abnormal": [],
                "notes": str(error),
            },
            "summary_view": ReportService._build_processing_summary_view(title),  # noqa: SLF001
            "full_text": "",
            "ocr_text": "",
            "markers": [],
            "biomarkers": [],
            "abnormal_values": [],
            "structured_lab_data": ReportService._empty_structured_lab_data(title),  # noqa: SLF001
            "source": "ocr-medical-report-fallback",
            "ocr_warnings": [str(error)],
            "provider": "deterministic_fallback",
        }

