"""Test QueryClassifier metrics instrumentation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_classifier_records_classification_metric():
    """Test classifier records total classifications."""
    from app.services.query_router.classifier import QueryClassifier, QueryType
    from app.api.middleware.metrics import query_classification_total
    
    # Create classifier with mocked LLM
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value='{"query_type": "rag", "confidence": 0.92, "reasoning": "Test"}')
    
    classifier = QueryClassifier(llm_client=mock_llm)
    
    # Get initial metric value
    initial_count = query_classification_total.labels(query_type='rag')._value._value
    
    # Classify query
    await classifier.classify("What is Python?")
    
    # Verify metric increased
    final_count = query_classification_total.labels(query_type='rag')._value._value
    assert final_count > initial_count


@pytest.mark.asyncio
async def test_classifier_records_confidence_metric():
    """Test classifier records confidence scores."""
    from app.services.query_router.classifier import QueryClassifier
    from app.api.middleware.metrics import query_classification_confidence
    
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value='{"query_type": "direct", "confidence": 0.85, "reasoning": "Test"}')
    
    classifier = QueryClassifier(llm_client=mock_llm)
    
    # Get initial sample count
    initial_count = query_classification_confidence._sum._value
    
    # Classify query
    await classifier.classify("What is 2+2?")
    
    # Verify confidence was recorded
    final_count = query_classification_confidence._sum._value
    assert final_count > initial_count


@pytest.mark.asyncio
async def test_classifier_records_duration_metric():
    """Test classifier records classification duration."""
    from app.services.query_router.classifier import QueryClassifier
    from app.api.middleware.metrics import query_classification_duration_seconds
    
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value='{"query_type": "rag", "confidence": 0.9, "reasoning": "Test"}')
    
    classifier = QueryClassifier(llm_client=mock_llm)
    
    # Get initial count
    initial_count = query_classification_duration_seconds._count._value
    
    # Classify query
    await classifier.classify("Test query")
    
    # Verify duration was recorded
    final_count = query_classification_duration_seconds._count._value
    assert final_count > initial_count
