"""Pydantic schemas for API request/response models.

This module defines data validation models for the RAG API endpoints.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.services.query_router.classifier import QueryType


class QueryClassificationSchema(BaseModel):
    """Schema for query classification results."""

    query_type: QueryType = Field(..., description="Classified query type")
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="Classification confidence score")
    reasoning: str = Field(..., min_length=1,
                           description="Reasoning for classification")


class QueryRequest(BaseModel):
    """Request model for query endpoint."""

    query: str = Field(..., min_length=1, description="User query text")
    top_k: int = Field(
        default=5, ge=1, description="Number of documents to retrieve")
    use_rag: bool = Field(
        default=True, description="Whether to use RAG retrieval")
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: Optional[int] = Field(
        default=None, ge=1, description="Max tokens to generate")

class IngestRequest(BaseModel):
    """Request model for document ingestion."""
    file_path: str = Field(..., description="Cloud storage path to document (gs:// or s3://)")
    collection_name: str = Field(..., description="Target collection")

class SourceDocument(BaseModel):
    """Model for source document retrieved from vector DB."""

    text: str = Field(..., description="Document text content")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    id: str = Field(..., description="Document ID")


class QueryResponse(BaseModel):
    """Response model for query endpoint."""

    answer: str = Field(..., min_length=1, description="Generated answer")
    sources: list[SourceDocument] = Field(
        default_factory=list, description="Retrieved source documents")
    used_rag: bool = Field(..., description="Whether RAG retrieval was used")
    query: str = Field(..., description="Original query")
    classification: Optional[QueryClassificationSchema] = Field(
        default=None, description="Query classification")


class IngestionRequest(BaseModel):
    """Request model for ingestion endpoint."""

    file_path: str = Field(..., min_length=1,
                           description="Path to file to ingest")
    collection_name: str = Field(..., min_length=1,
                                 description="Collection name for storage")
    chunk_size: int = Field(default=512, ge=100,
                            description="Chunk size for text splitting")
    chunk_overlap: int = Field(
        default=50, ge=0, description="Overlap between chunks")


class IngestionResponse(BaseModel):
    """Response model for ingestion endpoint."""

    status: str = Field(...,
                        description="Status of ingestion (success/failure)")
    message: str = Field(..., description="Human-readable message")
    chunks_created: int = Field(..., ge=0,
                                description="Number of chunks created")
    collection_name: str = Field(...,
                                 description="Collection name where data was stored")


class DocumentMetadata(BaseModel):
    """Metadata about the source document."""

    filename: str = Field(..., min_length=1, description="Original filename")
    content_type: str = Field(...,
                              description="MIME type (e.g., application/pdf)")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    upload_timestamp: datetime = Field(...,
                                       description="UTC timestamp of upload")


class StorageInfo(BaseModel):
    """Cloud storage information for document location (supports GCS and S3)."""

    storage_uri: str = Field(..., pattern=r"^(gs|s3)://",
                            description="Storage URI (gs:// for GCS, s3:// for S3)")
    bucket: str = Field(..., min_length=1, description="Storage bucket name")
    object_path: str = Field(..., min_length=1,
                            description="Object path within bucket")


class ChunkMetadata(BaseModel):
    """Metadata about document chunk."""

    chunk_index: int = Field(..., ge=0, description="Chunk index (0-based)")
    total_chunks: int = Field(..., gt=0, description="Total number of chunks")
    chunk_text: str = Field(..., min_length=1,
                            description="Chunk text content")
    chunk_size: int = Field(..., gt=0, description="Chunk size in characters")
    chunk_overlap: int = Field(..., ge=0,
                               description="Overlap with adjacent chunks")

    @field_validator('chunk_index')
    @classmethod
    def validate_chunk_index(cls, v, info):
        """Ensure chunk_index is less than total_chunks."""
        if 'total_chunks' in info.data and v >= info.data['total_chunks']:
            raise ValueError('chunk_index must be less than total_chunks')
        return v


class ProcessingMetadata(BaseModel):
    """Metadata about document processing."""

    processing_timestamp: datetime = Field(...,
                                           description="Processing timestamp")
    embedding_model: str = Field(..., min_length=1,
                                 description="Embedding model name")
    embedding_dimension: int = Field(..., gt=0,
                                     description="Embedding vector dimension")
    chunk_strategy: str = Field(..., min_length=1,
                                description="Chunking strategy used")


class QdrantPayload(BaseModel):
    """Complete payload schema for Qdrant vector storage.

    This comprehensive payload replaces traditional database storage,
    co-locating all metadata alongside vector embeddings in Qdrant.
    """

    document: DocumentMetadata = Field(..., description="Document metadata")
    storage: StorageInfo = Field(..., description="Cloud storage information")
    chunk: ChunkMetadata = Field(..., description="Chunk metadata")
    processing: ProcessingMetadata = Field(...,
                                           description="Processing metadata")
    collection_id: str = Field(..., min_length=1,
                               description="Collection identifier")
    tags: list[str] = Field(default_factory=list,
                            description="Custom tags for filtering")


class UploadResponse(BaseModel):
    """Response model for file upload endpoint."""
    file_id: str = Field(..., description="Unique file identifier (UUID)")
    filename: str = Field(..., description="Original filename")
    storage_path: str = Field(..., description="Cloud storage path (gs:// or s3://)")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    mime_type: str = Field(..., description="MIME type (e.g., application/pdf)")
    uploaded_at: str = Field(..., description="Upload timestamp (ISO format)")


class IngestResponse(BaseModel):
    """Response model for async ingestion start (202 Accepted).
    """
    job_id: str = Field(..., description="Job identifier for tracking")
    status: str = Field(..., description="Initial job status (pending/processing)")
    message: str = Field(..., description="Human-readable status message")
    file_path: str = Field(..., description="Cloud storage path being processed (gs:// or s3://)")
    collection_name: str = Field(..., description="Target collection")


class IngestStatusResponse(BaseModel):
    """Response model for ingestion status endpoint.
    """
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current job status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    message: str = Field(..., description="Status message")
    file_path: str = Field(..., description="Cloud storage path being processed (gs:// or s3://)")
    collection_name: str = Field(..., description="Target collection")
    chunks_created: int = Field(default=0, ge=0, description="Number of chunks created")
    error: Optional[str] = Field(default=None, description="Error message if failed")
