"""Tests for the BaseHandler abstract class."""

import pytest
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


def test_base_handler_is_abstract():
    """Test that BaseHandler cannot be instantiated directly."""
    from app.services.preprocessing.base import BaseHandler

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseHandler()


def test_base_handler_has_required_abstract_methods():
    """Test that BaseHandler defines the required abstract methods."""
    from app.services.preprocessing.base import BaseHandler

    # Check that BaseHandler has the required abstract methods
    assert hasattr(BaseHandler, 'validate')
    assert hasattr(BaseHandler, 'process')
    assert hasattr(BaseHandler, 'extract_text')

    # Check that these methods are abstract
    assert getattr(BaseHandler.validate, '__isabstractmethod__', False)
    assert getattr(BaseHandler.process, '__isabstractmethod__', False)
    assert getattr(BaseHandler.extract_text, '__isabstractmethod__', False)


def test_base_handler_concrete_subclass():
    """Test that a concrete subclass can be created and instantiated."""
    from app.services.preprocessing.base import BaseHandler

    class ConcreteHandler(BaseHandler):
        def validate(self, file_path: Path) -> bool:
            return True

        def process(self, file_path: Path, **kwargs) -> Dict[str, Any]:
            return {"status": "processed"}

        def extract_text(self, file_path: Path) -> str:
            return "extracted text"

    # Should be able to instantiate the concrete class
    handler = ConcreteHandler()
    assert handler is not None

    # Test that methods work
    test_path = Path("test.txt")
    assert handler.validate(test_path) is True
    assert handler.process(test_path) == {"status": "processed"}
    assert handler.extract_text(test_path) == "extracted text"


def test_base_handler_has_chunk_text_method():
    """Test that BaseHandler provides a chunk_text method."""
    from app.services.preprocessing.base import BaseHandler

    class ConcreteHandler(BaseHandler):
        def validate(self, file_path: Path) -> bool:
            return True

        def process(self, file_path: Path, **kwargs) -> Dict[str, Any]:
            return {"status": "processed"}

        def extract_text(self, file_path: Path) -> str:
            return "extracted text"

    handler = ConcreteHandler()

    # Test chunking functionality
    text = "This is a test. " * 10  # Create text with multiple sentences
    chunks = handler.chunk_text(text, chunk_size=50, overlap=10)

    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)


def test_base_handler_has_metadata_extraction():
    """Test that BaseHandler supports metadata extraction."""
    from app.services.preprocessing.base import BaseHandler

    class ConcreteHandler(BaseHandler):
        def validate(self, file_path: Path) -> bool:
            return True

        def process(self, file_path: Path, **kwargs) -> Dict[str, Any]:
            metadata = self.extract_metadata(file_path)
            return {
                "text": "content",
                "metadata": metadata
            }

        def extract_text(self, file_path: Path) -> str:
            return "extracted text"

        def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
            return {
                "filename": file_path.name,
                "size": 1024,
                "type": "text"
            }

    handler = ConcreteHandler()
    test_path = Path("test.txt")
    result = handler.process(test_path)

    assert "metadata" in result
    assert result["metadata"]["filename"] == "test.txt"
    assert result["metadata"]["size"] == 1024
    assert result["metadata"]["type"] == "text"