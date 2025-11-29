"""Upload endpoint for document ingestion.

This module handles file uploads with GCS integration, validation, and error handling.


Updated: 2025-10-29 - Production-ready with GCS integration (TDD GREEN phase)
"""

import uuid
import logging
import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.models.schemas import UploadResponse
from app.services.gcs_storage import GCSStorageService
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

# Initialize GCS storage service (will be configured from environment)
gcs_storage = GCSStorageService(
    project_id=os.getenv("GCP_PROJECT_ID", "intellirag-project"),
    bucket_name=os.getenv("GCS_BUCKET_NAME", "intellirag-uploads"),
    credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
)


@router.post("/api/v1/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    api_key: str = Depends(verify_api_key)
) -> UploadResponse:
    """Upload file to GCS for later ingestion.

    Validates file size, MIME type, and uploads to Google Cloud Storage.

    Args:
        file: File to upload (multipart/form-data)
        collection_name: Target collection name

    Returns:
        UploadResponse with file_id, gcs_path, file_size, mime_type, uploaded_at

    Raises:
        HTTPException: 
            - 400: Invalid file type or empty file
            - 413: File too large (>50MB)
            - 500: GCS upload failure
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

        # 6. Construct GCS object path: collection/file_id/original_filename
        file_extension = file.filename.split(
            '.')[-1] if '.' in file.filename else ''
        gcs_object_path = f"{collection_name}/{file_id}.{file_extension}" if file_extension else f"{collection_name}/{file_id}"

        # 7. Upload to GCS
        logger.info(f"Uploading to GCS: {gcs_object_path} ({file_size} bytes)")

        async with gcs_storage:
            gcs_uri = await gcs_storage.upload_file(
                file_data=content,
                object_path=gcs_object_path,
                content_type=mime_type,
                metadata={
                    "original_filename": file.filename,
                    "file_id": file_id,
                    "collection_name": collection_name,
                    "uploaded_at": datetime.now(timezone.utc).isoformat()
                }
            )

        logger.info(f"Upload successful: {file_id} -> {gcs_uri}")

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
            gcs_path=gcs_uri,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_at=datetime.now(timezone.utc).isoformat()
        )

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise

    except Exception as e:
        # Catch any other errors (GCS failures, etc.)
        logger.error(f"Upload failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )
