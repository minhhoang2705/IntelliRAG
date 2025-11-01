"""RAG Pipeline Service for orchestrating retrieval-augmented generation.

This module provides the RAGPipelineService which coordinates embedding,
retrieval, and generation to answer user queries.


Date: 2025-10-17
"""

from typing import List, Dict, Any
from app.services.embedding import EmbeddingService
from app.services.vectordb import VectorDBService
from app.services.llm_client import LLMClientService
import logging

logger = logging.getLogger(__name__)


class RAGPipelineService:
    """Service for orchestrating the RAG pipeline."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vectordb_service: VectorDBService,
        llm_client: LLMClientService
    ):
        """Initialize RAG pipeline with required services.

        Args:
            embedding_service: Service for generating embeddings
            vectordb_service: Service for vector storage and retrieval
            llm_client: Service for LLM text generation
        """
        self.embedding_service = embedding_service
        self.vectordb_service = vectordb_service
        self.llm_client = llm_client
        logger.info("Initialized RAGPipelineService")

    async def query_with_rag(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> Dict[str, Any]:
        """Execute RAG query flow: embed → retrieve → generate.

        Args:
            query: User query text
            collection_name: Vector DB collection to search
            top_k: Number of documents to retrieve
            temperature: LLM sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Dictionary with 'answer' and 'sources' keys
        """
        logger.info(f"Executing RAG query: {query[:50]}...")

        # Step 1: Embed query
        query_embedding = await self.embedding_service.embed_single_async(query)

        # Step 2: Retrieve relevant documents
        search_results = await self.vectordb_service.search_vectors(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k
        )

        # Step 3: Format context from retrieved documents
        context_parts = []
        sources = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"[{i}] {result.payload['text']}")
            sources.append({
                "text": result.payload['text'],
                "score": float(result.score),
                "id": str(result.id)
            })

        context = "\n\n".join(context_parts)

        # Step 4: Create prompt with context
        prompt = f"""Answer the question based on the provided context.

Context:
{context}

Question: {query}

Answer:"""

        # Step 5: Generate answer using LLM
        answer = await self.llm_client.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        logger.info(f"Generated answer with {len(sources)} sources")

        return {
            "answer": answer,
            "sources": sources
        }
