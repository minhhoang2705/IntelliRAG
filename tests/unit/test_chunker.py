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
    assert all(len(chunk['text']) <= 60 for chunk in chunks)  # Allow some buffer


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
