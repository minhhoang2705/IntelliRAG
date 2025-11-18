"""Semantic chunking service using LangChain.

This module provides SemanticChunkerService which uses LangChain's
SemanticChunker for text splitting based on semantic meaning.


"""

import logging
import asyncio
from typing import List, Optional
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class EmbeddingAdapter(Embeddings):
    """Adapter to make EmbeddingService compatible with LangChain Embeddings interface."""

    def __init__(self, embedding_service):
        """Initialize adapter with embedding service.

        Args:
            embedding_service: EmbeddingService instance
        """
        self.embedding_service = embedding_service

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed list of documents synchronously.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return self.embedding_service.embed_batch(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed single query synchronously.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        return self.embedding_service.embed_single(text)


class SemanticChunkerService:
    """Service for semantic-based document chunking using LangChain."""

    def __init__(
        self,
        embeddings,
        breakpoint_type: str = "percentile"
    ):
        """Initialize semantic chunker service.

        Args:
            embeddings: Embedding service (will be adapted to LangChain interface)
            breakpoint_type: Breakpoint strategy ("percentile", "gradient", "interquartile", "standard_deviation")
        """
        # Adapt embedding service to LangChain interface
        self.embeddings = EmbeddingAdapter(embeddings)
        self.breakpoint_type = breakpoint_type

        # Initialize LangChain SemanticChunker
        self.chunker = SemanticChunker(
            embeddings=self.embeddings,
            breakpoint_threshold_type=breakpoint_type
        )

        logger.info(
            f"Initialized SemanticChunkerService with breakpoint_type={breakpoint_type}")

    async def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Chunk documents semantically.

        Args:
            documents: List of LangChain Document objects to chunk

        Returns:
            List of chunked Document objects with preserved metadata

        """
        if not documents:
            return []

        logger.info(f"Chunking {len(documents)} document(s) semantically")

        all_chunks = []

        for doc_idx, document in enumerate(documents):
            # Split the document text using semantic chunker
            loop = asyncio.get_event_loop()
            text_chunks = await loop.run_in_executor(
                None,
                self.chunker.split_text,
                document.page_content
            )

            # Create new Document objects for each chunk, preserving metadata
            for chunk_idx, chunk_text in enumerate(text_chunks):
                chunk_metadata = {
                    **document.metadata,  # Preserve original metadata
                    "chunk_index": chunk_idx,
                    "total_chunks": len(text_chunks),
                    "document_index": doc_idx
                }

                chunk_doc = Document(
                    page_content=chunk_text,
                    metadata=chunk_metadata
                )

                all_chunks.append(chunk_doc)

        logger.info(
            f"Created {len(all_chunks)} semantic chunks from {len(documents)} documents")

        return all_chunks
