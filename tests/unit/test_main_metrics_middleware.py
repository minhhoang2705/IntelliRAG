"""Test that MetricsMiddleware is integrated into main FastAPI app.

Following TDD: This test will FAIL until we add MetricsMiddleware to main.py.
"""


def test_metrics_middleware_added_to_main_app():
    """Test that MetricsMiddleware is added to main FastAPI app.

    Expected to FAIL: MetricsMiddleware not yet added to main.py
    """
    from app.main import app
    from app.api.middleware.metrics_middleware import MetricsMiddleware

    # Check if MetricsMiddleware is in the middleware stack
    middleware_found = False
    for middleware in app.user_middleware:
        if middleware.cls == MetricsMiddleware:
            middleware_found = True
            break

    assert middleware_found, \
        "MetricsMiddleware not found in app.user_middleware - add it via app.add_middleware(MetricsMiddleware)"
