#!/bin/bash
# Setup KServe locally with Minikube
# Usage: ./scripts/setup-kserve-local.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}IntelliRAG KServe Local Setup Script${NC}"
echo -e "${GREEN}======================================${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists kubectl; then
    print_status "kubectl not found. Installing..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/
    print_success "kubectl installed"
fi

if ! command_exists minikube; then
    print_status "minikube not found. Installing..."
    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
    sudo install minikube-linux-amd64 /usr/local/bin/minikube
    rm minikube-linux-amd64
    print_success "minikube installed"
fi

# Check GPU
print_status "Checking GPU..."
if ! nvidia-smi &>/dev/null; then
    print_error "NVIDIA GPU not detected. Please ensure NVIDIA drivers are installed."
    exit 1
fi
print_success "GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader)"

# Start minikube if not running
print_status "Checking minikube status..."
if ! minikube status &>/dev/null; then
    print_status "Starting minikube with GPU support..."
    minikube start \
        --driver=docker \
        --container-runtime=docker \
        --gpus=all \
        --memory=12288 \
        --cpus=4 \
        --disk-size=50g \
        --kubernetes-version=v1.28.0
    print_success "Minikube started"
else
    print_success "Minikube is already running"
fi

# Install NVIDIA device plugin
print_status "Installing NVIDIA device plugin..."
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml --dry-run=client -o yaml | kubectl apply -f -
sleep 5
kubectl rollout status daemonset nvidia-device-plugin-daemonset -n kube-system --timeout=120s
print_success "NVIDIA device plugin installed"

# Verify GPU
GPU_COUNT=$(kubectl get nodes -o jsonpath='{.items[*].status.allocatable.nvidia\.com/gpu}')
if [ "$GPU_COUNT" = "1" ]; then
    print_success "GPU available to Kubernetes: $GPU_COUNT"
else
    print_error "GPU not available to Kubernetes"
    exit 1
fi

# Install cert-manager
print_status "Installing cert-manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml
print_status "Waiting for cert-manager to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-cainjector -n cert-manager
print_success "cert-manager installed"

# Install Istio
print_status "Installing Istio..."
if ! command_exists istioctl; then
    print_status "Downloading Istio..."
    cd /tmp
    curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.0 sh -
    sudo mv istio-1.20.0/bin/istioctl /usr/local/bin/
    rm -rf istio-1.20.0
    cd - > /dev/null
fi

istioctl install --set profile=default -y
kubectl label namespace default istio-injection=enabled --overwrite
print_success "Istio installed"

# Install Knative Serving
print_status "Installing Knative Serving..."
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-core.yaml
print_status "Waiting for Knative Serving to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/controller -n knative-serving
kubectl wait --for=condition=available --timeout=300s deployment/webhook -n knative-serving
print_success "Knative Serving installed"

# Install Knative Istio controller
print_status "Installing Knative Istio controller..."
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.12.0/net-istio.yaml

# Configure Knative features
kubectl patch configmap/config-features \
    -n knative-serving \
    --type merge \
    -p '{"data":{"kubernetes.podspec-affinity":"enabled", "kubernetes.podspec-nodeselector":"enabled", "kubernetes.podspec-tolerations":"enabled"}}'
print_success "Knative configured"

# Install KServe
print_status "Installing KServe..."
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.12.0/kserve.yaml
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.12.0/kserve-cluster-resources.yaml
print_status "Waiting for KServe to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/kserve-controller-manager -n kserve
kubectl wait --for=condition=available --timeout=300s deployment/kserve-webhook-server-deployment -n kserve
print_success "KServe installed"

# Configure KServe for local development
print_status "Configuring KServe..."
kubectl patch configmap/config-domain \
    -n knative-serving \
    --type merge \
    -p '{"data":{"example.com":""}}'

kubectl apply -f - <<EOF
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: PERMISSIVE
EOF

kubectl patch configmap/inferenceservice-config \
    -n kserve \
    --type merge \
    -p '{"data":{"deploy":"{\"defaultDeploymentMode\":\"RawDeployment\"}"}}'
print_success "KServe configured"

# Create IntelliRAG namespace
print_status "Creating IntelliRAG namespace..."
kubectl create namespace intellirag --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace intellirag istio-injection=enabled --overwrite
print_success "Namespace created"

# Summary
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Next steps:"
echo "1. Build and load embedding service image:"
echo "   docker build -t intellirag-embedding:latest deploy/embedding-service/"
echo "   minikube image load intellirag-embedding:latest"
echo ""
echo "2. Deploy InferenceServices:"
echo "   kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml"
echo "   kubectl apply -f kubernetes/kserve/embedding-bge-m3-inference.yaml"
echo ""
echo "3. Wait for services to be ready:"
echo "   kubectl get inferenceservice -n intellirag -w"
echo ""
echo "4. Set up port forwarding:"
echo "   kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080 &"
echo "   kubectl port-forward -n intellirag svc/embedding-bge-m3-predictor 8001:8001 &"
echo ""
echo "See docs/deployment/local-kserve-setup-guide.md for detailed instructions."
echo ""

