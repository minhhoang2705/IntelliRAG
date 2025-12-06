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

    @pytest.mark.unit
    def test_chunker_initializes_with_embedding_service(self, mock_embedding_service):
        """Test that chunker initializes with an embedding service."""
        from app.services.semantic_chunker import SemanticChunkerService

        # Use mocked embedding service
        chunker = SemanticChunkerService(embeddings=mock_embedding_service)

        assert chunker is not None
        assert hasattr(chunker, 'embeddings')

    @pytest.mark.unit
    def test_chunker_initializes_with_default_breakpoint_type(self, mock_embedding_service):
        """Test that chunker uses percentile breakpoint by default."""
        from app.services.semantic_chunker import SemanticChunkerService

        # Use mocked embedding service
        chunker = SemanticChunkerService(embeddings=mock_embedding_service)

        assert chunker.breakpoint_type == "percentile"


class TestDocumentChunking:
    """Test document chunking functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chunk_documents_returns_chunks(self, mock_embedding_service, mocker):
        """Test that chunking documents returns multiple smaller documents."""
        from app.services.semantic_chunker import SemanticChunkerService

        # Mock LangChain's SemanticChunker.split_text to return text chunks
        mock_langchain_chunker = mocker.Mock()
        mock_langchain_chunker.split_text.return_value = [
            "Chunk 1: AI and ML content",
            "Chunk 2: NLP content",
            "Chunk 3: Computer vision content",
        ]
        mocker.patch('app.services.semantic_chunker.SemanticChunker', return_value=mock_langchain_chunker)

        chunker = SemanticChunkerService(embeddings=mock_embedding_service)

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

        assert len(chunks) == 3  # Mock returns 3 chunks
        assert all(isinstance(chunk, Document) for chunk in chunks)
        mock_langchain_chunker.split_text.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chunk_preserves_metadata(self, mock_embedding_service, mocker):
        """Test that chunking preserves original document metadata."""
        from app.services.semantic_chunker import SemanticChunkerService

        # Mock to return text chunks (metadata is added by service)
        mock_langchain_chunker = mocker.Mock()
        mock_langchain_chunker.split_text.return_value = [
            "Chunk 1",
            "Chunk 2",
        ]
        mocker.patch('app.services.semantic_chunker.SemanticChunker', return_value=mock_langchain_chunker)

        chunker = SemanticChunkerService(embeddings=mock_embedding_service)

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

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chunk_adds_chunk_index(self, mock_embedding_service, mocker):
        """Test that chunks have index in metadata."""
        from app.services.semantic_chunker import SemanticChunkerService

        # Mock to return text chunks (chunk_index added by service)
        mock_langchain_chunker = mocker.Mock()
        mock_langchain_chunker.split_text.return_value = [
            "Section 1",
            "Section 2",
            "Section 3",
        ]
        mocker.patch('app.services.semantic_chunker.SemanticChunker', return_value=mock_langchain_chunker)

        chunker = SemanticChunkerService(embeddings=mock_embedding_service)

        text = "Section 1.\n\nSection 2.\n\nSection 3."
        documents = [Document(page_content=text)]

        chunks = await chunker.chunk_documents(documents)

        for i, chunk in enumerate(chunks):
            assert "chunk_index" in chunk.metadata
            assert chunk.metadata["chunk_index"] == i


class TestBreakpointStrategies:
    """Test different breakpoint threshold strategies."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_percentile_breakpoint_strategy(self, mock_embedding_service, mocker):
        """Test semantic chunking with percentile breakpoint."""
        from app.services.semantic_chunker import SemanticChunkerService

        # Mock LangChain chunker
        mock_langchain_chunker = mocker.Mock()
        mock_langchain_chunker.split_text.return_value = [
            "Topic A content",
            "Topic B content",
        ]
        mocker.patch('app.services.semantic_chunker.SemanticChunker', return_value=mock_langchain_chunker)

        chunker = SemanticChunkerService(
            embeddings=mock_embedding_service,
            breakpoint_type="percentile"
        )

        text = "Topic A content.\n\nTopic B content.\n\nTopic C content."
        documents = [Document(page_content=text)]

        chunks = await chunker.chunk_documents(documents)

        assert len(chunks) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_gradient_breakpoint_strategy(self, mock_embedding_service, mocker):
        """Test semantic chunking with gradient breakpoint."""
        from app.services.semantic_chunker import SemanticChunkerService

        # Mock LangChain chunker
        mock_langchain_chunker = mocker.Mock()
        mock_langchain_chunker.split_text.return_value = [
            "First topic here",
            "Second topic here",
        ]
        mocker.patch('app.services.semantic_chunker.SemanticChunker', return_value=mock_langchain_chunker)

        chunker = SemanticChunkerService(
            embeddings=mock_embedding_service,
            breakpoint_type="gradient"
        )

        text = "First topic here.\n\nSecond topic here.\n\nThird topic here."
        documents = [Document(page_content=text)]

        chunks = await chunker.chunk_documents(documents)

        assert len(chunks) == 2


class TestEdgeCases:
    """Test edge cases in chunking."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chunk_empty_documents(self, mock_embedding_service, mocker):
        """Test chunking empty documents list (no LangChain call needed)."""
        from app.services.semantic_chunker import SemanticChunkerService

        # Mock (won't be called for empty input)
        mock_langchain_chunker = mocker.Mock()
        mock_langchain_chunker.split_text.return_value = []
        mocker.patch('app.services.semantic_chunker.SemanticChunker', return_value=mock_langchain_chunker)

        chunker = SemanticChunkerService(embeddings=mock_embedding_service)

        chunks = await chunker.chunk_documents([])

        assert chunks == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_chunk_single_short_document(self, mock_embedding_service, mocker):
        """Test chunking a document shorter than typical chunk size."""
        from app.services.semantic_chunker import SemanticChunkerService

        short_text = "Just a short sentence."
        
        # Mock to return single chunk for short text
        mock_langchain_chunker = mocker.Mock()
        mock_langchain_chunker.split_text.return_value = [short_text]
        mocker.patch('app.services.semantic_chunker.SemanticChunker', return_value=mock_langchain_chunker)

        chunker = SemanticChunkerService(embeddings=mock_embedding_service)

        documents = [Document(page_content=short_text)]

        chunks = await chunker.chunk_documents(documents)

        # Short document returns single chunk
        assert len(chunks) == 1
        assert chunks[0].page_content == short_text
