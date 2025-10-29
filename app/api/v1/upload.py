"""Upload endpoint for document ingestion.

This module handles file uploads for the ingestion pipeline.

Date: 2025-10-28
"""

from fastapi import APIRouter, UploadFile

router = APIRouter()


@router.post("/api/v1/upload")
async def upload_file(file: UploadFile):
    """Upload a file for ingestion."""
    return {"filename": file.filename}
