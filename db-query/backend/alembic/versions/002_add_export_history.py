"""Add query exports table.

Revision ID: 002
Revises: 001
Create Date: 2026-02-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add query exports table."""
    op.create_table(
        'query_exports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('database_name', sa.String(length=50), nullable=False),
        sa.Column('sql', sa.Text(), nullable=False),
        sa.Column('export_format', sa.String(length=20), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('export_time_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['database_name'], ['databaseconnections.name'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_query_exports_database_name', 'query_exports', ['database_name'], unique=False)
    op.create_index('idx_query_exports_created_at', 'query_exports', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop query exports table."""
    op.drop_index('idx_query_exports_created_at', table_name='query_exports')
    op.drop_index('idx_query_exports_database_name', table_name='query_exports')
    op.drop_table('query_exports')
