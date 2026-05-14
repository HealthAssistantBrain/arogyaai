from __future__ import annotations

from typing import Any


class TrainingSplitGenerator:
    @staticmethod
    def split(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        user_ids = sorted({record["user_id"] for record in records})
        if not user_ids:
            return {"train": [], "validation": [], "test": []}
        train_cutoff = max(1, int(len(user_ids) * 0.7))
        validation_cutoff = max(train_cutoff + 1, int(len(user_ids) * 0.85))
        train_users = set(user_ids[:train_cutoff])
        validation_users = set(user_ids[train_cutoff:validation_cutoff])
        test_users = set(user_ids[validation_cutoff:])
        return {
            "train": [record for record in records if record["user_id"] in train_users],
            "validation": [record for record in records if record["user_id"] in validation_users],
            "test": [record for record in records if record["user_id"] in test_users],
        }
