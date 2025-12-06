"""
RAG Query Task Sets for Locust Load Testing
Defines reusable task sets for RAG endpoint testing
"""

import random
import json
from locust import TaskSet, task, between


# Query templates from different domains
QUERY_TEMPLATES = [
    # Machine Learning basics
    "What is machine learning?",
    "Explain supervised learning",
    "What is deep learning?",
    "Describe neural networks",

    # NLP and Transformers
    "How does RAG work?",
    "What are transformers in NLP?",
    "Explain attention mechanisms",
    "What is BERT?",

    # Algorithms
    "Describe gradient descent",
    "What is backpropagation?",
    "Explain the Adam optimizer",
    "How does SGD work?",

    # Computer Vision
    "What are convolutional neural networks?",
    "Explain image classification",
    "What is object detection?",
    "Describe transfer learning",

    # General AI
    "Difference between AI and ML?",
    "What is reinforcement learning?",
    "Explain model overfitting",
    "What is cross-validation?",
]

# Simple queries for quick tests
SIMPLE_QUERIES = [
    "Hello",
    "What is AI?",
    "Define ML",
    "Explain NLP",
]

# Complex multi-part queries
COMPLEX_QUERIES = [
    "Explain the difference between supervised and unsupervised learning, and provide examples of when to use each approach",
    "How do transformers work in natural language processing, and what makes them better than RNNs?",
    "Describe the complete training process for a neural network, including backpropagation and optimization",
    "What are the main challenges in deploying machine learning models to production, and how can they be addressed?",
]


class RAGQueryTaskSet(TaskSet):
    """Standard RAG query tasks with realistic distribution"""

    wait_time = between(1, 3)  # 1-3 seconds between requests

    def on_start(self):
        """Called when a user starts"""
        self.query_count = 0
        self.error_count = 0

    @task(10)  # 10x more likely than other tasks
    def query_rag_standard(self):
        """Standard RAG query with random question"""
        self.query_count += 1

        payload = {
            "query": random.choice(QUERY_TEMPLATES),
            "top_k": 5
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            catch_response=True,
            timeout=30,
            name="RAG Query (Standard)"
        ) as response:
            if not self._validate_response(response, "RAG Query"):
                self.error_count += 1

    @task(3)
    def query_rag_simple(self):
        """Simple quick queries"""
        payload = {
            "query": random.choice(SIMPLE_QUERIES),
            "top_k": 3
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            catch_response=True,
            timeout=15,
            name="RAG Query (Simple)"
        ) as response:
            self._validate_response(response, "Simple Query")

    @task(2)
    def query_rag_complex(self):
        """Complex multi-part queries"""
        payload = {
            "query": random.choice(COMPLEX_QUERIES),
            "top_k": 10
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            catch_response=True,
            timeout=60,
            name="RAG Query (Complex)"
        ) as response:
            self._validate_response(response, "Complex Query")

    @task(1)
    def health_check(self):
        """Health check endpoint"""
        with self.client.get(
            "/ready",
            catch_response=True,
            timeout=5,
            name="Health Check"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: HTTP {response.status_code}")

    def _validate_response(self, response, query_type):
        """Validate RAG response structure"""
        if response.status_code != 200:
            response.failure(f"{query_type} failed: HTTP {response.status_code}")
            return False

        try:
            data = response.json()

            # Check for required fields
            if "answer" not in data:
                response.failure(f"{query_type}: Missing 'answer' field")
                return False

            # Optional: Check for sources/context
            if "sources" in data and not isinstance(data["sources"], list):
                response.failure(f"{query_type}: Invalid 'sources' format")
                return False

            # Validate answer is not empty
            if not data["answer"] or not isinstance(data["answer"], str):
                response.failure(f"{query_type}: Empty or invalid answer")
                return False

            response.success()
            return True

        except json.JSONDecodeError:
            response.failure(f"{query_type}: Invalid JSON response")
            return False
        except Exception as e:
            response.failure(f"{query_type}: Validation error: {str(e)}")
            return False


class HighVolumeRAGTaskSet(RAGQueryTaskSet):
    """High-volume variant with faster requests"""

    wait_time = between(0.5, 1.5)  # Faster queries

    @task(15)  # Higher frequency
    def rapid_fire_queries(self):
        """Rapid-fire queries for stress testing"""
        payload = {
            "query": random.choice(SIMPLE_QUERIES),
            "top_k": 3
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            catch_response=True,
            timeout=20,
            name="RAG Query (Rapid)"
        ) as response:
            self._validate_response(response, "Rapid Query")


class ReadOnlyTaskSet(TaskSet):
    """Read-only tasks for baseline performance"""

    wait_time = between(1, 2)

    @task(5)
    def health_check(self):
        """Frequent health checks"""
        self.client.get("/ready", name="Health Check (Read-only)")

    @task(1)
    def metrics_endpoint(self):
        """Check metrics endpoint if available"""
        self.client.get("/metrics", name="Metrics Check")
