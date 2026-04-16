from __future__ import annotations

"""
Training template for future model integration.

This file intentionally does not execute training automatically. It exists as a
plug-in point for a future offline training job or notebook export.
"""

from pathlib import Path


def main() -> None:
    print("ML training template is present, but no training job is executed.")
    print("Wire your dataset, preprocessing, and model artifact export here.")
    print(f"Expected artifact path example: {Path('artifacts/model.pkl').as_posix()}")


if __name__ == "__main__":
    main()
