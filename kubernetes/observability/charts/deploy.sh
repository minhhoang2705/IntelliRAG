#!/bin/bash
# Deploy IntelliRAG Observability Stack
# Usage: ./deploy.sh [prometheus|loki|jaeger|all]

set -e

NAMESPACE="observability"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create namespace if it doesn't exist
create_namespace() {
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        log_info "Creating namespace: $NAMESPACE"
        kubectl create namespace $NAMESPACE
    else
        log_info "Namespace $NAMESPACE already exists"
    fi
}

# Deploy Prometheus
deploy_prometheus() {
    log_info "Deploying Prometheus..."
    cd "$SCRIPT_DIR/prometheus"
    
    log_info "Building dependencies..."
    helm dependency build
    
    log_info "Installing/Upgrading Prometheus..."
    helm upgrade --install prometheus . \
        --namespace $NAMESPACE \
        --wait \
        --timeout 10m
    
    log_info "✅ Prometheus deployed successfully"
    cd "$SCRIPT_DIR"
}

# Deploy Loki
deploy_loki() {
    log_info "Deploying Loki..."
    cd "$SCRIPT_DIR/loki"
    
    log_info "Building dependencies..."
    helm dependency build
    
    log_info "Installing/Upgrading Loki..."
    helm upgrade --install loki . \
        --namespace $NAMESPACE \
        --wait \
        --timeout 10m
    
    log_info "✅ Loki deployed successfully"
    cd "$SCRIPT_DIR"
}

# Deploy Jaeger
deploy_jaeger() {
    log_info "Deploying Jaeger..."
    cd "$SCRIPT_DIR/jaeger"
    
    log_info "Building dependencies..."
    helm dependency build
    
    log_info "Installing/Upgrading Jaeger..."
    helm upgrade --install jaeger . \
        --namespace $NAMESPACE \
        --wait \
        --timeout 10m
    
    log_info "✅ Jaeger deployed successfully"
    cd "$SCRIPT_DIR"
}

# Deploy Grafana
deploy_grafana() {
    log_info "Deploying Grafana..."
    cd "$SCRIPT_DIR/grafana"
    
    log_info "Building dependencies..."
    helm dependency build
    
    log_info "Installing/Upgrading Grafana..."
    helm upgrade --install grafana . \
        --namespace $NAMESPACE \
        --wait \
        --timeout 5m
    
    log_info "✅ Grafana deployed successfully"
    cd "$SCRIPT_DIR"
}

# Show access instructions
show_access_info() {
    echo ""
    log_info "=========================================="
    log_info "Observability Stack Access Information"
    log_info "=========================================="
    echo ""
    echo "Prometheus:"
    echo "  kubectl port-forward -n $NAMESPACE svc/prometheus-kube-prometheus-prometheus 9090:9090"
    echo "  Visit: http://localhost:9090"
    echo ""
    echo "Loki:"
    echo "  kubectl port-forward -n $NAMESPACE svc/loki-gateway 3100:80"
    echo "  Query: http://localhost:3100"
    echo ""
    echo "Jaeger:"
    echo "  kubectl port-forward -n $NAMESPACE svc/jaeger-query 16686:16686"
    echo "  Visit: http://localhost:16686"
    echo ""
    echo "Grafana:"
    echo "  kubectl port-forward -n $NAMESPACE svc/grafana 3000:80"
    echo "  Visit: http://localhost:3000"
    echo "  Login: admin / admin"
    echo ""
    log_info "=========================================="
}

# Check deployment status
check_status() {
    log_info "Checking deployment status..."
    echo ""
    kubectl get pods -n $NAMESPACE
    echo ""
    kubectl get svc -n $NAMESPACE
}

# Main deployment logic
main() {
    local component=${1:-all}
    
    log_info "Starting deployment: $component"
    
    create_namespace
    
    case $component in
        prometheus)
            deploy_prometheus
            ;;
        loki)
            deploy_loki
            ;;
        jaeger)
            deploy_jaeger
            ;;
        grafana)
            deploy_grafana
            ;;
        all)
            deploy_prometheus
            deploy_loki
            deploy_jaeger
            deploy_grafana
            ;;
        *)
            log_error "Unknown component: $component"
            echo "Usage: $0 [prometheus|loki|jaeger|grafana|all]"
            exit 1
            ;;
    esac
    
    check_status
    show_access_info
    
    log_info "Deployment complete! 🎉"
}

# Run main function
main "$@"

