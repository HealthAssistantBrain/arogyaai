from __future__ import annotations

from pathlib import Path
import sys


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from pipelines.ml_pipeline.train import train_and_save_model


def main() -> None:
    train_and_save_model(model_type="sleep")


if __name__ == "__main__":
    main()
