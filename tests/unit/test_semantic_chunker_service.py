"""Unit tests for SemanticChunkerService using LangChain.

This module tests the SemanticChunkerService which uses LangChain's
SemanticChunker for intelligent text splitting based on meaning.

Following TDD methodology - batch per service approach.

Date: 2025-10-25
"""

import pytest
from langchain_core.documents import Document


class TestSemanticChunkerInitialization:
    """Test SemanticChunkerService initialization."""

    def test_chunker_initializes_with_embedding_service(self):
        """Test that chunker initializes with an embedding service."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(embeddings=embeddings)

        assert chunker is not None
        assert hasattr(chunker, 'embeddings')

    def test_chunker_initializes_with_default_breakpoint_type(self):
        """Test that chunker uses percentile breakpoint by default."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(embeddings=embeddings)

        assert chunker.breakpoint_type == "percentile"


class TestDocumentChunking:
    """Test document chunking functionality."""

    @pytest.mark.asyncio
    async def test_chunk_documents_returns_chunks(self):
        """Test that chunking documents returns multiple smaller documents."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(embeddings=embeddings)

        long_text = """
        This is the first paragraph about artificial intelligence.
        It discusses machine learning and neural networks.

        This is the second paragraph about natural language processing.
        It covers tokenization and semantic understanding.

        This is the third paragraph about computer vision.
        It explains image recognition and object detection.
        """

        documents = [Document(page_content=long_text, metadata={"source": "test"})]

        chunks = await chunker.chunk_documents(documents)

        assert len(chunks) > 1
        assert all(isinstance(chunk, Document) for chunk in chunks)
        assert all(len(chunk.page_content) < len(long_text) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_chunk_preserves_metadata(self):
        """Test that chunking preserves original document metadata."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(embeddings=embeddings)

        text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        documents = [Document(
            page_content=text,
            metadata={"source": "test.txt", "author": "TestUser"}
        )]

        chunks = await chunker.chunk_documents(documents)

        for chunk in chunks:
            assert "source" in chunk.metadata
            assert chunk.metadata["source"] == "test.txt"
            assert chunk.metadata["author"] == "TestUser"

    @pytest.mark.asyncio
    async def test_chunk_adds_chunk_index(self):
        """Test that chunks have index in metadata."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(embeddings=embeddings)

        text = "Section 1.\n\nSection 2.\n\nSection 3."
        documents = [Document(page_content=text)]

        chunks = await chunker.chunk_documents(documents)

        for i, chunk in enumerate(chunks):
            assert "chunk_index" in chunk.metadata
            assert chunk.metadata["chunk_index"] == i


class TestBreakpointStrategies:
    """Test different breakpoint threshold strategies."""

    @pytest.mark.asyncio
    async def test_percentile_breakpoint_strategy(self):
        """Test semantic chunking with percentile breakpoint."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(
            embeddings=embeddings,
            breakpoint_type="percentile"
        )

        text = "Topic A content.\n\nTopic B content.\n\nTopic C content."
        documents = [Document(page_content=text)]

        chunks = await chunker.chunk_documents(documents)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_gradient_breakpoint_strategy(self):
        """Test semantic chunking with gradient breakpoint."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(
            embeddings=embeddings,
            breakpoint_type="gradient"
        )

        text = "First topic here.\n\nSecond topic here.\n\nThird topic here."
        documents = [Document(page_content=text)]

        chunks = await chunker.chunk_documents(documents)

        assert len(chunks) > 0


class TestEdgeCases:
    """Test edge cases in chunking."""

    @pytest.mark.asyncio
    async def test_chunk_empty_documents(self):
        """Test chunking empty documents list."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(embeddings=embeddings)

        chunks = await chunker.chunk_documents([])

        assert chunks == []

    @pytest.mark.asyncio
    async def test_chunk_single_short_document(self):
        """Test chunking a document shorter than typical chunk size."""
        from app.services.semantic_chunker import SemanticChunkerService
        from app.services.embedding import EmbeddingService

        embeddings = EmbeddingService()
        chunker = SemanticChunkerService(embeddings=embeddings)

        short_text = "Just a short sentence."
        documents = [Document(page_content=short_text)]

        chunks = await chunker.chunk_documents(documents)

        # Short document might return single chunk
        assert len(chunks) >= 1
        assert chunks[0].page_content == short_text
