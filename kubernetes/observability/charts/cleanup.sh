#!/bin/bash
# Cleanup IntelliRAG Observability Stack
# Usage: ./cleanup.sh [prometheus|loki|jaeger|all]

set -e

NAMESPACE="observability"

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

# Uninstall Prometheus
cleanup_prometheus() {
    log_info "Uninstalling Prometheus..."
    helm uninstall prometheus -n $NAMESPACE 2>/dev/null || log_warn "Prometheus not found or already uninstalled"
    
    # Clean up PVCs
    log_info "Cleaning up Prometheus PVCs..."
    kubectl delete pvc -n $NAMESPACE -l app.kubernetes.io/name=prometheus 2>/dev/null || true
    
    log_info "✅ Prometheus cleanup complete"
}

# Uninstall Loki
cleanup_loki() {
    log_info "Uninstalling Loki..."
    helm uninstall loki -n $NAMESPACE 2>/dev/null || log_warn "Loki not found or already uninstalled"
    
    # Clean up PVCs
    log_info "Cleaning up Loki PVCs..."
    kubectl delete pvc -n $NAMESPACE -l app.kubernetes.io/name=loki 2>/dev/null || true
    kubectl delete pvc -n $NAMESPACE -l app=loki 2>/dev/null || true
    
    log_info "✅ Loki cleanup complete"
}

# Uninstall Jaeger
cleanup_jaeger() {
    log_info "Uninstalling Jaeger..."
    helm uninstall jaeger -n $NAMESPACE 2>/dev/null || log_warn "Jaeger not found or already uninstalled"
    
    # Clean up PVCs
    log_info "Cleaning up Jaeger/Elasticsearch PVCs..."
    kubectl delete pvc -n $NAMESPACE -l app.kubernetes.io/name=jaeger 2>/dev/null || true
    kubectl delete pvc -n $NAMESPACE -l app=elasticsearch 2>/dev/null || true
    kubectl delete pvc -n $NAMESPACE -l app.kubernetes.io/component=elasticsearch 2>/dev/null || true
    
    log_info "✅ Jaeger cleanup complete"
}

# Uninstall Grafana
cleanup_grafana() {
    log_info "Uninstalling Grafana..."
    helm uninstall grafana -n $NAMESPACE 2>/dev/null || log_warn "Grafana not found or already uninstalled"
    
    # Clean up PVCs
    log_info "Cleaning up Grafana PVCs..."
    kubectl delete pvc -n $NAMESPACE -l app.kubernetes.io/name=grafana 2>/dev/null || true
    
    log_info "✅ Grafana cleanup complete"
}

# Delete namespace
delete_namespace() {
    log_warn "Deleting namespace: $NAMESPACE"
    read -p "Are you sure? This will delete all resources in the namespace. (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete namespace $NAMESPACE 2>/dev/null || log_warn "Namespace not found"
        log_info "✅ Namespace deleted"
    else
        log_info "Namespace deletion cancelled"
    fi
}

# Main cleanup logic
main() {
    local component=${1:-all}
    
    log_warn "Starting cleanup: $component"
    
    case $component in
        prometheus)
            cleanup_prometheus
            ;;
        loki)
            cleanup_loki
            ;;
        jaeger)
            cleanup_jaeger
            ;;
        grafana)
            cleanup_grafana
            ;;
        all)
            cleanup_prometheus
            cleanup_loki
            cleanup_jaeger
            cleanup_grafana
            echo ""
            delete_namespace
            ;;
        *)
            echo "Unknown component: $component"
            echo "Usage: $0 [prometheus|loki|jaeger|grafana|all]"
            exit 1
            ;;
    esac
    
    log_info "Cleanup complete! 🧹"
}

# Run main function
main "$@"

