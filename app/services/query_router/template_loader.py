"""Template loading service with language detection.

Provides Jinja2-based template rendering with automatic language detection
for Vietnamese/English RAG prompts.
"""
import logging
from pathlib import Path
from typing import Optional
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment
from app.services.query_router.language_detector import LanguageDetector

logger = logging.getLogger(__name__)

# Template directory path
TEMPLATES_DIR = Path(__file__).parent / "templates"


class TemplateLoader:
    """Loads and renders Jinja2 templates with language detection.

    Features:
    - Automatic language detection using LanguageDetector
    - Sandboxed Jinja2 environment for security
    - Custom filters for context formatting
    - Fallback to English for unsupported languages
    """

    SUPPORTED_LANGS = {"en", "vi"}

    def __init__(self, language_detector: Optional[LanguageDetector] = None):
        """Initialize template loader.

        Args:
            language_detector: Optional LanguageDetector instance.
                If None, creates new instance.
        """
        self.detector = language_detector or LanguageDetector()
        self.env = SandboxedEnvironment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True
        )
        self._register_filters()
        logger.info(f"Initialized TemplateLoader with templates from {TEMPLATES_DIR}")

    def _register_filters(self) -> None:
        """Register custom Jinja2 filters."""

        def format_context(texts: list) -> str:
            """Format list of texts as numbered context with separators.

            Args:
                texts: List of text strings

            Returns:
                Formatted string with [1], [2], [3] prefixes and separators

            Example:
                ["First", "Second"] -> "[1] First\n\n---\n\n[2] Second"
            """
            formatted = []
            counter = 1
            for text in texts:
                # Skip empty or None values
                if text:
                    formatted.append(f"[{counter}] {text}")
                    counter += 1

            return "\n\n---\n\n".join(formatted)

        self.env.filters['format_context'] = format_context

    def render(
        self,
        template_name: str,
        language: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs
    ) -> str:
        """Render template with automatic language detection.

        Args:
            template_name: Name of template file (e.g., "classification.j2")
            language: Optional language code override ("en" or "vi")
            query: Optional query text for auto-detection
            **kwargs: Additional template variables

        Returns:
            Rendered template string

        Raises:
            jinja2.TemplateNotFound: If template doesn't exist

        Example:
            >>> loader = TemplateLoader()
            >>> loader.render("test.j2", language="en", name="World")
            "Hello World"
        """
        # Auto-detect language if not provided
        if language is None and query:
            language = self.detector.detect_with_fallback(query)

        # Fallback to English for unsupported languages
        if language not in self.SUPPORTED_LANGS:
            logger.warning(
                f"Unsupported language '{language}', falling back to 'en'"
            )
            language = "en"

        # Build template path: {lang}/{template_name}
        template_path = f"{language}/{template_name}"
        logger.debug(f"Rendering template: {template_path}")

        # Load and render template
        template = self.env.get_template(template_path)
        return template.render(query=query, **kwargs)
