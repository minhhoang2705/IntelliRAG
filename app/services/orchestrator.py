"""Orchestrator Service for coordinating all RAG services.

This module provides the OrchestratorService which initializes and
coordinates all services for the RAG system.

Author: IntelliRAG Team
Date: 2025-10-17
"""

from app.services.embedding import EmbeddingService
from app.services.vectordb import VectorDBService
from app.services.llm_client import LLMClientService
from app.services.rag_pipeline import RAGPipelineService
import logging

logger = logging.getLogger(__name__)


class OrchestratorService:
    """Service for orchestrating all RAG components."""

    def __init__(
        self,
        vectordb_url: str = "http://localhost:6333",
        llm_base_url: str = "http://localhost:8000/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct"
    ):
        """Initialize orchestrator with all required services.

        Args:
            vectordb_url: Qdrant vector database URL
            llm_base_url: vLLM server base URL
            llm_model: LLM model name
        """
        logger.info("Initializing OrchestratorService...")

        # Initialize services
        self.embedding_service = EmbeddingService()
        self.vectordb_service = VectorDBService(url=vectordb_url)
        self.llm_client = LLMClientService(
            base_url=llm_base_url,
            model=llm_model
        )

        # Initialize RAG pipeline
        self.rag_pipeline = RAGPipelineService(
            embedding_service=self.embedding_service,
            vectordb_service=self.vectordb_service,
            llm_client=self.llm_client
        )

        logger.info("OrchestratorService initialized successfully")

    async def query(
        self,
        query: str,
        collection_name: str,
        use_rag: bool = True,
        top_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> dict:
        """Execute query using RAG pipeline or direct LLM.

        Args:
            query: User query text
            collection_name: Vector DB collection to search
            use_rag: Whether to use RAG retrieval (if False, direct LLM)
            top_k: Number of documents to retrieve
            temperature: LLM sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Dictionary with 'answer' and 'sources' keys
        """
        if use_rag:
            return await self.rag_pipeline.query_with_rag(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            # Direct LLM query without RAG
            answer = await self.llm_client.generate(
                prompt=query,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return {
                "answer": answer,
                "sources": []
            }
