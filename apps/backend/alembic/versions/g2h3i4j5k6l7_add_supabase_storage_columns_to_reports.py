"""
Alembic migration: add storage_bucket and storage_path columns to reports table.

These columns are optional metadata to track Supabase Storage object paths.
The existing `file_url` column continues to hold the public URL used by all
UI pages — this migration is purely additive and has zero risk.

Revision: g2h3i4j5k6l7
Revises:  e7f8a9b0c1d2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'g2h3i4j5k6l7'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('reports')}

    # Add storage_bucket: records which Supabase bucket the file lives in
    if 'storage_bucket' not in existing_columns:
        op.add_column(
            'reports',
            sa.Column('storage_bucket', sa.String(length=128), nullable=True, comment='Supabase Storage bucket name'),
        )
    # Add storage_path: the object path within the bucket, e.g. "<user_id>/<uuid>-name.pdf"
    if 'storage_path' not in existing_columns:
        op.add_column(
            'reports',
            sa.Column('storage_path', sa.Text(), nullable=True, comment='Supabase Storage object path'),
        )


def downgrade() -> None:
    op.drop_column('reports', 'storage_path')
    op.drop_column('reports', 'storage_bucket')
