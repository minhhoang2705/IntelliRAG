"""Integration test data fixtures.

This module provides sample data for integration testing of EmbeddingService,
VectorDBService, and end-to-end workflows.

Author: IntelliRAG Team
Date: 2025-10-17
"""

# Sample texts for basic embedding tests
SAMPLE_TEXTS = [
    "Python is a high-level programming language.",
    "Machine learning enables computers to learn from data.",
    "Vector databases store high-dimensional embeddings.",
    "Natural language processing helps computers understand text.",
    "Deep learning uses neural networks with multiple layers.",
]

# Sample documents with metadata for vector storage tests
SAMPLE_DOCUMENTS = [
    {
        "id": "doc_1",
        "text": "Python is a versatile programming language used for web development, data science, and automation.",
        "metadata": {"category": "programming", "language": "en"}
    },
    {
        "id": "doc_2",
        "text": "Vector databases like Qdrant enable semantic search through similarity comparisons.",
        "metadata": {"category": "databases", "language": "en"}
    },
    {
        "id": "doc_3",
        "text": "Embedding models convert text into numerical vectors for machine learning.",
        "metadata": {"category": "ai", "language": "en"}
    },
]

# Multilingual test samples
MULTILINGUAL_SAMPLES = {
    'en': "Hello world",
    'fr': "Bonjour le monde",
    'es': "Hola mundo",
    'vi': "Xin chào thế giới",
    'de': "Hallo Welt",
    'zh': "你好世界",
    'ja': "こんにちは世界",
}

# Query samples for semantic search testing
QUERY_SAMPLES = [
    {
        "query": "Tell me about programming languages",
        "expected_doc": "doc_1",
        "description": "Should match Python programming document"
    },
    {
        "query": "How do vector databases work?",
        "expected_doc": "doc_2",
        "description": "Should match vector database document"
    },
    {
        "query": "What are embeddings in AI?",
        "expected_doc": "doc_3",
        "description": "Should match embedding models document"
    },
]
