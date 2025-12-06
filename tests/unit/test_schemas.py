"""Unit tests for Pydantic schemas (API request/response models).


Date: 2025-10-17
"""

import pytest


def test_query_request_valid():
    """Test valid query request with minimal fields."""
    from app.models.schemas import QueryRequest

    request = QueryRequest(query="What is Python?")

    assert request.query == "What is Python?"
    assert request.top_k == 5
    assert request.use_rag is True
    assert request.temperature == 0.7


def test_query_request_with_all_fields():
    """Test query request with all optional fields."""
    from app.models.schemas import QueryRequest

    request = QueryRequest(
        query="What is Python?",
        top_k=10,
        use_rag=False,
        temperature=0.9,
        max_tokens=500
    )

    assert request.query == "What is Python?"
    assert request.top_k == 10
    assert request.use_rag is False
    assert request.temperature == 0.9
    assert request.max_tokens == 500


def test_query_request_empty_query_fails():
    """Test that empty query string fails validation."""
    from app.models.schemas import QueryRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        QueryRequest(query="")

    errors = exc_info.value.errors()
    assert any("query" in str(err) for err in errors)


def test_source_document_valid():
    """Test valid source document."""
    from app.models.schemas import SourceDocument

    doc = SourceDocument(
        text="Python is a programming language",
        score=0.95,
        id="doc_1"
    )

    assert doc.text == "Python is a programming language"
    assert doc.score == 0.95
    assert doc.id == "doc_1"


def test_query_response_valid():
    """Test valid query response."""
    from app.models.schemas import QueryResponse

    response = QueryResponse(
        answer="Python is a programming language",
        sources=[
            {"text": "Python is...", "score": 0.95, "id": "doc_1"},
            {"text": "Python was...", "score": 0.87, "id": "doc_2"}
        ],
        used_rag=True,
        query="What is Python?"
    )

    assert response.answer == "Python is a programming language"
    assert len(response.sources) == 2
    assert response.used_rag is True
    assert response.query == "What is Python?"


def test_ingestion_request_valid():
    """Test valid ingestion request."""
    from app.models.schemas import IngestionRequest

    request = IngestionRequest(
        file_path="/path/to/document.pdf",
        collection_name="my_docs"
    )

    assert request.file_path == "/path/to/document.pdf"
    assert request.collection_name == "my_docs"
    assert request.chunk_size == 512
    assert request.chunk_overlap == 50


def test_ingestion_response_valid():
    """Test valid ingestion response."""
    from app.models.schemas import IngestionResponse

    response = IngestionResponse(
        status="success",
        message="Ingested 10 chunks",
        chunks_created=10,
        collection_name="my_docs"
    )

    assert response.status == "success"
    assert response.message == "Ingested 10 chunks"
    assert response.chunks_created == 10
    assert response.collection_name == "my_docs"
