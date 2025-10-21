"""add processing_jobs table

Revision ID: 8658271d6578
Revises: 5ec5ca69d01e
Create Date: 2025-10-21 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8658271d6578'
down_revision: Union[str, None] = '5ec5ca69d01e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'processing_jobs',
        sa.Column('job_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('progress', postgresql.JSONB, nullable=False, server_default='{"upload": "pending", "parsing": "pending", "chunking": "pending", "embedding": "pending", "indexing": "pending"}'),
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer, nullable=False, server_default='3'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.collection_id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('idx_jobs_document', 'processing_jobs', ['document_id'])
    op.create_index('idx_jobs_collection', 'processing_jobs', ['collection_id'])
    op.create_index('idx_jobs_status', 'processing_jobs', ['status'])
    op.create_index('idx_jobs_created', 'processing_jobs', ['created_at'])
    op.create_index('idx_jobs_status_created', 'processing_jobs', ['status', 'created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_jobs_status_created', 'processing_jobs')
    op.drop_index('idx_jobs_created', 'processing_jobs')
    op.drop_index('idx_jobs_status', 'processing_jobs')
    op.drop_index('idx_jobs_collection', 'processing_jobs')
    op.drop_index('idx_jobs_document', 'processing_jobs')
    op.drop_table('processing_jobs')
