"""
Normal User Behavior Profiles for Locust Load Testing
Simulates realistic user patterns
"""

from locust import HttpUser, between
from tasks.rag_tasks import RAGQueryTaskSet, ReadOnlyTaskSet


class NormalRAGUser(HttpUser):
    """
    Normal user behavior - realistic query patterns

    Characteristics:
    - Moderate think time (1-3 seconds)
    - Mix of query types
    - Occasional health checks
    - Simulates typical user interaction
    """

    tasks = {RAGQueryTaskSet: 10, ReadOnlyTaskSet: 1}
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        """Initialize user session"""
        print(f"NormalRAGUser {self.client.base_url} started")


class CasualUser(HttpUser):
    """
    Casual user - infrequent queries

    Characteristics:
    - Long think time (3-8 seconds)
    - Mostly simple queries
    - Lower query rate
    """

    tasks = [RAGQueryTaskSet]
    wait_time = between(3, 8)
    host = "http://localhost:8000"


class PowerUser(HttpUser):
    """
    Power user - frequent complex queries

    Characteristics:
    - Short think time (0.5-2 seconds)
    - More complex queries
    - Higher query rate
    """

    tasks = [RAGQueryTaskSet]
    wait_time = between(0.5, 2)
    host = "http://localhost:8000"

    def on_start(self):
        """Power user initialization"""
        print(f"PowerUser {self.client.base_url} started (high frequency)")
