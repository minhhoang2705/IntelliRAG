"""
AWS S3 storage service for document storage.

This module provides S3StorageService implementing the ObjectStorageProtocol
for AWS S3 object storage operations.
"""

import aioboto3
import asyncio
import logging
import time
from typing import Optional
from botocore.exceptions import ClientError, BotoCoreError
from opentelemetry import trace
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Prometheus metrics for S3 operations
s3_operations_total = Counter(
    's3_operations_total',
    'Total S3 operations',
    ['operation', 'status', 'bucket']
)

s3_operation_duration_seconds = Histogram(
    's3_operation_duration_seconds',
    'S3 operation duration in seconds',
    ['operation', 'bucket'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

s3_retries_total = Counter(
    's3_retries_total',
    'Total S3 operation retries',
    ['operation', 'bucket']
)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 10.0  # seconds

# Retryable S3 error codes
RETRYABLE_ERRORS = {
    'RequestTimeout',
    'ServiceUnavailable',
    'ThrottlingException',
    'RequestLimitExceeded',
    'InternalError',
    'SlowDown'
}


async def retry_with_backoff(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """Execute async function with exponential backoff retry.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_retries: Maximum retry attempts (default: 3)
        **kwargs: Keyword arguments for func

    Returns:
        Result from func

    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in RETRYABLE_ERRORS and attempt < max_retries:
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                logger.warning(
                    f"S3 operation failed with {error_code}, "
                    f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(delay)
                last_exception = e
            else:
                raise
        except BotoCoreError as e:
            if attempt < max_retries:
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                logger.warning(
                    f"S3 connection error, retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(delay)
                last_exception = e
            else:
                raise

    raise last_exception


class S3StorageService:
    """AWS S3 storage service implementing ObjectStorageProtocol."""

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        max_retries: int = MAX_RETRIES
    ):
        """Initialize S3 client.

        Args:
            bucket_name: S3 bucket name
            region: AWS region (default: us-east-1)
            endpoint_url: Optional endpoint URL for LocalStack testing
            max_retries: Maximum retry attempts for operations (default: 3)
        """
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url
        self.max_retries = max_retries
        self._session = None
        self._client = None
        self._session_active = False
        logger.info(
            f"Initialized S3StorageService for bucket: {bucket_name}, "
            f"region: {region}"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Initialize S3 storage client."""
        self._session = aioboto3.Session()
        client_kwargs = {'region_name': self.region}

        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url

        self._client = await self._session.client(
            's3', **client_kwargs
        ).__aenter__()
        self._session_active = True
        logger.debug(f"Connected to S3 bucket: {self.bucket_name}")

    async def disconnect(self) -> None:
        """Close S3 client session."""
        if self._client and self._session_active:
            await self._client.__aexit__(None, None, None)
            self._session_active = False
            logger.debug(f"Disconnected from S3 bucket: {self.bucket_name}")

    async def upload_file(
        self,
        file_data,
        object_path: str,
        content_type: str,
        metadata: Optional[dict] = None
    ) -> str:
        """Upload file to S3 bucket with retry logic and telemetry.

        Args:
            file_data: File content as bytes or file-like object
            object_path: Path in bucket (e.g., "collection_1/doc_uuid.pdf")
            content_type: MIME type (e.g., "application/pdf")
            metadata: Optional custom metadata dict

        Returns:
            S3 URI (e.g., "s3://bucket-name/object-path")

        Raises:
            StorageError: If upload fails after all retries
        """
        from app.exceptions import StorageError

        if not self._session_active:
            raise StorageError("S3 client not connected")

        content = file_data.read() if hasattr(file_data, 'read') else file_data
        start_time = time.time()

        with tracer.start_as_current_span("s3.upload_file") as span:
            span.set_attribute("s3.bucket", self.bucket_name)
            span.set_attribute("s3.key", object_path)
            span.set_attribute("s3.content_type", content_type)
            span.set_attribute("s3.content_length", len(content))

            async def _do_upload():
                await self._client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_path,
                    Body=content,
                    ContentType=content_type,
                    Metadata=metadata or {}
                )

            try:
                await retry_with_backoff(_do_upload, max_retries=self.max_retries)
                duration = time.time() - start_time

                # Record success metrics
                s3_operations_total.labels(
                    operation='upload', status='success', bucket=self.bucket_name
                ).inc()
                s3_operation_duration_seconds.labels(
                    operation='upload', bucket=self.bucket_name
                ).observe(duration)

                span.set_attribute("s3.duration_seconds", duration)
                logger.info(f"Uploaded to S3: s3://{self.bucket_name}/{object_path}")
                return f"s3://{self.bucket_name}/{object_path}"

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                s3_operations_total.labels(
                    operation='upload', status='error', bucket=self.bucket_name
                ).inc()
                span.set_attribute("error", True)
                span.set_attribute("error.code", error_code)
                logger.error(
                    f"S3 upload failed: {error_code} - s3://{self.bucket_name}/{object_path}"
                )
                raise StorageError(f"S3 upload failed: {error_code}") from e

            except BotoCoreError as e:
                s3_operations_total.labels(
                    operation='upload', status='error', bucket=self.bucket_name
                ).inc()
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"S3 connection error during upload: {e}")
                raise StorageError(f"S3 connection error: {e}") from e

    async def download_file(self, object_path: str) -> bytes:
        """Download file from S3 bucket with retry logic and telemetry.

        Args:
            object_path: Path in bucket

        Returns:
            File content as bytes

        Raises:
            StorageError: If download fails after all retries
        """
        from app.exceptions import StorageError

        if not self._session_active:
            raise StorageError("S3 client not connected")

        start_time = time.time()

        with tracer.start_as_current_span("s3.download_file") as span:
            span.set_attribute("s3.bucket", self.bucket_name)
            span.set_attribute("s3.key", object_path)

            async def _do_download():
                response = await self._client.get_object(
                    Bucket=self.bucket_name,
                    Key=object_path
                )
                return await response['Body'].read()

            try:
                content = await retry_with_backoff(
                    _do_download, max_retries=self.max_retries
                )
                duration = time.time() - start_time

                # Record success metrics
                s3_operations_total.labels(
                    operation='download', status='success', bucket=self.bucket_name
                ).inc()
                s3_operation_duration_seconds.labels(
                    operation='download', bucket=self.bucket_name
                ).observe(duration)

                span.set_attribute("s3.duration_seconds", duration)
                span.set_attribute("s3.content_length", len(content))
                logger.info(f"Downloaded from S3: s3://{self.bucket_name}/{object_path}")
                return content

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                s3_operations_total.labels(
                    operation='download', status='error', bucket=self.bucket_name
                ).inc()
                span.set_attribute("error", True)
                span.set_attribute("error.code", error_code)

                if error_code == 'NoSuchKey':
                    logger.error(f"S3 object not found: s3://{self.bucket_name}/{object_path}")
                    raise StorageError(f"Object not found: {object_path}") from e
                logger.error(
                    f"S3 download failed: {error_code} - s3://{self.bucket_name}/{object_path}"
                )
                raise StorageError(f"S3 download failed: {error_code}") from e

            except BotoCoreError as e:
                s3_operations_total.labels(
                    operation='download', status='error', bucket=self.bucket_name
                ).inc()
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"S3 connection error during download: {e}")
                raise StorageError(f"S3 connection error: {e}") from e
