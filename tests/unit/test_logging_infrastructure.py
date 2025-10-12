"""Unit tests for structured logging infrastructure."""

import pytest
from pathlib import Path
from unittest.mock import patch

from app.services.preprocessing.text import TextHandler


def test_handler_logs_processing_start(tmp_path):
    """Test that handlers log when processing starts."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    handler = TextHandler()

    with patch('app.services.preprocessing.text.logger') as mock_logger:
        handler.process(test_file)
        mock_logger.info.assert_called()
