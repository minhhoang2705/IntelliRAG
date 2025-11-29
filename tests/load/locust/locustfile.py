"""
IntelliRAG End-to-End Load Testing with Locust
Main locustfile for orchestrating different user profiles and test scenarios

Usage Examples:

# Normal load (50 users)
locust -f locustfile.py --headless --users 50 --spawn-rate 5 --run-time 5m --html report.html

# Stress test (200 users)
locust -f locustfile.py --user-classes StressTestUser --headless --users 200 --spawn-rate 20 --run-time 3m

# Mixed user types (use web UI)
locust -f locustfile.py --host http://localhost:8000

# With custom host
locust -f locustfile.py --host https://intellirag.example.com
"""

import sys
import os
from locust import HttpUser, between, events
from locust.runners import MasterRunner, WorkerRunner

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from tasks.rag_tasks import RAGQueryTaskSet, HighVolumeRAGTaskSet


# Default test configuration
DEFAULT_HOST = "http://localhost:8000"


class DefaultRAGUser(HttpUser):
    """
    Default user profile when no specific class is selected
    Balanced mix of normal and power user behavior
    """

    tasks = [RAGQueryTaskSet]
    wait_time = between(1, 3)
    host = DEFAULT_HOST

    # Weight distribution
    weight = 3


class DefaultStressUser(HttpUser):
    """
    Default stress testing user
    Used when running stress tests via web UI
    """

    tasks = [HighVolumeRAGTaskSet]
    wait_time = between(0.5, 1)
    host = DEFAULT_HOST

    weight = 1


# Event listeners for custom metrics and reporting

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("=" * 60)
    print("IntelliRAG Load Test Starting")
    print("=" * 60)
    print(f"Target Host: {environment.host or DEFAULT_HOST}")
    print(f"Test Mode: {'Distributed' if isinstance(environment.runner, (MasterRunner, WorkerRunner)) else 'Standalone'}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops - print summary"""
    print("\n" + "=" * 60)
    print("IntelliRAG Load Test Complete")
    print("=" * 60)

    stats = environment.stats

    # Overall statistics
    print("\n📊 Overall Statistics:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Failed Requests: {stats.total.num_failures}")
    print(f"  Failure Rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"  Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"  RPS: {stats.total.total_rps:.2f}")

    # Request breakdown
    print("\n📈 Request Breakdown:")
    for name, stat in stats.entries.items():
        print(f"\n  {name}:")
        print(f"    Requests: {stat.num_requests}")
        print(f"    Failures: {stat.num_failures} ({stat.fail_ratio * 100:.2f}%)")
        print(f"    Avg: {stat.avg_response_time:.2f}ms")
        print(f"    P50: {stat.get_response_time_percentile(0.5):.2f}ms")
        print(f"    P95: {stat.get_response_time_percentile(0.95):.2f}ms")
        print(f"    P99: {stat.get_response_time_percentile(0.99):.2f}ms")

    # Errors summary
    if stats.errors:
        print("\n❌ Errors:")
        for error in stats.errors.values():
            print(f"  {error.method} {error.name}")
            print(f"    Count: {error.occurrences}")
            print(f"    Error: {error.error}")

    print("\n" + "=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests for debugging"""
    if response_time > 10000:  # Log requests slower than 10 seconds
        print(f"⚠️  Slow request detected: {name} took {response_time:.0f}ms")


# Shape classes for custom load patterns

try:
    from locust import LoadTestShape

    class StepLoadShape(LoadTestShape):
        """
        Step load pattern - gradually increase users
        Steps: 10 -> 25 -> 50 -> 75 -> 100 users
        """

        step_time = 60  # Each step lasts 60 seconds
        step_load = 25   # Increase by 25 users per step
        spawn_rate = 5
        time_limit = 300  # Total 5 minutes

        def tick(self):
            run_time = self.get_run_time()

            if run_time > self.time_limit:
                return None

            current_step = run_time // self.step_time
            user_count = min(current_step * self.step_load + 10, 100)

            return (user_count, self.spawn_rate)

    class SpikeLoadShape(LoadTestShape):
        """
        Spike load pattern - sudden traffic spike
        Pattern: 10 users -> 150 users -> 10 users
        """

        def tick(self):
            run_time = self.get_run_time()

            if run_time < 60:
                # Baseline: 10 users
                return (10, 2)
            elif run_time < 120:
                # Spike: 150 users
                return (150, 50)
            elif run_time < 240:
                # Recovery: back to 10 users
                return (10, 10)
            else:
                return None

except ImportError:
    # LoadTestShape not available in older locust versions
    pass


# Main execution
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("IntelliRAG Locust Load Test")
    print("=" * 60)
    print("\nAvailable User Classes:")
    print("  - NormalRAGUser (default, balanced)")
    print("  - CasualUser (low frequency)")
    print("  - PowerUser (high frequency)")
    print("  - StressTestUser (aggressive)")
    print("  - BurstUser (burst patterns)")
    print("  - SpikeUser (extreme load)")
    print("  - SustainedLoadUser (consistent load)")
    print("\nUsage:")
    print("  locust -f locustfile.py --host http://localhost:8000")
    print("  locust -f locustfile.py --user-classes StressTestUser --headless --users 100")
    print("=" * 60 + "\n")
