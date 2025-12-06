#!/usr/bin/env python3
"""Simple E2E RAG load test to verify service connectivity."""

import asyncio
import httpx
import time
from datetime import datetime
import json

# Test configuration
BASE_URL = "http://localhost:8002"
NUM_REQUESTS = 20
CONCURRENT_USERS = 5
TIMEOUT = 30.0

# Test queries
QUERIES = [
    "What is machine learning?",
    "Explain neural networks",
    "How does RAG work?",
    "What are transformers?",
    "Describe deep learning",
]

results = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "response_times": [],
    "errors": {},
    "start_time": None,
    "end_time": None,
}


async def test_query(client: httpx.AsyncClient, query: str, request_id: int):
    """Test a single query request."""
    try:
        start = time.time()
        response = await client.post(
            f"{BASE_URL}/api/v1/query",
            json={"query": query},
            timeout=TIMEOUT,
        )
        duration = (time.time() - start) * 1000  # Convert to ms

        results["total_requests"] += 1
        results["response_times"].append(duration)

        if response.status_code == 200:
            results["successful_requests"] += 1
            data = response.json()
            # Check if we got expected fields
            has_answer = "answer" in data
            has_sources = "sources" in data
            return {
                "id": request_id,
                "status": "success",
                "duration_ms": duration,
                "has_answer": has_answer,
                "has_sources": has_sources,
                "answer_length": len(data.get("answer", "")),
            }
        else:
            results["failed_requests"] += 1
            error_key = f"HTTP_{response.status_code}"
            results["errors"][error_key] = results["errors"].get(error_key, 0) + 1
            return {
                "id": request_id,
                "status": "failed",
                "duration_ms": duration,
                "error": f"HTTP {response.status_code}",
            }
    except Exception as e:
        results["failed_requests"] += 1
        error_type = type(e).__name__
        results["errors"][error_type] = results["errors"].get(error_type, 0) + 1
        return {
            "id": request_id,
            "status": "error",
            "error": str(e),
        }


async def test_health_endpoints(client: httpx.AsyncClient):
    """Test health and readiness endpoints."""
    health_results = {}

    try:
        # Test root health endpoint
        response = await client.get(f"{BASE_URL}/", timeout=5.0)
        health_results["root"] = {
            "status": response.status_code,
            "healthy": response.status_code == 200,
        }

        # Test readiness endpoint
        response = await client.get(f"{BASE_URL}/ready", timeout=5.0)
        health_results["ready"] = {
            "status": response.status_code,
            "healthy": response.status_code == 200,
            "data": response.json() if response.status_code == 200 else None,
        }

        # Test metrics endpoint
        response = await client.get(f"{BASE_URL}/metrics", timeout=5.0)
        health_results["metrics"] = {
            "status": response.status_code,
            "healthy": response.status_code == 200,
        }

    except Exception as e:
        health_results["error"] = str(e)

    return health_results


async def run_load_test():
    """Run the load test."""
    print("=" * 60)
    print("Simple E2E RAG Load Test")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Total Requests: {NUM_REQUESTS}")
    print(f"Concurrent Users: {CONCURRENT_USERS}")
    print(f"Timeout: {TIMEOUT}s")
    print("=" * 60)
    print()

    async with httpx.AsyncClient() as client:
        # Step 1: Test health endpoints
        print("Step 1: Testing health endpoints...")
        health_results = await test_health_endpoints(client)
        print(json.dumps(health_results, indent=2))
        print()

        all_healthy = all(
            endpoint.get("healthy", False)
            for endpoint in health_results.values()
            if isinstance(endpoint, dict)
        )

        if not all_healthy:
            print("❌ Health check failed. Aborting load test.")
            return

        print("✅ All health endpoints passed")
        print()

        # Step 2: Run load test
        print(f"Step 2: Running load test ({NUM_REQUESTS} requests)...")
        results["start_time"] = datetime.now()

        tasks = []
        for i in range(NUM_REQUESTS):
            query = QUERIES[i % len(QUERIES)]
            task = test_query(client, query, i + 1)
            tasks.append(task)

            # Control concurrency
            if len(tasks) >= CONCURRENT_USERS:
                completed = await asyncio.gather(*tasks)
                tasks = []
                # Small delay between batches
                await asyncio.sleep(0.1)

        # Complete remaining tasks
        if tasks:
            await asyncio.gather(*tasks)

        results["end_time"] = datetime.now()

    # Calculate statistics
    duration_s = (results["end_time"] - results["start_time"]).total_seconds()
    success_rate = (results["successful_requests"] / results["total_requests"] * 100) if results["total_requests"] > 0 else 0

    response_times = results["response_times"]
    if response_times:
        response_times.sort()
        avg_latency = sum(response_times) / len(response_times)
        p50_latency = response_times[len(response_times) // 2]
        p95_latency = response_times[int(len(response_times) * 0.95)]
        p99_latency = response_times[int(len(response_times) * 0.99)]
    else:
        avg_latency = p50_latency = p95_latency = p99_latency = 0

    # Print results
    print()
    print("=" * 60)
    print("Test Results")
    print("=" * 60)
    print(f"Total Duration: {duration_s:.2f}s")
    print(f"Total Requests: {results['total_requests']}")
    print(f"Successful: {results['successful_requests']}")
    print(f"Failed: {results['failed_requests']}")
    print(f"Success Rate: {success_rate:.1f}%")
    print()
    print("Latency Statistics:")
    print(f"  Average: {avg_latency:.0f}ms")
    print(f"  P50: {p50_latency:.0f}ms")
    print(f"  P95: {p95_latency:.0f}ms")
    print(f"  P99: {p99_latency:.0f}ms")

    if results["errors"]:
        print()
        print("Errors:")
        for error_type, count in results["errors"].items():
            print(f"  {error_type}: {count}")

    print("=" * 60)

    # Return status
    if success_rate >= 95:
        print("✅ Test PASSED - All services connected and functional")
        return 0
    elif success_rate >= 80:
        print("⚠️  Test PARTIAL - Some issues detected but services are accessible")
        return 1
    else:
        print("❌ Test FAILED - Significant connectivity issues")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(run_load_test())
    exit(exit_code)
