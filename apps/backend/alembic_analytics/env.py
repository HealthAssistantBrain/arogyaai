from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path
import sys

from sqlalchemy import create_engine, pool

from alembic import context

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import models  # noqa: F401
from models.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

NEON_DIRECT_URL = (
    os.getenv("NEON_DIRECT_URL")
    or os.getenv("ANALYTICS_DIRECT_URL")
    or os.getenv("NEON_DATABASE_URL")
    or os.getenv("ANALYTICS_DATABASE_URL")
    or os.getenv("DATABASE_URL")
)

ANALYTICS_TABLES = {
    "baseline_metrics",
    "feature_snapshots",
    "health_scores",
    "recommendations",
    "risk_scores",
    "shap_values",
    "user_vitals",
    "wearable_metrics",
}

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    if type_ != "table":
        return True
    return name in ANALYTICS_TABLES


def run_migrations_offline() -> None:
    context.configure(
        url=NEON_DIRECT_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        version_table="alembic_version_analytics",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        NEON_DIRECT_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
            version_table="alembic_version_analytics",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
