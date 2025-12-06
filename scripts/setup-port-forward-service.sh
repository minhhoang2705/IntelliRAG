#!/bin/bash
# Script to create kserve-port-forward systemd service

echo "Creating kserve-port-forward.service..."

sudo tee /etc/systemd/system/kserve-port-forward.service > /dev/null <<'EOF'
[Unit]
Description=KServe Port Forwarding for CloudFlare Tunnel
After=network.target

[Service]
Type=simple
User=minh-ubs-k8s
WorkingDirectory=/home/minh-ubs-k8s
ExecStart=/bin/bash -c '\
  # Wait for minikube to be ready \
  while ! kubectl --context=minikube get pods -n kserve >/dev/null 2>&1; do sleep 5; done; \
  # vLLM port forward \
  POD_NAME=$(kubectl --context=minikube get pods -n kserve -l serving.knative.dev/service=vllm-qwen-predictor -o jsonpath="{.items[0].metadata.name}") && \
  kubectl --context=minikube port-forward -n kserve pod/$POD_NAME 8000:8000 & \
  # Embedding port forward \
  POD_NAME=$(kubectl --context=minikube get pods -n kserve -l serving.knative.dev/service=embedding-service-predictor -o jsonpath="{.items[0].metadata.name}") && \
  kubectl --context=minikube port-forward -n kserve pod/$POD_NAME 8001:8001 & \
  wait'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

if [ $? -eq 0 ]; then
    echo "✅ kserve-port-forward.service created successfully at /etc/systemd/system/kserve-port-forward.service"
    sudo systemctl daemon-reload
    echo "✅ Systemd daemon reloaded"
else
    echo "❌ Failed to create kserve-port-forward.service"
    exit 1
fi
