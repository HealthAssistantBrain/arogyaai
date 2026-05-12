from __future__ import annotations

from typing import Any

from ..utils import utc_now_iso
from .fhir_mapping import FHIRMapper


class EHRExportBuilder:
    @staticmethod
    def generate(bundle: dict[str, Any]) -> dict[str, Any]:
        fhir_bundle = FHIRMapper.to_bundle(bundle)
        return {
            "format": "fhir-r4",
            "exported_at": utc_now_iso(),
            "bundle": fhir_bundle,
        }
