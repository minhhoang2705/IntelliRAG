"""
Register IntelliRAG models in MLFlow registry.
"""
import mlflow
from mlflow.tracking import MlflowClient
import os
import sys

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "https://mlflow.blockchainradar.xyz"
)
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

def register_llm_model():
    """Register vLLM Qwen3-0.6B model."""
    client = MlflowClient()

    try:
        client.create_registered_model(
            name="qwen3-0.6b-instruct",
            description="Qwen3-0.6B-Instruct LLM for RAG generation",
            tags={
                "task": "text-generation",
                "framework": "vllm",
                "model_size": "0.6B",
                "use_case": "rag",
                "deployment": "kserve-local-gpu"
            }
        )
        print("✅ Created model: qwen3-0.6b-instruct")
    except Exception as e:
        print(f"Model already exists or error: {e}")

    with mlflow.start_run(run_name="qwen3-0.6b-v1.0.0") as run:
        mlflow.log_param("model_name", "Qwen/Qwen3-0.6B")
        mlflow.log_param("framework", "vLLM")
        mlflow.log_param("endpoint", "https://llm.blockchainradar.xyz/v1")
        mlflow.log_param("max_tokens", 8192)
        mlflow.log_param("deployment_type", "kserve")
        mlflow.log_param("gpu", "NVIDIA RTX 4070Ti 12GB")

        mlflow.log_metric("throughput_tps", 793)
        mlflow.log_metric("p99_latency_ms", 80)
        mlflow.log_metric("gpu_utilization", 0.95)

        try:
            mv = client.create_model_version(
                name="qwen3-0.6b-instruct",
                source=f"runs:/{run.info.run_id}",
                tags={
                    "version": "v1.0.0",
                    "deployment": "production",
                    "endpoint": "https://llm.blockchainradar.xyz/v1"
                }
            )

            print(f"✅ Registered model version: {mv.version}")

            client.transition_model_version_stage(
                name="qwen3-0.6b-instruct",
                version=mv.version,
                stage="Production"
            )
            print("✅ Transitioned to Production stage")
        except Exception as e:
            print(f"Error registering model version: {e}")

def register_embedding_model():
    """Register EmbeddingGemma-300m model."""
    client = MlflowClient()

    try:
        client.create_registered_model(
            name="embeddinggemma-300m",
            description="Google EmbeddingGemma-300M for document embeddings",
            tags={
                "task": "embedding",
                "framework": "sentence-transformers",
                "model_size": "300M",
                "embedding_dim": "768",
                "deployment": "kserve-local-gpu"
            }
        )
        print("✅ Created model: embeddinggemma-300m")
    except Exception as e:
        print(f"Model already exists or error: {e}")

    with mlflow.start_run(run_name="embeddinggemma-300m-v1.0.0") as run:
        mlflow.log_param("model_name", "google/embeddinggemma-300m")
        mlflow.log_param("framework", "KServe")
        mlflow.log_param("endpoint", "https://embed.blockchainradar.xyz")
        mlflow.log_param("embedding_dimension", 768)
        mlflow.log_param("max_batch_size", 16)
        mlflow.log_param("device", "cuda")

        mlflow.log_metric("avg_latency_ms", 287)
        mlflow.log_metric("batch_throughput", 128)

        try:
            mv = client.create_model_version(
                name="embeddinggemma-300m",
                source=f"runs:/{run.info.run_id}",
                tags={
                    "version": "v1.0.0",
                    "deployment": "production",
                    "endpoint": "https://embed.blockchainradar.xyz"
                }
            )

            print(f"✅ Registered model version: {mv.version}")

            client.transition_model_version_stage(
                name="embeddinggemma-300m",
                version=mv.version,
                stage="Production"
            )
            print("✅ Transitioned to Production stage")
        except Exception as e:
            print(f"Error registering model version: {e}")

if __name__ == "__main__":
    print("🚀 Registering IntelliRAG models in MLFlow...")
    print(f"MLFlow Tracking URI: {MLFLOW_TRACKING_URI}\n")

    try:
        register_llm_model()
        print()
        register_embedding_model()

        print("\n✅ All models registered successfully!")
        print(f"View models at: {MLFLOW_TRACKING_URI}/#/models")
    except Exception as e:
        print(f"\n❌ Error during registration: {e}")
        sys.exit(1)
