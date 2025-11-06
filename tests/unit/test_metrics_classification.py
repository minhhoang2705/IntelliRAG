"""Unit tests for Prometheus metrics in QueryClassifier.

This module tests that classification metrics are properly recorded.

Date: 2025-11-06
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import time


class TestClassificationMetrics:
    """Test suite for query classification metrics."""

    @pytest.mark.asyncio
    async def test_classification_records_metrics(self):
        """Test that classify method records Prometheus metrics."""
        # RED: Will fail because metrics not recorded
        from app.services.query_router.classifier import QueryClassifier

        # Create classifier with mocked LLM
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = '''
        {
            "query_type": "rag",
            "needs_rag": true,
            "confidence": 0.95,
            "reasoning": "This is a factual question requiring retrieval"
        }
        '''

        classifier = QueryClassifier(llm_client=mock_llm)

        # Mock metrics to verify they're called
        with patch('app.services.query_router.classifier.query_classification_total') as mock_total, \
             patch('app.services.query_router.classifier.query_classification_confidence') as mock_confidence, \
             patch('app.services.query_router.classifier.query_classification_duration_seconds') as mock_duration:

            # Call classify
            result = await classifier.classify("What is machine learning?")

            # Verify metrics were recorded
            # Check counter was incremented with correct label
            mock_total.labels.assert_called_once_with(query_type='rag')
            mock_total.labels.return_value.inc.assert_called_once()

            # Check confidence histogram was observed
            mock_confidence.observe.assert_called_once_with(0.95)

            # Check duration histogram was observed
            mock_duration.observe.assert_called_once()
            # Verify observe was called with a float (duration)
            assert isinstance(mock_duration.observe.call_args[0][0], float)
