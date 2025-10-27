"""Test QueryResponse with classification field.

Following TDD: This test will FAIL until we add classification to QueryResponse.
"""

import pytest


def test_query_response_accepts_classification():
    """Test that QueryResponse can include classification information."""
    from app.models.schemas import QueryResponse, QueryClassificationSchema
    from app.services.query_router.classifier import QueryType

    # Create classification
    classification = QueryClassificationSchema(
        query_type=QueryType.RAG,
        confidence=0.92,
        reasoning="Query requires document retrieval"
    )

    # This should work when we add classification field
    response = QueryResponse(
        answer="Python is a programming language",
        sources=[],
        used_rag=True,
        query="What is Python?",
        classification=classification
    )

    assert response.classification is not None
    assert response.classification.query_type == QueryType.RAG
