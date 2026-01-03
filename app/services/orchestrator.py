"""Orchestrator Service for coordinating all RAG services.

This module provides the OrchestratorService which initializes and
coordinates all services for the RAG system.


"""

from app.services.embedding import EmbeddingService
from app.services.vectordb import VectorDBService, parse_collection_dimension
from app.services.llm_client import LLMClientService
from app.services.rag_pipeline import RAGPipelineService
from app.services.query_router.classifier import QueryClassifier, QueryType
from app.services.query_router_service import QueryRouterService
from app.services.job_state import JobStateManager
from app.services.gcs_loader import GCSLoaderService
from app.services.loaders.s3_loader import S3LoaderService
from app.services.semantic_chunker import SemanticChunkerService
from app.utils import extract_file_extension
from urllib.parse import urlparse
import logging
import time
from opentelemetry import trace
from app.api.middleware.metrics import (
    document_processing_stage_duration_seconds,
    ingestion_chunks_created,
    ingestion_job_duration_seconds,
    ingestion_errors_total
)

logger = logging.getLogger(__name__)


class OrchestratorService:
    """Service for orchestrating all RAG components."""

    def __init__(
        self,
        vectordb_url: str = "http://localhost:6333",
        llm_base_url: str = "http://localhost:8000/v1",
        llm_model: str = "Qwen/Qwen3-0.6B",
        storage_provider: str = "gcs",
        storage_bucket: str = "test-bucket",
        gcs_project: str = "test-project",
        s3_region: str = "us-east-1",
        embedding_service_url: str = "http://localhost:8001",
        use_remote_embedding: bool = True,
        # Optional service injection for testing
        embedding_service: EmbeddingService = None,
        vectordb_service: VectorDBService = None,
        llm_client: LLMClientService = None,
        storage_loader = None,
        semantic_chunker: SemanticChunkerService = None,
        job_state_manager: JobStateManager = None,
        query_router_service: QueryRouterService = None
    ):
        """Initialize orchestrator with all required services.

        Args:
            vectordb_url: Qdrant vector database URL
            llm_base_url: vLLM server base URL
            llm_model: LLM model name
            storage_provider: Storage provider ("gcs" or "s3", default: "gcs")
            storage_bucket: Storage bucket name
            gcs_project: GCP project ID (required for GCS)
            s3_region: AWS region (required for S3, default: "us-east-1")
            embedding_service_url: Embedding service URL (default: http://localhost:8001)
            use_remote_embedding: Use remote embedding service (default: True)
            embedding_service: Optional pre-configured embedding service (for testing)
            vectordb_service: Optional pre-configured vector DB service (for testing)
            llm_client: Optional pre-configured LLM client (for testing)
            storage_loader: Optional pre-configured storage loader (for testing)
            semantic_chunker: Optional pre-configured semantic chunker (for testing)
            job_state_manager: Optional pre-configured job state manager (for testing)
            query_router_service: Optional pre-configured query router (for testing)
        """
        logger.info("Initializing OrchestratorService...")

        # Initialize embedding service (use provided or create new)
        if embedding_service is not None:
            self.embedding_service = embedding_service
        else:
            self.embedding_service = EmbeddingService(
                use_remote=use_remote_embedding,
                remote_url=embedding_service_url,
                device="cpu"  # Only used in local mode
            )

        # Initialize other services (use provided or create new)
        if vectordb_service is not None:
            self.vectordb_service = vectordb_service
        else:
            self.vectordb_service = VectorDBService(url=vectordb_url)

        if llm_client is not None:
            self.llm_client = llm_client
        else:
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

        # Initialize query router service (use provided or create new)
        if query_router_service is not None:
            self.query_router_service = query_router_service
        else:
            classifier = QueryClassifier(llm_client=self.llm_client)
            self.query_router_service = QueryRouterService(
                classifier=classifier,
                vectordb=self.vectordb_service,
                llm=self.llm_client,
                embedding=self.embedding_service
            )

        # Initialize storage loader service (use provided or create based on provider)
        if storage_loader is not None:
            self.storage_loader = storage_loader
        else:
            if storage_provider == "gcs":
                self.storage_loader = GCSLoaderService(
                    project_name=gcs_project,
                    bucket=storage_bucket
                )
            elif storage_provider == "s3":
                self.storage_loader = S3LoaderService(
                    bucket=storage_bucket,
                    region=s3_region
                )
            else:
                raise ValueError(
                    f"Unknown storage provider: {storage_provider}. "
                    f"Supported providers: gcs, s3"
                )

        # Store provider and bucket for URI parsing
        self.storage_provider = storage_provider
        self.storage_bucket = storage_bucket

        if semantic_chunker is not None:
            self.semantic_chunker = semantic_chunker
        else:
            self.semantic_chunker = SemanticChunkerService(
                embeddings=self.embedding_service)

        # Initialize job state manager (use provided or create new)
        if job_state_manager is not None:
            self.job_state_manager = job_state_manager
        else:
            self.job_state_manager = JobStateManager()

        logger.info("OrchestratorService initialized successfully")

    def _parse_storage_uri(self, uri: str) -> str:
        """Parse cloud storage URI and extract object path.

        Uses urllib.parse for robust URI parsing to avoid issues when
        bucket name appears in the object path.

        Args:
            uri: Cloud storage URI (gs://bucket/path or s3://bucket/path)
                 or plain path without scheme

        Returns:
            Object path within the bucket (e.g., "folder/file.pdf")

        Examples:
            gs://my-bucket/docs/file.pdf -> docs/file.pdf
            s3://my-bucket/my-bucket/file.pdf -> my-bucket/file.pdf (handles edge case)
        """
        if uri.startswith(("gs://", "s3://")):
            parsed = urlparse(uri)
            # parsed.path starts with '/', so strip leading slash
            return parsed.path.lstrip("/")
        else:
            # Already a plain path without URI scheme
            return uri

    async def query(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 512,
        use_rag: bool = None
    ) -> dict:
        """Execute query using QueryRouterService for intelligent routing.

        Args:
            query: User query text
            collection_name: Vector DB collection to search
            top_k: Number of documents to retrieve
            temperature: LLM sampling temperature
            max_tokens: Maximum tokens to generate
            use_rag: If True, force RAG retrieval; if False, force direct; if None, use classification

        Returns:
            dict with keys:
            - answer: Generated answer
            - sources: List of source documents
            - classification: Query classification result
            - used_rag: Boolean indicating whether RAG retrieval was used
        """
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("orchestrator.query") as span:
            # Set span attributes
            span.set_attribute("query.collection", collection_name)
            span.set_attribute("query.top_k", top_k)

            # Use QueryRouterService for intelligent routing
            # If use_rag is explicitly set, honor it
            force_rag = use_rag if use_rag is True else False
            result = await self.query_router_service.route_query(
                query=query,
                collection_name=collection_name,
                force_rag=force_rag
            )

            # Check for errors from graph execution
            if result.get("error"):
                logger.error(f"Query routing failed: {result['error']}")
                # Return error response with proper defaults
                return {
                    "answer": f"I apologize, but I encountered an error processing your query: {result['error']}",
                    "sources": [],
                    "classification": None,
                    "used_rag": False
                }

            # Extract sources from context if available
            sources = []
            if result.get("context"):
                # Context is a list of retrieved documents with scores
                for doc in result["context"]:
                    sources.append({
                        "text": doc.get("text", ""),
                        "score": doc.get("score", 0.0),
                        "id": str(doc.get("id", ""))
                    })

            # Determine if RAG was actually used
            classification = result.get("classification")
            used_rag = len(sources) > 0 or (
                classification and classification.query_type in [
                    QueryType.RAG, QueryType.MULTI_HOP]
            )

            # Get response, ensuring it's never None or empty
            answer = result.get("response", "")
            if not answer:
                answer = "I apologize, but I was unable to generate a response to your query."

            # Transform result to maintain backward compatibility
            return {
                "answer": answer,
                "sources": sources,
                "classification": classification,
                "used_rag": used_rag
            }

    async def ingest(self, file_path: str, collection_name: str, job_id: str = None):
        """Ingest document into vector database.

        Args:
            file_path: Cloud storage path to document (gs://bucket/path or s3://bucket/path)
            collection_name: Target collection in vector database
            job_id: Optional pre-existing job ID. If not provided, creates a new job.

        Returns:
            Job ID for tracking ingestion progress
        """
        from app.services.job_state import JobStatus

        # Use provided job_id or create a new one
        if job_id is None:
            job_id = self.job_state_manager.create_job(
                file_path, collection_name)

        self.job_state_manager.update_job_status(job_id, JobStatus.PROCESSING)

        # Start timing for end-to-end job duration
        job_start_time = time.time()

        try:
            # Extract file type for metrics
            file_extension = extract_file_extension(file_path)

            # Parse cloud storage URI to extract object path using urlparse
            # gs://bucket/folder/file.pdf -> folder/file.pdf
            # s3://bucket/folder/file.pdf -> folder/file.pdf
            object_path = self._parse_storage_uri(file_path)

            # Load document from cloud storage
            try:
                start_time = time.time()
                if self.storage_provider == "gcs":
                    documents = await self.storage_loader.load_file(object_path)
                else:  # s3
                    # S3LoaderService uses 'key' instead of 'blob'
                    documents = await self.storage_loader.load_file(object_path)
                load_duration = time.time() - start_time
                document_processing_stage_duration_seconds.labels(
                    stage='loading', file_type=file_extension
                ).observe(load_duration)
            except Exception as e:
                ingestion_errors_total.labels(
                    error_type=type(e).__name__, stage='loading'
                ).inc()
                raise

            # Chunk documents semantically
            try:
                start_time = time.time()
                chunks = await self.semantic_chunker.chunk_documents(documents)
                chunk_duration = time.time() - start_time
                document_processing_stage_duration_seconds.labels(
                    stage='chunking', file_type=file_extension
                ).observe(chunk_duration)
                ingestion_chunks_created.labels(
                    file_type=file_extension).observe(len(chunks))
            except Exception as e:
                ingestion_errors_total.labels(
                    error_type=type(e).__name__, stage='chunking'
                ).inc()
                raise

            # Generate embeddings for chunks
            try:
                chunk_texts = [chunk.page_content for chunk in chunks]
                start_time = time.time()
                embeddings = self.embedding_service.embed_batch(chunk_texts)
                embed_duration = time.time() - start_time
                document_processing_stage_duration_seconds.labels(
                    stage='embedding', file_type=file_extension
                ).observe(embed_duration)
            except Exception as e:
                ingestion_errors_total.labels(
                    error_type=type(e).__name__, stage='embedding'
                ).inc()
                raise

            # Ensure collection exists with correct dimension (auto-migrate if needed)
            try:
                result = await self.vectordb_service.ensure_collection_with_dimension(
                    collection_name=collection_name,
                    vector_size=self.embedding_service.get_embedding_dimension(),
                    distance="cosine",
                    auto_migrate=True  # Create new collection with dimension suffix if mismatch
                )

                if result["action"] == "created":
                    logger.info(
                        f"Created new collection '{collection_name}' with dimension {result['dimension']}")
                elif result["action"] == "exists":
                    logger.info(
                        f"Using existing collection '{collection_name}' with dimension {result['dimension']}")
                elif result["action"] == "created_new":
                    # Dimension mismatch - new collection created with suffix
                    new_collection_name = result["new_collection_name"]
                    logger.warning(
                        f"Dimension mismatch detected! "
                        f"Old collection '{result['old_collection_name']}' has dimension {parse_collection_dimension(result['old_collection_name'])}. "
                        f"Created new collection '{new_collection_name}' with dimension {result['dimension']}"
                    )
                    # Update collection_name to use the new one
                    collection_name = new_collection_name

            except ValueError as e:
                # Dimension mismatch - provide helpful error
                self.job_state_manager.mark_job_failed(job_id, str(e))
                raise

            # Store vectors in database
            try:
                start_time = time.time()
                await self.vectordb_service.upsert_vectors(
                    collection_name=collection_name,
                    vectors=embeddings,
                    payloads=[chunk.metadata for chunk in chunks],
                    ids=None  # Let Qdrant generate IDs
                )
                storage_duration = time.time() - start_time
                document_processing_stage_duration_seconds.labels(
                    stage='storage', file_type=file_extension
                ).observe(storage_duration)
            except Exception as e:
                ingestion_errors_total.labels(
                    error_type=type(e).__name__, stage='storage'
                ).inc()
                raise

            # Mark job as completed with progress and chunks info
            self.job_state_manager.update_job_status(
                job_id, JobStatus.COMPLETED)
            self.job_state_manager.update_job_progress(
                job_id,
                progress=100,
                message=f"Ingestion completed successfully. Created {len(chunks)} chunks."
            )
            # Update chunks_created in job state
            job = self.job_state_manager.get_job(job_id)
            if job:
                job.chunks_created = len(chunks)
            else:
                logger.warning(
                    f"Job {job_id} not found in job state manager after completion")

            # Record successful job duration
            job_duration = time.time() - job_start_time
            ingestion_job_duration_seconds.labels(
                status='completed', file_type=file_extension
            ).observe(job_duration)

        except Exception as e:
            # Record failed job duration
            job_duration = time.time() - job_start_time
            file_extension = extract_file_extension(file_path)
            ingestion_job_duration_seconds.labels(
                status='failed', file_type=file_extension
            ).observe(job_duration)

            # Mark job as failed with error message
            self.job_state_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                error=str(e)
            )
            raise

        return job_id
