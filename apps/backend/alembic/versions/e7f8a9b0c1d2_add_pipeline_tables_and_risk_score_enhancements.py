"""Add pipeline tables and risk score enhancements

Revision ID: e7f8a9b0c1d2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-16 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "risk_scores" in inspector.get_table_names():
        existing_columns = {column["name"] for column in inspector.get_columns("risk_scores")}

        if "report_id" in existing_columns:
            op.alter_column("risk_scores", "report_id", nullable=True)

        risk_columns = {
            "prediction_source": sa.Column("prediction_source", sa.String(40), nullable=False, server_default="rule_engine"),
            "prediction_status": sa.Column("prediction_status", sa.String(20), nullable=False, server_default="ready"),
            "feature_snapshot": sa.Column("feature_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            "risk_payload": sa.Column("risk_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            "health_score": sa.Column("health_score", sa.Numeric(5, 2), nullable=True),
            "pipeline_run_id": sa.Column("pipeline_run_id", sa.String(64), nullable=True),
            "is_fallback": sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        }
        for column_name, column in risk_columns.items():
            if column_name not in existing_columns:
                op.add_column("risk_scores", column)

    op.create_table(
        "feature_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("hr_mean_7d", sa.Numeric(6, 2), nullable=True),
        sa.Column("steps_avg_7d", sa.Numeric(10, 2), nullable=True),
        sa.Column("sleep_efficiency", sa.Numeric(5, 2), nullable=True),
        sa.Column("bmi", sa.Numeric(5, 2), nullable=True),
        sa.Column("lifestyle_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("activity_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("sleep_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("latest_observation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("feature_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_feature_snapshots_user_id", "feature_snapshots", ["user_id"], if_not_exists=True)
    op.create_index("ix_feature_snapshots_calculated_at", "feature_snapshots", ["calculated_at"], if_not_exists=True)

    op.create_table(
        "baseline_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_name", sa.String(80), nullable=False),
        sa.Column("mean_7d", sa.Numeric(10, 2), nullable=True),
        sa.Column("mean_30d", sa.Numeric(10, 2), nullable=True),
        sa.Column("std_dev", sa.Numeric(10, 2), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metric_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_baseline_metrics_user_id", "baseline_metrics", ["user_id"], if_not_exists=True)
    op.create_index("ix_baseline_metrics_metric_name", "baseline_metrics", ["metric_name"], if_not_exists=True)
    op.create_index("ix_baseline_metrics_calculated_at", "baseline_metrics", ["calculated_at"], if_not_exists=True)

    op.create_table(
        "lab_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("biomarker_name", sa.String(255), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("reference_range", sa.String(100), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("raw_text", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_lab_values_user_id", "lab_values", ["user_id"], if_not_exists=True)
    op.create_index("ix_lab_values_report_id", "lab_values", ["report_id"], if_not_exists=True)
    op.create_index("ix_lab_values_biomarker_name", "lab_values", ["biomarker_name"], if_not_exists=True)
    op.create_index("ix_lab_values_category", "lab_values", ["category"], if_not_exists=True)
    op.create_index("ix_lab_values_extracted_at", "lab_values", ["extracted_at"], if_not_exists=True)

    op.create_table(
        "shap_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risk_scores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_name", sa.String(120), nullable=False),
        sa.Column("shap_value", sa.Numeric(10, 4), nullable=False),
        sa.Column("abs_shap_value", sa.Numeric(10, 4), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("explanation", sa.String(500), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="rule_fallback"),
        sa.Column("shap_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_shap_values_prediction_id", "shap_values", ["prediction_id"], if_not_exists=True)
    op.create_index("ix_shap_values_user_id", "shap_values", ["user_id"], if_not_exists=True)
    op.create_index("ix_shap_values_feature_name", "shap_values", ["feature_name"], if_not_exists=True)
    op.create_index("ix_shap_values_calculated_at", "shap_values", ["calculated_at"], if_not_exists=True)
    op.create_index(
        "uq_shap_values_prediction_feature",
        "shap_values",
        ["prediction_id", "feature_name"],
        unique=True,
        if_not_exists=True,
    )

    op.create_table(
        "health_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_score_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risk_scores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("risk_component", sa.Numeric(5, 2), nullable=True),
        sa.Column("lifestyle_component", sa.Numeric(5, 2), nullable=True),
        sa.Column("vitals_component", sa.Numeric(5, 2), nullable=True),
        sa.Column("sleep_component", sa.Numeric(5, 2), nullable=True),
        sa.Column("health_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(40), nullable=False, server_default="pipeline"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_health_scores_user_id", "health_scores", ["user_id"], if_not_exists=True)
    op.create_index("ix_health_scores_risk_score_id", "health_scores", ["risk_score_id"], if_not_exists=True)
    op.create_index("ix_health_scores_calculated_at", "health_scores", ["calculated_at"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_health_scores_calculated_at", table_name="health_scores", if_exists=True)
    op.drop_index("ix_health_scores_risk_score_id", table_name="health_scores", if_exists=True)
    op.drop_index("ix_health_scores_user_id", table_name="health_scores", if_exists=True)
    op.drop_table("health_scores", if_exists=True)

    op.drop_index("uq_shap_values_prediction_feature", table_name="shap_values", if_exists=True)
    op.drop_index("ix_shap_values_calculated_at", table_name="shap_values", if_exists=True)
    op.drop_index("ix_shap_values_feature_name", table_name="shap_values", if_exists=True)
    op.drop_index("ix_shap_values_user_id", table_name="shap_values", if_exists=True)
    op.drop_index("ix_shap_values_prediction_id", table_name="shap_values", if_exists=True)
    op.drop_table("shap_values", if_exists=True)

    op.drop_index("ix_lab_values_extracted_at", table_name="lab_values", if_exists=True)
    op.drop_index("ix_lab_values_category", table_name="lab_values", if_exists=True)
    op.drop_index("ix_lab_values_biomarker_name", table_name="lab_values", if_exists=True)
    op.drop_index("ix_lab_values_report_id", table_name="lab_values", if_exists=True)
    op.drop_index("ix_lab_values_user_id", table_name="lab_values", if_exists=True)
    op.drop_table("lab_values", if_exists=True)

    op.drop_index("ix_baseline_metrics_calculated_at", table_name="baseline_metrics", if_exists=True)
    op.drop_index("ix_baseline_metrics_metric_name", table_name="baseline_metrics", if_exists=True)
    op.drop_index("ix_baseline_metrics_user_id", table_name="baseline_metrics", if_exists=True)
    op.drop_table("baseline_metrics", if_exists=True)

    op.drop_index("ix_feature_snapshots_calculated_at", table_name="feature_snapshots", if_exists=True)
    op.drop_index("ix_feature_snapshots_user_id", table_name="feature_snapshots", if_exists=True)
    op.drop_table("feature_snapshots", if_exists=True)

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "risk_scores" in inspector.get_table_names():
        existing_columns = {column["name"] for column in inspector.get_columns("risk_scores")}
        for column_name in [
            "is_fallback",
            "pipeline_run_id",
            "health_score",
            "risk_payload",
            "feature_snapshot",
            "prediction_status",
            "prediction_source",
        ]:
            if column_name in existing_columns:
                op.drop_column("risk_scores", column_name)
        if "report_id" in existing_columns:
            op.alter_column("risk_scores", "report_id", nullable=False)
