"""HTTP Metrics Middleware for Prometheus instrumentation."""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from app.api.middleware.metrics import (
    http_requests_total,
    http_request_duration_seconds
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request and track metrics."""
        # Start timing
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Track request count
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=str(response.status_code)
        ).inc()

        # Track request duration
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response
