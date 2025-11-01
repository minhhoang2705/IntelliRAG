"""Integration tests for full ingestion pipeline with real GCS.

Tests the complete flow: Upload → Ingest → Status Polling → Query
Uses real GCS bucket configured in .env.test

Date: 2025-10-30
"""

import pytest
import pytest_asyncio
import asyncio
import os
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from google.cloud import storage


@pytest.fixture(scope="session")
def gcs_config():
    """GCS configuration from .env.test"""
    config = {
        "project_id": os.getenv("GCP_PROJECT_ID"),
        "bucket_name": os.getenv("GCS_BUCKET_NAME"),
        "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    }

    # Verify all required config is present
    missing = [k for k, v in config.items() if not v]
    if missing:
        pytest.skip(f"Missing GCS config: {', '.join(missing)}. Configure in .env.test")

    return config


@pytest.fixture(scope="session")
def gcs_client(gcs_config):
    """Create GCS client with service account credentials."""
    return storage.Client.from_service_account_json(
        gcs_config["credentials_path"],
        project=gcs_config["project_id"]
    )


@pytest.fixture(scope="function")
def cleanup_gcs_files(gcs_client, gcs_config):
    """Cleanup test files from GCS after each test."""
    files_to_cleanup = []

    def register(blob_name):
        files_to_cleanup.append(blob_name)

    yield register

    # Cleanup after test
    bucket = gcs_client.bucket(gcs_config["bucket_name"])
    for blob_name in files_to_cleanup:
        try:
            blob = bucket.blob(blob_name)
            blob.delete()
        except Exception as e:
            print(f"Warning: Could not delete {blob_name}: {e}")


@pytest.fixture(scope="function")
def sample_pdf_path():
    """Path to sample PDF for testing."""
    pdf_path = Path(__file__).parent.parent / "fixtures" / "test-sample-2.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Sample PDF not found: {pdf_path}")
    return pdf_path


class TestIngestionPipelineIntegration:
    """Integration tests for full ingestion pipeline (TDD)."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)  # 5 minutes timeout for first-time model loading
    async def test_full_upload_ingest_status_pipeline(
        self,
        initialized_app,
        sample_pdf_path,
        cleanup_gcs_files,
        gcs_config
    ):
        """Test complete pipeline: upload → ingest → poll status until complete.

        Flow:
        1. Upload PDF file to GCS via /upload endpoint
        2. Trigger ingestion via /ingest endpoint
        3. Poll /status endpoint until job completes
        4. Verify job completed successfully
        5. Verify metrics were recorded

        Expected: Full pipeline succeeds, metrics recorded
        RED: This should FAIL as pipeline not fully integrated yet.
        
        Note: First run may take 3-5 minutes due to embedding model download/loading (560MB).
        """
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 1: Upload file
            with open(sample_pdf_path, "rb") as f:
                upload_response = await client.post(
                    "/api/v1/upload",
                    files={"file": ("test.pdf", f, "application/pdf")},
                    data={"collection_name": "test_integration"}
                )

            assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
            upload_data = upload_response.json()
            assert "gcs_path" in upload_data
            gcs_path = upload_data["gcs_path"]

            # Register for cleanup
            blob_name = gcs_path.replace(f"gs://{gcs_config['bucket_name']}/", "")
            cleanup_gcs_files(blob_name)

            # Step 2: Trigger ingestion
            ingest_response = await client.post(
                "/api/v1/ingest",
                json={
                    "file_path": gcs_path,
                    "collection_name": "test_integration"
                }
            )

            assert ingest_response.status_code == 202, f"Ingest failed: {ingest_response.text}"
            ingest_data = ingest_response.json()
            assert "job_id" in ingest_data
            job_id = ingest_data["job_id"]

            # Step 3: Poll status until completion with exponential backoff
            # Allow up to 4 minutes for ingestion (model loading + processing)
            max_wait_time = 240  # seconds
            poll_interval = 1.0  # start with 1 second
            max_poll_interval = 5.0  # cap at 5 seconds
            elapsed_time = 0
            final_status = None
            last_message = None

            print(f"\n⏳ Polling job {job_id} (may take 3-5 minutes on first run for model loading)...")

            while elapsed_time < max_wait_time:
                status_response = await client.get(f"/api/v1/ingest/status/{job_id}")
                assert status_response.status_code == 200, f"Status check failed: {status_response.text}"

                status_data = status_response.json()
                final_status = status_data["status"]
                current_message = status_data.get("message", "")
                progress = status_data.get("progress", 0)

                # Log progress changes
                if current_message != last_message:
                    print(f"  [{int(elapsed_time)}s] Status: {final_status}, Progress: {progress}%, Message: {current_message}")
                    last_message = current_message

                # Check for terminal states
                if final_status == "completed":
                    print(f"✅ Job completed in {int(elapsed_time)} seconds")
                    break
                    
                if final_status == "failed":
                    error = status_data.get("error", "Unknown error")
                    print(f"❌ Job failed: {error}")
                    break

                # Wait with exponential backoff
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval
                
                # Increase poll interval gradually (exponential backoff)
                poll_interval = min(poll_interval * 1.2, max_poll_interval)

            # Step 4: Verify completion
            if final_status != "completed":
                error_detail = status_data.get("error", "No error details")
                assert False, (
                    f"Job did not complete within {max_wait_time}s. "
                    f"Final status: {final_status}, Progress: {status_data.get('progress')}%, "
                    f"Message: {status_data.get('message')}, Error: {error_detail}"
                )
            
            assert status_data.get("progress") == 100, "Progress should be 100% on completion"

            # Step 5: Verify chunks were created
            chunks_created = status_data.get("chunks_created", 0)
            assert chunks_created > 0, f"Expected chunks to be created, got: {chunks_created}"
            print(f"  Chunks created: {chunks_created}")
