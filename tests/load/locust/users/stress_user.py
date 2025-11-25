"""
Stress Test User Behavior Profiles
Aggressive patterns for finding system limits
"""

from locust import HttpUser, between
from tasks.rag_tasks import HighVolumeRAGTaskSet, RAGQueryTaskSet


class StressTestUser(HttpUser):
    """
    Stress test user - aggressive query patterns

    Characteristics:
    - Minimal think time (0.5-1 second)
    - Rapid-fire queries
    - High concurrency
    - Tests system under pressure
    """

    tasks = [HighVolumeRAGTaskSet]
    wait_time = between(0.5, 1)
    host = "http://localhost:8000"

    def on_start(self):
        """Stress user initialization"""
        print(f"StressTestUser {self.client.base_url} started (stress mode)")


class BurstUser(HttpUser):
    """
    Burst pattern user - sudden spikes

    Characteristics:
    - Alternates between idle and burst
    - Simulates traffic spikes
    - No wait time during burst
    """

    tasks = [HighVolumeRAGTaskSet]
    wait_time = between(0, 0.5)  # Minimal wait for burst
    host = "http://localhost:8000"

    def on_start(self):
        """Burst user initialization"""
        self.burst_count = 0
        print(f"BurstUser {self.client.base_url} started (burst mode)")


class SpikeUser(HttpUser):
    """
    Spike user - extreme load simulation

    Characteristics:
    - No think time
    - Maximum query rate
    - Tests breaking points
    """

    tasks = [HighVolumeRAGTaskSet]
    wait_time = between(0, 0.2)  # Almost no wait
    host = "http://localhost:8000"

    def on_start(self):
        """Spike user initialization"""
        print(f"SpikeUser {self.client.base_url} started (spike mode - maximum load)")


class SustainedLoadUser(HttpUser):
    """
    Sustained load user - consistent pressure

    Characteristics:
    - Consistent query rate
    - Medium frequency
    - Tests stability over time
    """

    tasks = [RAGQueryTaskSet]
    wait_time = between(1, 2)  # Consistent wait
    host = "http://localhost:8000"

    def on_start(self):
        """Sustained load user initialization"""
        print(f"SustainedLoadUser {self.client.base_url} started (sustained load)")
