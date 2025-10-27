"""Google Cloud Storage service for document storage.
"""

from gcloud.aio.storage import Storage


class GCSStorageService:
    """Google Cloud Storage service for document storage."""

    def __init__(self, project_id: str, bucket_name: str, credentials_path: str = None):
        """Initialize GCS client."""
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.credentials_path = credentials_path
        self.client = None
        self._session_active = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Initialize GCS storage client."""
        self.client = Storage(project=self.project_id)
        self._session_active = True

        # Verify bucket exists
        await self.client.get_bucket(self.bucket_name)

    async def disconnect(self) -> None:
        """Close GCS client session."""
        if self.client and self._session_active:
            await self.client.close()
            self._session_active = False

    async def upload_file(
        self,
        file_data,
        object_path: str,
        content_type: str,
        metadata: dict = None
    ) -> str:
        """Upload file to GCS bucket.

        Args:
            file_data: File content as bytes or file-like object
            object_path: Path in bucket (e.g., "collection_1/doc_uuid.pdf")
            content_type: MIME type (e.g., "application/pdf")
            metadata: Custom metadata dict

        Returns:
            GCS URI (e.g., "gs://bucket-name/object-path")

        Raises:
            StorageError: If upload fails
        """
        from app.exceptions import StorageError

        if not self._session_active:
            raise StorageError("GCS client not connected")

        # Read file data
        if hasattr(file_data, 'read'):
            content = file_data.read()
        else:
            content = file_data

        # Upload to GCS
        await self.client.upload(
            bucket=self.bucket_name,
            object_name=object_path,
            file_data=content,
            content_type=content_type,
            metadata=metadata or {}
        )

        gcs_uri = f"gs://{self.bucket_name}/{object_path}"
        return gcs_uri

    async def download_file(self, object_path: str) -> bytes:
        """Download file from GCS bucket.

        Args:
            object_path: Path in bucket

        Returns:
            File content as bytes

        Raises:
            StorageError: If download fails
        """
        from app.exceptions import StorageError

        if not self._session_active:
            raise StorageError("GCS client not connected")

        content = await self.client.download(
            bucket=self.bucket_name,
            object_name=object_path
        )

        return content
