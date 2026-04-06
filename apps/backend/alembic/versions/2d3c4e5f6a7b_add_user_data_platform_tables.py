"""add user data platform tables

Revision ID: 2d3c4e5f6a7b
Revises: 9b6c1f2a7d4e
Create Date: 2026-04-06 19:30:00.000000

"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2d3c4e5f6a7b"
down_revision: Union[str, Sequence[str], None] = "9b6c1f2a7d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)} if table_name in inspector.get_table_names() else set()


def _unique_sets(inspector: sa.Inspector, table_name: str) -> set[tuple[str, ...]]:
    return {tuple(item["column_names"]) for item in inspector.get_unique_constraints(table_name)} if table_name in inspector.get_table_names() else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    now = datetime.now(timezone.utc)

    user_profile_columns = _column_names(inspector, "user_profile")
    if "phone_number" not in user_profile_columns:
        op.add_column("user_profile", sa.Column("phone_number", sa.String(length=20), nullable=True))
    if "height_cm" not in user_profile_columns:
        op.add_column("user_profile", sa.Column("height_cm", sa.Numeric(5, 2), nullable=True))
    if "weight_kg" not in user_profile_columns:
        op.add_column("user_profile", sa.Column("weight_kg", sa.Numeric(5, 2), nullable=True))

    if "user_profile" in inspector.get_table_names():
        if "phone" in user_profile_columns:
            bind.execute(sa.text("UPDATE user_profile SET phone_number = COALESCE(phone_number, phone) WHERE phone IS NOT NULL"))
        if "height" in user_profile_columns:
            bind.execute(sa.text("UPDATE user_profile SET height_cm = COALESCE(height_cm, height) WHERE height IS NOT NULL"))
        if "weight" in user_profile_columns:
            bind.execute(sa.text("UPDATE user_profile SET weight_kg = COALESCE(weight_kg, weight) WHERE weight IS NOT NULL"))

    existing_user_profile_uniques = _unique_sets(inspector, "user_profile")
    if ("user_id",) not in existing_user_profile_uniques and "user_profile" in inspector.get_table_names():
        try:
            op.create_unique_constraint("uq_user_profile_user_id", "user_profile", ["user_id"])
        except Exception:
            pass

    if "user_devices" not in inspector.get_table_names():
        op.create_table(
            "user_devices",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "provider",
                sa.Enum("google_fit", "apple_health", "fitbit", name="user_device_provider_enum"),
                nullable=False,
            ),
            sa.Column("access_token", sa.Text(), nullable=True),
            sa.Column("refresh_token", sa.Text(), nullable=True),
            sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "provider", name="uq_user_devices_user_provider"),
        )

    if "user_vitals" not in inspector.get_table_names():
        op.create_table(
            "user_vitals",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("type", sa.Enum("heart_rate", "steps", "sleep", "spo2", name="user_vital_type_enum"), nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column("unit", sa.String(length=20), nullable=False),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.Enum("google_fit", name="user_vital_source_enum"), nullable=False),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "user_settings" not in inspector.get_table_names():
        op.create_table(
            "user_settings",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("auto_fetch_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("fetch_interval_minutes", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("last_fetch_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_user_settings_user_id"),
            sa.CheckConstraint("fetch_interval_minutes IN (5, 10, 15, 20, 25, 30)", name="ck_user_settings_interval"),
        )

    inspector = sa.inspect(bind)

    if "user_devices" in inspector.get_table_names():
        existing_index_names = {index["name"] for index in inspector.get_indexes("user_devices")}
        if op.f("ix_user_devices_user_id") not in existing_index_names:
            op.create_index(op.f("ix_user_devices_user_id"), "user_devices", ["user_id"], unique=False)
        if op.f("ix_user_devices_provider") not in existing_index_names:
            op.create_index(op.f("ix_user_devices_provider"), "user_devices", ["provider"], unique=False)

    if "user_vitals" in inspector.get_table_names():
        existing_index_names = {index["name"] for index in inspector.get_indexes("user_vitals")}
        if op.f("ix_user_vitals_user_id") not in existing_index_names:
            op.create_index(op.f("ix_user_vitals_user_id"), "user_vitals", ["user_id"], unique=False)
        if op.f("ix_user_vitals_type") not in existing_index_names:
            op.create_index(op.f("ix_user_vitals_type"), "user_vitals", ["type"], unique=False)
        if op.f("ix_user_vitals_timestamp") not in existing_index_names:
            op.create_index(op.f("ix_user_vitals_timestamp"), "user_vitals", ["timestamp"], unique=False)
        if op.f("ix_user_vitals_user_id_type_timestamp") not in existing_index_names:
            op.create_index(
                op.f("ix_user_vitals_user_id_type_timestamp"),
                "user_vitals",
                ["user_id", "type", "timestamp"],
                unique=False,
            )

    if "user_settings" in inspector.get_table_names():
        existing_index_names = {index["name"] for index in inspector.get_indexes("user_settings")}
        if op.f("ix_user_settings_user_id") not in existing_index_names:
            op.create_index(op.f("ix_user_settings_user_id"), "user_settings", ["user_id"], unique=True)

    # Backfill canonical user_devices rows from legacy Google Fit connections.
    if "google_fit_connections" in inspector.get_table_names() and "user_devices" in inspector.get_table_names():
        legacy_rows = bind.execute(
            sa.text(
                "SELECT user_id, access_token_encrypted, refresh_token_encrypted, token_expires_at, last_sync_status, created_at "
                "FROM google_fit_connections"
            )
        ).mappings().all()
        existing_devices = {
            (row["user_id"], row["provider"])
            for row in bind.execute(sa.text("SELECT user_id, provider FROM user_devices")).mappings().all()
        }
        rows_to_insert = []
        for row in legacy_rows:
            key = (row["user_id"], "google_fit")
            if key in existing_devices:
                continue
            rows_to_insert.append(
                {
                    "id": uuid.uuid4(),
                    "user_id": row["user_id"],
                    "provider": "google_fit",
                    "access_token": row["access_token_encrypted"],
                    "refresh_token": row["refresh_token_encrypted"],
                    "token_expiry": row["token_expires_at"],
                    "is_active": row["last_sync_status"] != "disconnected",
                    "created_at": row["created_at"] or now,
                }
            )
        if rows_to_insert:
            op.bulk_insert(
                sa.table(
                    "user_devices",
                    sa.column("id", postgresql.UUID(as_uuid=True)),
                    sa.column("user_id", postgresql.UUID(as_uuid=True)),
                    sa.column("provider", sa.String()),
                    sa.column("access_token", sa.Text()),
                    sa.column("refresh_token", sa.Text()),
                    sa.column("token_expiry", sa.DateTime(timezone=True)),
                    sa.column("is_active", sa.Boolean()),
                    sa.column("created_at", sa.DateTime(timezone=True)),
                ),
                rows_to_insert,
            )

    # Backfill default settings for all active users.
    if "user_settings" in inspector.get_table_names() and "users" in inspector.get_table_names():
        users = bind.execute(sa.text("SELECT id FROM users WHERE is_deleted = false")).mappings().all()
        existing_settings = {row["user_id"] for row in bind.execute(sa.text("SELECT user_id FROM user_settings")).mappings().all()}
        rows_to_insert = []
        for row in users:
            if row["id"] in existing_settings:
                continue
            rows_to_insert.append(
                {
                    "id": uuid.uuid4(),
                    "user_id": row["id"],
                    "auto_fetch_enabled": False,
                    "fetch_interval_minutes": 15,
                    "last_fetch_at": None,
                }
            )
        if rows_to_insert:
            op.bulk_insert(
                sa.table(
                    "user_settings",
                    sa.column("id", postgresql.UUID(as_uuid=True)),
                    sa.column("user_id", postgresql.UUID(as_uuid=True)),
                    sa.column("auto_fetch_enabled", sa.Boolean()),
                    sa.column("fetch_interval_minutes", sa.Integer()),
                    sa.column("last_fetch_at", sa.DateTime(timezone=True)),
                ),
                rows_to_insert,
            )

    # Backfill vitals data from legacy tables.
    if "user_vitals" in inspector.get_table_names():
        existing_vitals = {
            (row["user_id"], row["type"], row["timestamp"], row["source"])
            for row in bind.execute(sa.text("SELECT user_id, type, timestamp, source FROM user_vitals")).mappings().all()
        }
        rows_to_insert = []

        if "vitals_data" in inspector.get_table_names():
            legacy_vitals = bind.execute(
                sa.text(
                    "SELECT user_id, recorded_at, heart_rate_bpm, oxygen_saturation_spo2 FROM vitals_data"
                )
            ).mappings().all()
            for row in legacy_vitals:
                if row["heart_rate_bpm"] is not None:
                    key = (row["user_id"], "heart_rate", row["recorded_at"], "google_fit")
                    if key not in existing_vitals:
                        rows_to_insert.append(
                            {
                                "id": uuid.uuid4(),
                                "user_id": row["user_id"],
                                "type": "heart_rate",
                                "value": float(row["heart_rate_bpm"]),
                                "unit": "bpm",
                                "timestamp": row["recorded_at"],
                                "source": "google_fit",
                                "created_at": now,
                            }
                        )
                if row["oxygen_saturation_spo2"] is not None:
                    key = (row["user_id"], "spo2", row["recorded_at"], "google_fit")
                    if key not in existing_vitals:
                        rows_to_insert.append(
                            {
                                "id": uuid.uuid4(),
                                "user_id": row["user_id"],
                                "type": "spo2",
                                "value": float(row["oxygen_saturation_spo2"]),
                                "unit": "%",
                                "timestamp": row["recorded_at"],
                                "source": "google_fit",
                                "created_at": now,
                            }
                        )

        if "wearable_data" in inspector.get_table_names():
            legacy_wearable = bind.execute(
                sa.text(
                    "SELECT user_id, recorded_at, step_count, sleep_duration_minutes FROM wearable_data"
                )
            ).mappings().all()
            for row in legacy_wearable:
                if row["step_count"] is not None:
                    key = (row["user_id"], "steps", row["recorded_at"], "google_fit")
                    if key not in existing_vitals:
                        rows_to_insert.append(
                            {
                                "id": uuid.uuid4(),
                                "user_id": row["user_id"],
                                "type": "steps",
                                "value": float(row["step_count"]),
                                "unit": "count",
                                "timestamp": row["recorded_at"],
                                "source": "google_fit",
                                "created_at": now,
                            }
                        )
                if row["sleep_duration_minutes"] is not None:
                    key = (row["user_id"], "sleep", row["recorded_at"], "google_fit")
                    if key not in existing_vitals:
                        rows_to_insert.append(
                            {
                                "id": uuid.uuid4(),
                                "user_id": row["user_id"],
                                "type": "sleep",
                                "value": round(float(row["sleep_duration_minutes"]) / 60.0, 2),
                                "unit": "hours",
                                "timestamp": row["recorded_at"],
                                "source": "google_fit",
                                "created_at": now,
                            }
                        )

        if rows_to_insert:
            op.bulk_insert(
                sa.table(
                    "user_vitals",
                    sa.column("id", postgresql.UUID(as_uuid=True)),
                    sa.column("user_id", postgresql.UUID(as_uuid=True)),
                    sa.column("type", sa.String()),
                    sa.column("value", sa.Float()),
                    sa.column("unit", sa.String()),
                    sa.column("timestamp", sa.DateTime(timezone=True)),
                    sa.column("source", sa.String()),
                    sa.column("created_at", sa.DateTime(timezone=True)),
                ),
                rows_to_insert,
            )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_vitals_user_id_type_timestamp"), table_name="user_vitals")
    op.drop_index(op.f("ix_user_vitals_timestamp"), table_name="user_vitals")
    op.drop_index(op.f("ix_user_vitals_type"), table_name="user_vitals")
    op.drop_index(op.f("ix_user_vitals_user_id"), table_name="user_vitals")
    op.drop_table("user_vitals")
    op.execute("DROP TYPE IF EXISTS user_vital_source_enum")
    op.execute("DROP TYPE IF EXISTS user_vital_type_enum")

    op.drop_index(op.f("ix_user_devices_provider"), table_name="user_devices")
    op.drop_index(op.f("ix_user_devices_user_id"), table_name="user_devices")
    op.drop_table("user_devices")
    op.execute("DROP TYPE IF EXISTS user_device_provider_enum")

    op.drop_index(op.f("ix_user_settings_user_id"), table_name="user_settings")
    op.drop_table("user_settings")

    op.drop_column("user_profile", "weight_kg")
    op.drop_column("user_profile", "height_cm")
    op.drop_column("user_profile", "phone_number")
