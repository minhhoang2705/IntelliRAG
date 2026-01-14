"""Language detection service using langdetect.

NOTE: Originally planned to use FastText (120k sentences/s), but FastText has
NumPy 2.0 compatibility issues. Using langdetect as interim solution.
Migration to FastText planned when upstream fixes NumPy compatibility.

langdetect provides good accuracy with simple API, no model download needed.
"""
import logging
from typing import Tuple
from langdetect import detect, detect_langs, LangDetectException

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Language detection using langdetect library.

    Why langdetect (temporary)?
    - No NumPy 2.0 compatibility issues (FastText has breaking changes)
    - Simple API, no model download required
    - Good accuracy for Vietnamese/English detection
    - 55+ languages supported

    Future migration to FastText:
    - When fasttext fixes NumPy 2.0 compatibility
    - FastText provides 120k sentences/s (vs langdetect ~100 sentences/s)
    - 176 languages vs 55 languages
    """

    def __init__(self):
        """Initialize detector - langdetect requires no setup."""
        logger.info("Language detector initialized (using langdetect)")

    def _set_seed(self) -> None:
        """Set seed for consistent detection results.

        langdetect uses randomization internally. Not needed for production
        but useful for testing consistency.
        """
        import random
        from langdetect import DetectorFactory
        DetectorFactory.seed = 0

    def detect(self, text: str) -> Tuple[str, float]:
        """Detect language of text.

        Args:
            text: Input text to detect language

        Returns:
            Tuple of (language_code, confidence)
            - language_code: ISO 639-1 code (e.g., "en", "vi")
            - confidence: Float between 0 and 1

        Example:
            >>> detector = LanguageDetector()
            >>> lang, conf = detector.detect("Hello world")
            >>> print(f"{lang}: {conf:.2f}")  # "en: 0.95"
        """
        # Normalize newlines to spaces
        cleaned = text.replace('\n', ' ').strip()

        # Limit to 500 chars for speed
        if len(cleaned) > 500:
            cleaned = cleaned[:500]

        if not cleaned:
            logger.warning("Empty text provided for detection, defaulting to 'en'")
            return "en", 0.0

        try:
            # Get language probabilities
            lang_probs = detect_langs(cleaned)

            # langdetect returns list of Language objects sorted by probability
            # Get top prediction
            top_lang = lang_probs[0]
            lang_code = top_lang.lang
            confidence = float(top_lang.prob)

            logger.debug(f"Detected language: {lang_code} (confidence: {confidence:.2f})")
            return lang_code, confidence

        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}, defaulting to 'en'")
            return "en", 0.0

    def detect_with_fallback(
        self,
        text: str,
        fallback: str = "en"
    ) -> str:
        """Detect language with fallback for low confidence.

        Args:
            text: Input text to detect
            fallback: Language code to return if confidence <0.7

        Returns:
            Language code (detected or fallback)

        Why 0.7 threshold?
        - Validated during research: balances accuracy vs false positives
        - Below 0.7: often mixed-language or ambiguous input
        - Fallback to English maintains user experience

        Example:
            >>> detector.detect_with_fallback("123 456")  # Low confidence
            "en"  # Fallback to English
        """
        lang_code, confidence = self.detect(text)

        if confidence < 0.7:
            logger.info(
                f"Low confidence ({confidence:.2f}) for detected language '{lang_code}', "
                f"using fallback '{fallback}'"
            )
            return fallback

        return lang_code
