"""Upload endpoint for document ingestion.

This module handles file uploads with cloud storage integration, validation, and error handling.


Updated: 2025-12-31 - Cloud-agnostic storage with dependency injection
"""

import uuid
import logging
import time
from functools import lru_cache
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.models.schemas import UploadResponse
from app.services.storage.factory import create_storage_service
from app.services.storage.base import ObjectStorageProtocol
from app.config import settings
from app.api.middleware.metrics import file_upload_duration_seconds, file_upload_size_bytes
from app.api.middleware.auth import verify_api_key
from app.utils import extract_file_extension

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",
    "text/csv",
    "text/markdown"
]


@lru_cache()
def get_storage_service() -> ObjectStorageProtocol:
    """Dependency injection for storage service.

    Uses lru_cache to create singleton instance per process.
    Can be overridden in tests using app.dependency_overrides.

    Returns:
        Storage service instance (GCS or S3 based on config)
    """
    if settings.storage_provider == "gcs":
        return create_storage_service(
            provider="gcs",
            bucket_name=settings.gcs_bucket_name,
            project_id=settings.gcs_project_id,
            credentials_path=settings.gcs_credentials_path
        )
    elif settings.storage_provider == "s3":
        return create_storage_service(
            provider="s3",
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url or None
        )
    else:
        raise ValueError(f"Unknown storage provider: {settings.storage_provider}")


@router.post("/api/v1/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    api_key: str = Depends(verify_api_key),
    storage_service: ObjectStorageProtocol = Depends(get_storage_service)
) -> UploadResponse:
    """Upload file to cloud storage for later ingestion.

    Validates file size, MIME type, and uploads to configured cloud storage (GCS or S3).

    Args:
        file: File to upload (multipart/form-data)
        collection_name: Target collection name
        api_key: API key for authentication
        storage_service: Injected storage service (GCS or S3)

    Returns:
        UploadResponse with file_id, storage_path, file_size, mime_type, uploaded_at

    Raises:
        HTTPException:
            - 400: Invalid file type or empty file
            - 413: File too large (>50MB)
            - 500: Cloud storage upload failure
    """
    logger.info(
        f"Upload request: filename={file.filename}, collection={collection_name}")

    start_time = time.time()

    try:
        # 1. Read file content
        content = await file.read()
        file_size = len(content)

        # 2. Validate file is not empty
        if file_size == 0:
            logger.warning(f"Empty file rejected: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="File is empty (0 bytes). Please upload a valid file."
            )

        # 3. Validate file size (max 50MB)
        if file_size > MAX_FILE_SIZE:
            logger.warning(
                f"File too large: {file.filename} ({file_size} bytes)")
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size} bytes). Maximum allowed size is {MAX_FILE_SIZE} bytes (50MB)."
            )

        # 4. Validate MIME type
        mime_type = file.content_type or "application/octet-stream"
        if mime_type not in ALLOWED_MIME_TYPES:
            logger.warning(
                f"Invalid MIME type: {mime_type} for {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {mime_type}. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
            )

        # 5. Generate unique file ID
        file_id = str(uuid.uuid4())

        # 6. Construct cloud storage object path: collection/file_id.extension
        file_extension = file.filename.split(
            '.')[-1] if '.' in file.filename else ''
        object_path = f"{collection_name}/{file_id}.{file_extension}" if file_extension else f"{collection_name}/{file_id}"

        # 7. Upload to cloud storage (GCS or S3)
        logger.info(f"Uploading to {settings.storage_provider.upper()}: {object_path} ({file_size} bytes)")

        async with storage_service:
            storage_uri = await storage_service.upload_file(
                file_data=content,
                object_path=object_path,
                content_type=mime_type,
                metadata={
                    "original_filename": file.filename,
                    "file_id": file_id,
                    "collection_name": collection_name,
                    "uploaded_at": datetime.now(timezone.utc).isoformat()
                }
            )

        logger.info(f"Upload successful: {file_id} -> {storage_uri}")

        # 8. Record metrics
        file_extension = extract_file_extension(file.filename)
        duration = time.time() - start_time
        file_upload_duration_seconds.labels(
            file_type=file_extension).observe(duration)
        file_upload_size_bytes.labels(
            file_type=file_extension).observe(file_size)

        # 9. Return response
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            storage_path=storage_uri,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_at=datetime.now(timezone.utc).isoformat()
        )

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise

    except Exception as e:
        # Catch any other errors (storage failures, etc.)
        logger.error(f"Upload failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )
