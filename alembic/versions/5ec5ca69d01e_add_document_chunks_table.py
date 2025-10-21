"""add document_chunks table

Revision ID: 5ec5ca69d01e
Revises: 3711abbe132a
Create Date: 2025-10-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5ec5ca69d01e'
down_revision: Union[str, None] = '3711abbe132a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'document_chunks',
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('chunk_text', sa.Text, nullable=False),
        sa.Column('chunk_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('vector_id', sa.String(255), nullable=True),
        sa.Column('embedding_model', sa.String(255), nullable=True),
        sa.Column('minio_chunk_path', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.collection_id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('idx_chunks_document', 'document_chunks', ['document_id'])
    op.create_index('idx_chunks_collection', 'document_chunks', ['collection_id'])
    op.create_index('idx_chunks_vector_id', 'document_chunks', ['vector_id'])
    op.create_index('idx_chunks_document_index', 'document_chunks', ['document_id', 'chunk_index'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_chunks_document_index', 'document_chunks')
    op.drop_index('idx_chunks_vector_id', 'document_chunks')
    op.drop_index('idx_chunks_collection', 'document_chunks')
    op.drop_index('idx_chunks_document', 'document_chunks')
    op.drop_table('document_chunks')
