"""Test QueryClassificationSchema has required fields."""

import pytest


def test_classification_schema_has_confidence_field():
    """Test QueryClassificationSchema requires confidence field."""
    from app.models.schemas import QueryClassificationSchema
    from app.services.query_router.classifier import QueryType
    
    classification = QueryClassificationSchema(
        query_type=QueryType.RAG,
        confidence=0.92,
        reasoning="Test"
    )
    
    # This will fail if confidence field doesn't exist
    assert hasattr(classification, 'confidence')
    assert classification.confidence == 0.92


def test_classification_schema_has_reasoning_field():
    """Test QueryClassificationSchema requires reasoning field."""
    from app.models.schemas import QueryClassificationSchema
    from app.services.query_router.classifier import QueryType
    
    classification = QueryClassificationSchema(
        query_type=QueryType.RAG,
        confidence=0.92,
        reasoning="Query requires document retrieval"
    )
    
    # This will fail if reasoning field doesn't exist
    assert hasattr(classification, 'reasoning')
    assert classification.reasoning == "Query requires document retrieval"
