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
