"""
Standalone Embedding Service for IntelliRAG
Serves BAAI/bge-m3 embeddings via FastAPI
Always-on service - model pre-loaded on startup

Configurable via environment variables:
- EMBEDDING_MODEL: Model to load (default: BAAI/bge-m3)
- DEVICE: cpu or cuda (default: cpu)
- MAX_BATCH_SIZE: Maximum batch size (default: 128)

Date: 2025-11-04
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import logging
import time
import torch
import os
from huggingface_hub import login  
from dotenv import load_dotenv

load_dotenv("../../.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global model instance (loaded on startup)
model: Optional[SentenceTransformer] = None
model_metadata: dict = {}

# Configuration from environment variables
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "google/embeddinggemma-300m")
DEVICE = os.getenv("DEVICE", "cpu")
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "32"))
HF_TOKEN = os.getenv("HF_TOKEN", None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global model, model_metadata

    # Startup
    logger.info(f"🚀 Loading embedding model: {MODEL_NAME}")
    logger.info(f"🔧 Device: {DEVICE}")
    start_time = time.time()

    try:
        # Login to HuggingFace if token is provided (for gated models)
        if HF_TOKEN:
            logger.info("🔐 Authenticating with HuggingFace...")
            login(token=HF_TOKEN, add_to_git_credential=False)
            logger.info("✅ HuggingFace authentication successful")

        # Load model
        model = SentenceTransformer(MODEL_NAME)
        model.to(DEVICE)

        # Auto-detect model properties
        embedding_dim = get_embedding_dimension(model)
        max_seq_len = get_max_seq_length(model)

        # Store metadata
        model_metadata = {
            "model_name": MODEL_NAME,
            "embedding_dimension": embedding_dim,
            "device": DEVICE,
            "max_seq_length": max_seq_len,
            "max_batch_size": MAX_BATCH_SIZE
        }

        # Warm up with a test embedding
        _ = model.encode("warm up", convert_to_numpy=True)

        load_time = time.time() - start_time
        logger.info(f"✅ Model loaded successfully in {load_time:.2f}s")
        logger.info(f"📊 Embedding dimension: {embedding_dim}")
        logger.info(f"📏 Max sequence length: {max_seq_len}")
        logger.info(f"🔧 Device: {DEVICE}")

    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        raise RuntimeError(f"Model loading failed: {e}")

    yield  # Application runs here

    # Shutdown (cleanup if needed)
    logger.info("Shutting down embedding service...")


app = FastAPI(
    title="Embedding Service",
    description="Configurable Embedding Model Service",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response Models
class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1,
                             description="List of texts to embed")
    normalize: bool = Field(
        default=False, description="L2 normalize embeddings")
    batch_size: Optional[int] = Field(
        default=None, description="Batch size for processing")


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int
    count: int
    processing_time_seconds: float


class ModelInfoResponse(BaseModel):
    """Model information - allows clients to query embedding dimension dynamically."""
    model_name: str
    embedding_dimension: int
    device: str
    max_batch_size: int
    model_loaded: bool
    max_seq_length: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    device: str
    embedding_dimension: int


def get_embedding_dimension(model_instance: SentenceTransformer) -> int:
    """
    Auto-detect embedding dimension from the loaded model.
    This ensures we always return the correct dimension regardless of model.
    """
    try:
        # Method 1: Check model config
        if hasattr(model_instance, 'get_sentence_embedding_dimension'):
            return model_instance.get_sentence_embedding_dimension()

        # Method 2: Generate a test embedding
        test_embedding = model_instance.encode("test", convert_to_numpy=True)
        return len(test_embedding)
    except Exception as e:
        logger.error(f"Failed to detect embedding dimension: {e}")
        raise


def get_max_seq_length(model_instance: SentenceTransformer) -> Optional[int]:
    """Get maximum sequence length supported by the model."""
    try:
        if hasattr(model_instance, 'max_seq_length'):
            return model_instance.max_seq_length
        return None
    except Exception as e:
        logger.warning(f"Could not detect max sequence length: {e}")
        return None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with model status."""
    return HealthResponse(
        status="healthy" if model is not None else "unhealthy",
        model_loaded=model is not None,
        model_name=model_metadata.get("model_name", MODEL_NAME),
        device=model_metadata.get("device", DEVICE),
        embedding_dimension=model_metadata.get("embedding_dimension", 0)
    )


@app.get("/model-info", response_model=ModelInfoResponse)
async def get_model_info():
    """
    Get model information including embedding dimension.

    Clients should call this endpoint to discover the embedding dimension
    before creating vector database collections.
    """
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service may be starting up."
        )

    return ModelInfoResponse(
        model_name=model_metadata["model_name"],
        embedding_dimension=model_metadata["embedding_dimension"],
        device=model_metadata["device"],
        max_batch_size=model_metadata["max_batch_size"],
        max_seq_length=model_metadata.get("max_seq_length"),
        model_loaded=True
    )


@app.post("/vectorize", response_model=EmbedResponse)
async def vectorize(request: EmbedRequest):
    """
    Generate embeddings for input texts.

    This endpoint is always ready - no model loading delay!
    Returns embeddings with the actual dimension of the loaded model.
    """
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service may be starting up."
        )

    if not request.texts:
        raise HTTPException(status_code=400, detail="No texts provided")

    try:
        start_time = time.time()

        # Use batch size from request or default
        batch_size = request.batch_size or MAX_BATCH_SIZE

        # Generate embeddings
        embeddings = model.encode(
            request.texts,
            batch_size=batch_size,
            normalize_embeddings=request.normalize,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        duration = time.time() - start_time

        logger.info(
            f"Generated {len(request.texts)} embeddings in {duration:.3f}s "
            f"({len(request.texts)/duration:.1f} vectors/sec)"
        )

        return EmbedResponse(
            embeddings=embeddings.tolist(),
            model=model_metadata["model_name"],
            dimension=model_metadata["embedding_dimension"],
            count=len(request.texts),
            processing_time_seconds=round(duration, 3)
        )

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Embedding failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "IntelliRAG Embedding Service",
        "model": model_metadata.get("model_name", MODEL_NAME),
        "dimension": model_metadata.get("embedding_dimension", "not loaded"),
        "status": "ready" if model is not None else "starting",
        "endpoints": {
            "health": "/health",
            "model_info": "/model-info (GET) - Get model metadata",
            "vectorize": "/vectorize (POST) - Generate embeddings",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
