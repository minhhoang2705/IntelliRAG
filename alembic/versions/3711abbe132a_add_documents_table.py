"""add documents table

Revision ID: 3711abbe132a
Revises: 631d4a550bd9
Create Date: 2025-10-21 09:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3711abbe132a'
down_revision: Union[str, None] = '631d4a550bd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(512), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger, nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('minio_bucket', sa.String(255), nullable=False),
        sa.Column('minio_raw_path', sa.String(1024), nullable=False),
        sa.Column('minio_processed_path', sa.String(1024), nullable=True),
        sa.Column('custom_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.collection_id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('idx_documents_collection', 'documents', ['collection_id'])
    op.create_index('idx_documents_hash', 'documents', ['file_hash'])
    op.create_index('idx_documents_uploaded', 'documents', ['uploaded_at'])
    op.create_index('idx_documents_collection_hash', 'documents', ['collection_id', 'file_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_documents_collection_hash', 'documents')
    op.drop_index('idx_documents_uploaded', 'documents')
    op.drop_index('idx_documents_hash', 'documents')
    op.drop_index('idx_documents_collection', 'documents')
    op.drop_table('documents')
