#!/bin/bash

# IntelliRAG GKE Verification Script
# This script verifies that the GKE cluster is properly configured

PROJECT_ID="intellirag-aide1-capstone"
REGION="asia-southeast1"
CLUSTER_NAME="intellirag-cluster"

echo "========================================="
echo "IntelliRAG GKE Verification"
echo "========================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Helper function for tests
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo -n "Testing: $test_name... "
    if eval "$test_command" &>/dev/null; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
        return 1
    fi
}

echo "[1/10] Cluster Connectivity Tests"
echo "=================================="
run_test "kubectl configured" "kubectl cluster-info"
run_test "Cluster accessible" "kubectl get nodes"
run_test "System pods running" "kubectl get pods -n kube-system"

echo ""
echo "[2/10] Namespace Tests"
echo "====================="
run_test "app namespace exists" "kubectl get namespace app"
run_test "observability namespace exists" "kubectl get namespace observability"

echo ""
echo "[3/10] Service Account Tests"
echo "============================="
run_test "intellirag-app SA exists" "kubectl get sa intellirag-app -n app"
run_test "observability-sa SA exists" "kubectl get sa observability-sa -n observability"

echo ""
echo "[4/10] RBAC Tests"
echo "================="
run_test "app-role exists" "kubectl get role app-role -n app"
run_test "app-role-binding exists" "kubectl get rolebinding app-role-binding -n app"
run_test "kserve-role exists" "kubectl get clusterrole kserve-role"
run_test "kserve-role-binding exists" "kubectl get clusterrolebinding kserve-role-binding"

echo ""
echo "[5/10] Storage Tests"
echo "===================="
run_test "StorageClass exists" "kubectl get storageclass standard-rwo"

echo ""
echo "[6/10] Workload Identity Tests"
echo "==============================="
echo -n "Testing: Workload Identity annotation... "
ANNOTATION=$(kubectl get sa intellirag-app -n app -o jsonpath='{.metadata.annotations.iam\.gke\.io/gcp-service-account}')
if [[ "$ANNOTATION" == "intellirag-cluster-workload-sa@${PROJECT_ID}.iam.gserviceaccount.com" ]]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Expected: intellirag-cluster-workload-sa@${PROJECT_ID}.iam.gserviceaccount.com"
    echo "  Got: $ANNOTATION"
    ((FAILED++))
fi

echo ""
echo "[7/10] GCS Bucket Tests"
echo "======================="
run_test "Terraform state bucket exists" "gsutil ls gs://intellirag-aide1-capstone-terraform-state"
run_test "Models bucket exists" "gsutil ls gs://intellirag-aide1-capstone-models"
run_test "Data bucket exists" "gsutil ls gs://intellirag-aide1-capstone-data"

echo ""
echo "[8/10] Pod Scheduling Test"
echo "==========================="
echo -n "Testing: Pod can be scheduled... "
kubectl run test-nginx --image=nginx --restart=Never -n app &>/dev/null
if kubectl wait --for=condition=Ready pod/test-nginx -n app --timeout=60s &>/dev/null; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
    kubectl delete pod test-nginx -n app &>/dev/null
else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
    kubectl delete pod test-nginx -n app &>/dev/null 2>&1 || true
fi

echo ""
echo "[9/10] Workload Identity Access Test"
echo "====================================="
echo -n "Testing: GCS access from pod... "

# Create test pod with Workload Identity
cat <<EOF | kubectl apply -f - &>/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: workload-identity-test
  namespace: app
spec:
  serviceAccountName: intellirag-app
  containers:
  - name: gcloud
    image: google/cloud-sdk:slim
    command: ["sleep", "300"]
EOF

# Wait for pod to be ready
if kubectl wait --for=condition=Ready pod/workload-identity-test -n app --timeout=60s &>/dev/null; then
    # Test GCS access
    sleep 5
    if kubectl exec workload-identity-test -n app -- gsutil ls gs://intellirag-aide1-capstone-models &>/dev/null; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  Pod cannot access GCS bucket"
        ((FAILED++))
    fi
else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Pod failed to start"
    ((FAILED++))
fi

# Cleanup
kubectl delete pod workload-identity-test -n app &>/dev/null

echo ""
echo "[10/10] Cluster Info"
echo "===================="
kubectl get nodes -o wide
echo ""

echo "========================================="
echo "Verification Results"
echo "========================================="
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! GKE cluster is ready.${NC}"
    echo ""
    echo "Next Steps:"
    echo "==========="
    echo "1. Deploy observability stack (Phase 1)"
    echo "2. Deploy application services (Phase 1)"
    echo "3. Setup local minikube for KServe (Phase 2)"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "================"
    echo "- Ensure Terraform apply completed successfully"
    echo "- Verify all Kubernetes manifests were applied"
    echo "- Check GCS buckets were created"
    echo "- Review IAM bindings for Workload Identity"
    exit 1
fi
