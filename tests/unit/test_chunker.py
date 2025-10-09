"""Tests for the DocumentChunker class."""

import pytest


def test_document_chunker_exists():
    """Test that DocumentChunker class exists."""
    from app.services.preprocessing.chunker import DocumentChunker

    assert DocumentChunker is not None


def test_document_chunker_can_be_instantiated():
    """Test that DocumentChunker can be instantiated."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker()
    assert chunker is not None


def test_document_chunker_has_default_parameters():
    """Test that DocumentChunker has default chunking parameters."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker()
    assert hasattr(chunker, 'chunk_size')
    assert hasattr(chunker, 'chunk_overlap')
    assert chunker.chunk_size == 512  # Default chunk size
    assert chunker.chunk_overlap == 100  # Default overlap


def test_document_chunker_accepts_custom_parameters():
    """Test that DocumentChunker accepts custom parameters."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)
    assert chunker.chunk_size == 1000
    assert chunker.chunk_overlap == 200


def test_document_chunker_has_chunk_text_method():
    """Test that DocumentChunker has a chunk_text method."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker()
    assert hasattr(chunker, 'chunk_text')
    assert callable(chunker.chunk_text)


def test_document_chunker_chunks_simple_text():
    """Test basic text chunking functionality."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
    text = "This is a simple text. " * 10  # ~230 characters

    chunks = chunker.chunk_text(text)

    assert isinstance(chunks, list)
    assert len(chunks) > 1
    assert all(isinstance(chunk, dict) for chunk in chunks)
    assert all('text' in chunk for chunk in chunks)
    assert all('metadata' in chunk for chunk in chunks)
    # Allow some buffer
    assert all(len(chunk['text']) <= 60 for chunk in chunks)


def test_document_chunker_preserves_metadata():
    """Test that chunker preserves document metadata."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)
    text = "This is a test document. " * 10
    metadata = {"source": "test.txt", "author": "Test Author"}

    chunks = chunker.chunk_text(text, metadata=metadata)

    for i, chunk in enumerate(chunks):
        assert chunk['metadata']['source'] == "test.txt"
        assert chunk['metadata']['author'] == "Test Author"
        assert chunk['metadata']['chunk_index'] == i
        assert 'start_position' in chunk['metadata']
        assert 'end_position' in chunk['metadata']


def test_document_chunker_handles_empty_text():
    """Test that chunker handles empty text gracefully."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker()

    # Test empty string
    chunks = chunker.chunk_text("")
    assert chunks == []

    # Test None
    chunks = chunker.chunk_text(None)
    assert chunks == []


def test_document_chunker_handles_small_text():
    """Test that chunker handles text smaller than chunk_size."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker(chunk_size=1000, chunk_overlap=100)
    small_text = "This is a small text."

    chunks = chunker.chunk_text(small_text)

    assert len(chunks) == 1
    assert chunks[0]['text'] == small_text
    assert chunks[0]['metadata']['chunk_index'] == 0


def test_document_chunker_accepts_chunker_type_parameter():
    """Test that DocumentChunker accepts chunker_type parameter."""
    from app.services.preprocessing.chunker import DocumentChunker

    # Test langchain type (default)
    chunker = DocumentChunker(chunker_type="langchain")
    assert chunker.chunker_type == "langchain"


def test_document_chunker_accepts_model_id_parameter():
    """Test that DocumentChunker accepts model_id for tokenizer configuration."""
    from app.services.preprocessing.chunker import DocumentChunker

    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    chunker = DocumentChunker(model_id=model_id)
    assert chunker.model_id == model_id


def test_document_chunker_hybrid_type_can_be_instantiated():
    """Test that hybrid chunker can be instantiated without errors."""
    from app.services.preprocessing.chunker import DocumentChunker

    # Should not raise any errors even if Docling deps are missing (fallback to langchain)
    chunker = DocumentChunker(chunker_type="hybrid")
    assert chunker is not None
    assert chunker.chunker_type == "hybrid"


def test_document_chunker_hybrid_type_chunks_text():
    """Test that hybrid chunker successfully chunks text."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker(chunker_type="hybrid",
                              chunk_size=100, chunk_overlap=20)
    text = "This is a test document. " * 10  # ~250 characters

    chunks = chunker.chunk_text(text)

    # Should successfully chunk text
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all('text' in chunk for chunk in chunks)
    assert all('metadata' in chunk for chunk in chunks)


def test_document_chunker_hybrid_uses_token_based_chunking():
    """Test that hybrid chunker uses token-based chunking from Docling HybridChunker."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker(chunker_type="hybrid",
                              chunk_size=50, chunk_overlap=10)

    # Verify the chunker has a tokenizer (unique to HybridChunker)
    assert hasattr(
        chunker, 'tokenizer'), "Hybrid chunker should have a tokenizer attribute"
    assert chunker.tokenizer is not None, "Tokenizer should be initialized for hybrid chunker"


def test_document_chunker_hybrid_uses_docling_hybrid_chunker():
    """Test that hybrid chunker actually uses Docling's HybridChunker for splitting."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker(chunker_type="hybrid",
                              chunk_size=50, chunk_overlap=10)

    # Verify the splitter is a Docling HybridChunker, not LangChain
    assert hasattr(chunker, 'splitter'), "Chunker should have a splitter"

    # Check the splitter type - should be HybridChunker from Docling
    splitter_class_name = chunker.splitter.__class__.__name__
    assert splitter_class_name == "HybridChunker", f"Expected HybridChunker but got {splitter_class_name}"
def test_hybrid_chunker_length_function_uses_tokenizer():
    """Test that HybridChunker's length_function uses tokenizer to count tokens."""
    from app.services.preprocessing.chunker import DocumentChunker

    # Create hybrid chunker
    chunker = DocumentChunker(chunker_type="hybrid", chunk_size=50, chunk_overlap=10)

    # Test text
    test_text = "This is a test string for tokenization."

    # Access the length function from the splitter
    length_func = chunker.splitter._length_function

    # Calculate length using the chunker's length function
    calculated_length = length_func(test_text)

    # Calculate expected token count using tokenizer
    expected_token_count = len(chunker.tokenizer.encode(test_text))

    # The length function MUST return token count, not character count
    assert calculated_length == expected_token_count, \
        f"Length function returned {calculated_length}, but tokenizer gives {expected_token_count} tokens"
