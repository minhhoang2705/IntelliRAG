"""Unit tests for ingestion pipeline metrics.

Tests verify that all required metrics are defined with correct types,
labels, and buckets for monitoring the document ingestion pipeline.
"""

from prometheus_client import Counter, Gauge, Histogram


class TestIngestionMetricsDefinitions:
    """Test that ingestion metrics are properly defined."""

    def test_ingestion_jobs_total_counter_exists(self):
        """Test ingestion_jobs_total Counter is defined with correct labels."""
        from app.api.middleware.metrics import ingestion_jobs_total

        assert isinstance(ingestion_jobs_total, Counter)
        # Prometheus Client strips _total suffix from Counter names internally
        assert ingestion_jobs_total._name == 'ingestion_jobs'
        assert 'status' in ingestion_jobs_total._labelnames
        assert 'file_type' in ingestion_jobs_total._labelnames

    def test_ingestion_jobs_active_gauge_exists(self):
        """Test ingestion_jobs_active Gauge is defined with correct labels."""
        from app.api.middleware.metrics import ingestion_jobs_active

        assert isinstance(ingestion_jobs_active, Gauge)
        assert ingestion_jobs_active._name == 'ingestion_jobs_active'
        assert 'status' in ingestion_jobs_active._labelnames

    def test_file_upload_duration_histogram_exists(self):
        """Test file_upload_duration_seconds Histogram is defined."""
        from app.api.middleware.metrics import file_upload_duration_seconds

        assert isinstance(file_upload_duration_seconds, Histogram)
        assert file_upload_duration_seconds._name == 'file_upload_duration_seconds'
        assert 'file_type' in file_upload_duration_seconds._labelnames

    def test_file_upload_size_histogram_exists(self):
        """Test file_upload_size_bytes Histogram is defined."""
        from app.api.middleware.metrics import file_upload_size_bytes

        assert isinstance(file_upload_size_bytes, Histogram)
        assert file_upload_size_bytes._name == 'file_upload_size_bytes'
        assert 'file_type' in file_upload_size_bytes._labelnames

    def test_document_processing_stage_duration_histogram_exists(self):
        """Test document_processing_stage_duration_seconds Histogram is defined."""
        from app.api.middleware.metrics import document_processing_stage_duration_seconds

        assert isinstance(document_processing_stage_duration_seconds, Histogram)
        assert document_processing_stage_duration_seconds._name == 'document_processing_stage_duration_seconds'
        assert 'stage' in document_processing_stage_duration_seconds._labelnames
        assert 'file_type' in document_processing_stage_duration_seconds._labelnames

    def test_ingestion_chunks_created_histogram_exists(self):
        """Test ingestion_chunks_created Histogram is defined."""
        from app.api.middleware.metrics import ingestion_chunks_created

        assert isinstance(ingestion_chunks_created, Histogram)
        assert ingestion_chunks_created._name == 'ingestion_chunks_created'
        assert 'file_type' in ingestion_chunks_created._labelnames

    def test_ingestion_job_duration_histogram_exists(self):
        """Test ingestion_job_duration_seconds Histogram is defined."""
        from app.api.middleware.metrics import ingestion_job_duration_seconds

        assert isinstance(ingestion_job_duration_seconds, Histogram)
        assert ingestion_job_duration_seconds._name == 'ingestion_job_duration_seconds'
        assert 'status' in ingestion_job_duration_seconds._labelnames
        assert 'file_type' in ingestion_job_duration_seconds._labelnames

    def test_ingestion_errors_total_counter_exists(self):
        """Test ingestion_errors_total Counter is defined."""
        from app.api.middleware.metrics import ingestion_errors_total

        assert isinstance(ingestion_errors_total, Counter)
        assert ingestion_errors_total._name == 'ingestion_errors'
        assert 'error_type' in ingestion_errors_total._labelnames
        assert 'stage' in ingestion_errors_total._labelnames
