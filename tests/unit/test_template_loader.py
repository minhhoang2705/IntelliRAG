"""Unit tests for TemplateLoader service.

Tests Jinja2 template loading with language detection integration.
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from app.services.query_router.template_loader import TemplateLoader
from app.services.query_router.language_detector import LanguageDetector


class TestTemplateLoader:
    """Test suite for template loading functionality."""

    @pytest.fixture
    def mock_detector(self):
        """Create mock LanguageDetector for testing."""
        detector = Mock(spec=LanguageDetector)
        detector.detect_with_fallback.return_value = "en"
        return detector

    @pytest.fixture
    def loader(self, mock_detector):
        """Create TemplateLoader instance with mock detector."""
        return TemplateLoader(language_detector=mock_detector)

    def test_render_english_template(self, loader, tmp_path):
        """Should render English template with provided variables."""
        # This test will fail first because TemplateLoader doesn't exist yet
        # Create temporary template for testing
        en_dir = tmp_path / "en"
        en_dir.mkdir()
        template_file = en_dir / "test.j2"
        template_file.write_text("Hello {{ name }}")

        # Patch TEMPLATES_DIR to use tmp_path
        with patch('app.services.query_router.template_loader.TEMPLATES_DIR', tmp_path):
            loader_temp = TemplateLoader(language_detector=loader.detector)
            result = loader_temp.render(
                template_name="test.j2",
                language="en",
                name="World"
            )

        assert result == "Hello World", f"Expected 'Hello World' but got '{result}'"

    def test_render_vietnamese_template(self, loader, tmp_path):
        """Should render Vietnamese template with provided variables."""
        # Create temporary Vietnamese template
        vi_dir = tmp_path / "vi"
        vi_dir.mkdir()
        template_file = vi_dir / "test.j2"
        template_file.write_text("Xin chao {{ name }}")

        with patch('app.services.query_router.template_loader.TEMPLATES_DIR', tmp_path):
            loader_temp = TemplateLoader(language_detector=loader.detector)
            result = loader_temp.render(
                template_name="test.j2",
                language="vi",
                name="Vietnam"
            )

        assert result == "Xin chao Vietnam", f"Expected 'Xin chao Vietnam' but got '{result}'"

    def test_auto_language_detection(self, loader, tmp_path):
        """Should auto-detect language when not explicitly provided."""
        # Setup mock to return Vietnamese
        loader.detector.detect_with_fallback.return_value = "vi"

        # Create templates
        for lang in ["en", "vi"]:
            lang_dir = tmp_path / lang
            lang_dir.mkdir()
            template_file = lang_dir / "test.j2"
            template_file.write_text(f"Template: {lang}")

        with patch('app.services.query_router.template_loader.TEMPLATES_DIR', tmp_path):
            loader_temp = TemplateLoader(language_detector=loader.detector)
            result = loader_temp.render(
                template_name="test.j2",
                query="Doanh thu la bao nhieu?"
            )

        # Should use detected language (vi)
        assert "vi" in result, f"Expected Vietnamese template but got '{result}'"
        loader.detector.detect_with_fallback.assert_called_once()

    def test_fallback_to_english(self, loader, tmp_path):
        """Should fallback to English for unsupported languages."""
        # Create only English template
        en_dir = tmp_path / "en"
        en_dir.mkdir()
        template_file = en_dir / "test.j2"
        template_file.write_text("English template")

        with patch('app.services.query_router.template_loader.TEMPLATES_DIR', tmp_path):
            loader_temp = TemplateLoader(language_detector=loader.detector)
            # Try to render with unsupported language
            result = loader_temp.render(
                template_name="test.j2",
                language="fr",  # French not supported
                query="test"
            )

        assert result == "English template", "Should fallback to English"

    def test_format_context_filter(self, loader, tmp_path):
        """Should format context list with filter."""
        # Create template using format_context filter
        en_dir = tmp_path / "en"
        en_dir.mkdir()
        template_file = en_dir / "test.j2"
        template_file.write_text("{{ context | format_context }}")

        with patch('app.services.query_router.template_loader.TEMPLATES_DIR', tmp_path):
            loader_temp = TemplateLoader(language_detector=loader.detector)
            result = loader_temp.render(
                template_name="test.j2",
                language="en",
                context=["First doc", "Second doc", "Third doc"]
            )

        # Should format with numbered citations
        assert "[1] First doc" in result, "Should include first doc with [1]"
        assert "[2] Second doc" in result, "Should include second doc with [2]"
        assert "[3] Third doc" in result, "Should include third doc with [3]"
        assert "---" in result, "Should include separator between docs"

    def test_format_context_filter_skips_empty(self, loader, tmp_path):
        """Should skip empty strings in context formatting."""
        en_dir = tmp_path / "en"
        en_dir.mkdir()
        template_file = en_dir / "test.j2"
        template_file.write_text("{{ context | format_context }}")

        with patch('app.services.query_router.template_loader.TEMPLATES_DIR', tmp_path):
            loader_temp = TemplateLoader(language_detector=loader.detector)
            result = loader_temp.render(
                template_name="test.j2",
                language="en",
                context=["First", "", "Third", None]
            )

        # Should skip empty/None values
        assert "[1] First" in result
        assert "[2] Third" in result
        assert "None" not in result

    def test_sandboxed_environment(self, loader):
        """Should use SandboxedEnvironment for security."""
        # TemplateLoader should use SandboxedEnvironment
        from jinja2.sandbox import SandboxedEnvironment
        assert isinstance(loader.env, SandboxedEnvironment), \
            "Should use SandboxedEnvironment for security"

    def test_autoescape_enabled(self, loader):
        """Should have autoescape enabled for XSS protection."""
        assert loader.env.autoescape is True, \
            "Autoescape should be enabled for security"

    def test_supported_languages(self):
        """Should support only en and vi languages."""
        # TemplateLoader should define SUPPORTED_LANGS
        assert hasattr(TemplateLoader, 'SUPPORTED_LANGS'), \
            "Should define SUPPORTED_LANGS"
        assert TemplateLoader.SUPPORTED_LANGS == {"en", "vi"}, \
            "Should support only en and vi"
