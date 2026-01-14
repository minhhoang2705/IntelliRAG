"""RAG Pipeline Service for orchestrating retrieval-augmented generation.

This module provides the RAGPipelineService which coordinates embedding,
retrieval, and generation to answer user queries.



"""

from typing import List, Dict, Any, Optional
from app.services.embedding import EmbeddingService
from app.services.vectordb import VectorDBService
from app.services.llm_client import LLMClientService
from app.services.query_router.template_loader import TemplateLoader
import logging
from opentelemetry import trace

logger = logging.getLogger(__name__)


class RAGPipelineService:
    """Service for orchestrating the RAG pipeline."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vectordb_service: VectorDBService,
        llm_client: LLMClientService,
        template_loader: Optional[TemplateLoader] = None
    ):
        """Initialize RAG pipeline with required services.

        Args:
            embedding_service: Service for generating embeddings
            vectordb_service: Service for vector storage and retrieval
            llm_client: Service for LLM text generation
            template_loader: Optional TemplateLoader for multilingual prompts
        """
        self.embedding_service = embedding_service
        self.vectordb_service = vectordb_service
        self.llm_client = llm_client
        self.template_loader = template_loader or TemplateLoader()
        logger.info("Initialized RAGPipelineService")

    async def query_with_rag(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 512,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute RAG query flow: embed → retrieve → generate.

        Args:
            query: User query text
            collection_name: Vector DB collection to search
            top_k: Number of documents to retrieve
            temperature: LLM sampling temperature
            max_tokens: Maximum tokens to generate
            language: Optional language override ("en" or "vi")

        Returns:
            Dictionary with 'answer' and 'sources' keys
        """
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("rag.query") as span:
            span.set_attribute("rag.collection", collection_name)
            span.set_attribute("rag.top_k", top_k)

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
            context_texts = []
            sources = []
            for result in search_results:
                context_texts.append(result.payload['text'])
                sources.append({
                    "text": result.payload['text'],
                    "score": float(result.score),
                    "id": str(result.id)
                })

            # Step 4: Create system and user prompts using templates
            system_prompt = self.template_loader.render(
                template_name="rag_system.j2",
                language=language,
                query=query,
                context=context_texts
            )

            user_prompt = self.template_loader.render(
                template_name="rag_user.j2",
                language=language,
                query=query
            )

            # Combine system and user prompts
            prompt = f"{system_prompt}\n\n{user_prompt}"

            # Step 5: Generate answer using LLM
            answer = await self.llm_client.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            span.set_attribute("rag.sources_count", len(sources))

            logger.info(f"Generated answer with {len(sources)} sources")

            return {
                "answer": answer,
                "sources": sources
            }
