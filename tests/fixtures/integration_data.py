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


# RAG-specific test queries with expected characteristics
RAG_TEST_QUERIES = [
    {
        "query": "What is machine learning?",
        "expected_keywords": ["machine learning", "learn", "data"],
        "use_rag": True,
        "description": "Factual question requiring document retrieval"
    },
    {
        "query": "Explain deep learning",
        "expected_keywords": ["deep", "learning", "neural"],
        "use_rag": True,
        "description": "Technical question about AI concepts"
    },
    {
        "query": "Hello, how are you?",
        "expected_keywords": [],
        "use_rag": False,
        "description": "Conversational query not requiring RAG"
    },
]

# Technical documentation samples for RAG testing
TECHNICAL_DOCS = [
    {
        "id": "ml_1",
        "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves.",
        "metadata": {"category": "ml_basics", "language": "en", "topic": "machine_learning"}
    },
    {
        "id": "ml_2",
        "text": "Deep learning is a machine learning technique that teaches computers to do what comes naturally to humans: learn by example. It is a key technology behind driverless cars, voice control, and image recognition.",
        "metadata": {"category": "ml_advanced", "language": "en", "topic": "deep_learning"}
    },
    {
        "id": "ml_3",
        "text": "Neural networks are computing systems inspired by biological neural networks that constitute animal brains. A neural network consists of layers of connected nodes, where each connection can transmit a signal from one node to another.",
        "metadata": {"category": "ml_advanced", "language": "en", "topic": "neural_networks"}
    },
    {
        "id": "ai_1",
        "text": "Artificial intelligence refers to the simulation of human intelligence in machines that are programmed to think like humans and mimic their actions. The term may also be applied to any machine that exhibits traits associated with a human mind.",
        "metadata": {"category": "ai_basics", "language": "en", "topic": "artificial_intelligence"}
    },
    {
        "id": "nlp_1",
        "text": "Natural Language Processing (NLP) is a branch of AI that helps computers understand, interpret and manipulate human language. NLP draws from many disciplines, including computer science and computational linguistics.",
        "metadata": {"category": "nlp", "language": "en", "topic": "nlp"}
    },
]

# Expected RAG responses for validation
RAG_EXPECTED_RESPONSES = {
    "machine_learning": {
        "query": "What is machine learning?",
        "expected_sources": ["ml_1", "ml_2"],
        "min_answer_length": 50,
        "should_contain": ["learn", "data", "artificial intelligence"]
    },
    "deep_learning": {
        "query": "Explain deep learning",
        "expected_sources": ["ml_2", "ml_3"],
        "min_answer_length": 40,
        "should_contain": ["deep", "learning", "neural"]
    },
    "neural_networks": {
        "query": "What are neural networks?",
        "expected_sources": ["ml_3"],
        "min_answer_length": 40,
        "should_contain": ["neural", "network", "nodes"]
    },
}

# Performance test data
PERFORMANCE_TEST_QUERIES = [
    "What is AI?",
    "Explain machine learning",
    "How do neural networks work?",
    "What is NLP?",
    "Define deep learning",
]
