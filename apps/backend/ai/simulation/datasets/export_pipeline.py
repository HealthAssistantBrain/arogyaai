from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import pandas as pd

from .._shared import encode_json, log_simulation


class ExportPipeline:
    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        path.write_text("\n".join(encode_json(row) for row in rows), encoding="utf-8")

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        pd.DataFrame(rows).to_csv(path, index=False)

    @staticmethod
    def _write_parquet(path: Path, rows: list[dict[str, Any]]) -> str:
        try:
            import pyarrow  # noqa: F401
        except ImportError:
            return "skipped_missing_pyarrow"
        pd.DataFrame(rows).to_parquet(path, index=False)
        return "written"

    @classmethod
    def export(
        cls,
        *,
        export_root: str | Path,
        splits: dict[str, list[dict[str, Any]]],
        manifests: dict[str, Any],
        contract: dict[str, Any],
    ) -> dict[str, Any]:
        base = Path(export_root)
        for folder in ("train", "validation", "test", "manifests", "schemas", "metadata"):
            (base / folder).mkdir(parents=True, exist_ok=True)

        results: dict[str, Any] = {"root": str(base)}
        for split_name in ("train", "validation", "test"):
            rows = splits.get(split_name, [])
            jsonl_path = base / split_name / f"{split_name}.jsonl"
            csv_path = base / split_name / f"{split_name}.csv"
            parquet_path = base / split_name / f"{split_name}.parquet"
            cls._write_jsonl(jsonl_path, rows)
            cls._write_csv(csv_path, rows)
            parquet_status = cls._write_parquet(parquet_path, rows) if rows else "skipped_empty"
            results[split_name] = {
                "jsonl": str(jsonl_path),
                "csv": str(csv_path),
                "parquet": str(parquet_path),
                "parquet_status": parquet_status,
                "rows": len(rows),
            }

        (base / "manifests" / "schema_manifest.json").write_text(json.dumps(manifests, indent=2, default=str), encoding="utf-8")
        (base / "schemas" / "dataset_contract.json").write_text(json.dumps(contract, indent=2, default=str), encoding="utf-8")
        (base / "metadata" / "generation_metadata.json").write_text(json.dumps(contract, indent=2, default=str), encoding="utf-8")
        log_simulation("DATASET EXPORTED", root=base, train_rows=len(splits.get("train", [])))
        return results
