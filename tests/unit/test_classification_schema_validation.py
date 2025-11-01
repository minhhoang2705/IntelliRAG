"""Test QueryClassificationSchema validation rules."""

import pytest
from pydantic import ValidationError


def test_classification_confidence_must_be_between_0_and_1():
    """Test confidence must be in range [0.0, 1.0]."""
    from app.models.schemas import QueryClassificationSchema
    from app.services.query_router.classifier import QueryType
    
    # Valid confidence values should work
    valid_classification = QueryClassificationSchema(
        query_type=QueryType.RAG,
        confidence=0.5,
        reasoning="Test"
    )
    assert valid_classification.confidence == 0.5
    
    # Confidence > 1.0 should fail
    with pytest.raises(ValidationError) as exc_info:
        QueryClassificationSchema(
            query_type=QueryType.RAG,
            confidence=1.5,
            reasoning="Test"
        )
    
    errors = exc_info.value.errors()
    assert any("confidence" in str(err) for err in errors)


def test_classification_reasoning_cannot_be_empty():
    """Test reasoning must not be empty string."""
    from app.models.schemas import QueryClassificationSchema
    from app.services.query_router.classifier import QueryType
    from pydantic import ValidationError
    
    # Empty reasoning should fail
    with pytest.raises(ValidationError) as exc_info:
        QueryClassificationSchema(
            query_type=QueryType.RAG,
            confidence=0.9,
            reasoning=""
        )
    
    errors = exc_info.value.errors()
    assert any("reasoning" in str(err) for err in errors)
