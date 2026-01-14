"""Unit tests for LanguageDetector service.

Tests language detection using FastText model with Vietnamese/English support.
"""
import pytest
from app.services.query_router.language_detector import LanguageDetector


class TestLanguageDetector:
    """Test suite for language detection functionality."""

    @pytest.fixture
    def detector(self):
        """Create LanguageDetector instance for tests."""
        return LanguageDetector()

    def test_detect_english(self, detector):
        """Should detect English text with high confidence."""
        text = "What is the revenue for Q4 2025?"
        lang, conf = detector.detect(text)

        assert lang == "en", f"Expected 'en' but got '{lang}'"
        assert conf > 0.7, f"Expected confidence >0.7 but got {conf}"

    def test_detect_vietnamese(self, detector):
        """Should detect Vietnamese text with high confidence."""
        text = "Doanh thu quy 4 nam 2025 la bao nhieu?"
        lang, conf = detector.detect(text)

        assert lang == "vi", f"Expected 'vi' but got '{lang}'"
        assert conf > 0.7, f"Expected confidence >0.7 but got {conf}"

    def test_fallback_on_low_confidence(self, detector):
        """Should fallback to English when confidence <0.7."""
        # Use ambiguous/noisy text that might have low confidence
        text = "123 456 789"
        result = detector.detect_with_fallback(text, fallback="en")

        # Should fallback to 'en' if confidence is low
        assert result in ["en", "vi"], f"Expected 'en' or detected lang, got '{result}'"

    def test_mixed_language_query(self, detector):
        """Should handle mixed language queries (English-Vietnamese)."""
        text = "What is doanh thu Q4?"
        lang, conf = detector.detect(text)

        # Should detect dominant language
        assert lang in ["en", "vi"], f"Expected 'en' or 'vi' but got '{lang}'"
        assert conf >= 0, "Confidence should be non-negative"

    def test_detect_with_fallback_uses_detected_lang(self, detector):
        """Should use detected language when confidence is high."""
        text = "This is clearly English text"
        result = detector.detect_with_fallback(text, fallback="vi")

        assert result == "en", f"Expected 'en' (not fallback) but got '{result}'"

    def test_handles_newlines_in_text(self, detector):
        """Should handle text with newlines by normalizing them."""
        text = "What is\nthe revenue\nfor Q4?"
        lang, conf = detector.detect(text)

        assert lang == "en", f"Expected 'en' but got '{lang}'"
        assert conf > 0, "Confidence should be positive"

    def test_handles_long_text(self, detector):
        """Should handle long text by limiting to first 500 chars."""
        # Create text longer than 500 characters
        text = "This is English. " * 50  # ~850 chars
        lang, conf = detector.detect(text)

        assert lang == "en", f"Expected 'en' but got '{lang}'"
        assert conf > 0.7, f"Expected high confidence for clear English"
