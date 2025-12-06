#!/bin/bash
# Main Load Test Orchestrator
# Runs complete Day 2 load testing suite for IntelliRAG

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${SCRIPT_DIR}/scripts"
LOCUST_DIR="${SCRIPT_DIR}/locust"
REPORTS_DIR="${SCRIPT_DIR}/reports"
RESULTS_DIR="${SCRIPT_DIR}/results"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Test configuration
RUN_VLLM=1
RUN_EMBEDDING=1
RUN_E2E=1
SKIP_BREAKING=0
VERBOSE=""

# Usage
usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Run complete Day 2 load testing suite for IntelliRAG.

Options:
  --vllm-only          Run only vLLM tests
  --embedding-only     Run only embedding tests
  --e2e-only           Run only end-to-end tests
  --skip-vllm          Skip vLLM tests
  --skip-embedding     Skip embedding tests
  --skip-e2e           Skip end-to-end tests
  --skip-breaking      Skip breaking point tests (faster)
  --verbose            Enable verbose output
  --help               Show this help message

Examples:
  # Run complete test suite
  $0

  # Run only vLLM tests
  $0 --vllm-only

  # Run all except breaking point tests
  $0 --skip-breaking

  # Skip end-to-end tests
  $0 --skip-e2e
EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --vllm-only)
            RUN_EMBEDDING=0
            RUN_E2E=0
            shift
            ;;
        --embedding-only)
            RUN_VLLM=0
            RUN_E2E=0
            shift
            ;;
        --e2e-only)
            RUN_VLLM=0
            RUN_EMBEDDING=0
            shift
            ;;
        --skip-vllm)
            RUN_VLLM=0
            shift
            ;;
        --skip-embedding)
            RUN_EMBEDDING=0
            shift
            ;;
        --skip-e2e)
            RUN_E2E=0
            shift
            ;;
        --skip-breaking)
            SKIP_BREAKING=1
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Print banner
print_banner() {
    echo -e "\n${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║                                                            ║${NC}"
    echo -e "${MAGENTA}║        IntelliRAG Day 2 Load Testing Suite                ║${NC}"
    echo -e "${MAGENTA}║                                                            ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}\n"
}

# Print section header
print_section() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Pre-flight checks
preflight_checks() {
    print_section "Pre-flight Checks"

    local checks_passed=0
    local checks_failed=0

    # Check hey
    echo -n "Checking hey... "
    if command -v hey &> /dev/null; then
        echo -e "${GREEN}✓ Installed${NC}"
        ((checks_passed++))
    else
        echo -e "${RED}✗ Not found${NC}"
        echo -e "${YELLOW}Install with: go install github.com/rakyll/hey@latest${NC}"
        ((checks_failed++))
    fi

    # Check locust
    echo -n "Checking locust... "
    if command -v locust &> /dev/null; then
        echo -e "${GREEN}✓ Installed${NC}"
        ((checks_passed++))
    else
        echo -e "${RED}✗ Not found${NC}"
        echo -e "${YELLOW}Install with: pip install locust${NC}"
        ((checks_failed++))
    fi

    # Check kubectl (for port-forward)
    if [[ $RUN_E2E -eq 1 ]]; then
        echo -n "Checking kubectl... "
        if command -v kubectl &> /dev/null; then
            echo -e "${GREEN}✓ Installed${NC}"
            ((checks_passed++))
        else
            echo -e "${RED}✗ Not found${NC}"
            ((checks_failed++))
        fi
    fi

    # Check endpoint health
    if [[ $RUN_VLLM -eq 1 ]]; then
        echo -n "Checking vLLM endpoint... "
        if curl -s --max-time 5 "https://llm.blockchainradar.xyz/health" &> /dev/null; then
            echo -e "${GREEN}✓ Reachable${NC}"
            ((checks_passed++))
        else
            echo -e "${YELLOW}⚠ Not reachable${NC}"
        fi
    fi

    if [[ $RUN_EMBEDDING -eq 1 ]]; then
        echo -n "Checking embedding endpoint... "
        if curl -s --max-time 5 "https://embed.blockchainradar.xyz/health" &> /dev/null; then
            echo -e "${GREEN}✓ Reachable${NC}"
            ((checks_passed++))
        else
            echo -e "${YELLOW}⚠ Not reachable${NC}"
        fi
    fi

    echo ""
    echo -e "Pre-flight checks: ${GREEN}${checks_passed} passed${NC}"

    if [[ $checks_failed -gt 0 ]]; then
        echo -e "${RED}${checks_failed} failed${NC}"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Run vLLM tests
run_vllm_tests() {
    print_section "Phase 1: vLLM Load Testing"

    local skip_args=""
    if [[ $SKIP_BREAKING -eq 1 ]]; then
        skip_args="--skip-breaking"
    fi

    if ${SCRIPTS_DIR}/test-vllm.sh $skip_args $VERBOSE; then
        echo -e "\n${GREEN}✓ vLLM tests completed successfully${NC}"
        return 0
    else
        echo -e "\n${RED}✗ vLLM tests failed or had warnings${NC}"
        return 1
    fi
}

# Run embedding tests
run_embedding_tests() {
    print_section "Phase 2: Embedding Service Load Testing"

    local skip_args=""
    if [[ $SKIP_BREAKING -eq 1 ]]; then
        skip_args="--skip-breaking"
    fi

    if ${SCRIPTS_DIR}/test-embedding.sh $skip_args $VERBOSE; then
        echo -e "\n${GREEN}✓ Embedding tests completed successfully${NC}"
        return 0
    else
        echo -e "\n${RED}✗ Embedding tests failed or had warnings${NC}"
        return 1
    fi
}

# Run end-to-end tests
run_e2e_tests() {
    print_section "Phase 3: End-to-End RAG Load Testing"

    echo -e "${YELLOW}Setting up port-forward to GKE...${NC}"

    # Check if port-forward is already running
    if pgrep -f "port-forward.*intellirag-app" > /dev/null; then
        echo -e "${GREEN}✓ Port-forward already running${NC}"
    else
        echo -e "${YELLOW}Starting port-forward...${NC}"
        kubectl port-forward -n app svc/intellirag-app 8000:8000 &
        PF_PID=$!

        # Wait for port-forward to be ready
        sleep 3

        # Test connection
        if curl -s --max-time 5 http://localhost:8000/ready &> /dev/null; then
            echo -e "${GREEN}✓ Port-forward established${NC}"
        else
            echo -e "${RED}✗ Port-forward failed${NC}"
            echo -e "${YELLOW}Trying to continue anyway...${NC}"
        fi
    fi

    echo ""
    echo -e "${YELLOW}Running Locust tests...${NC}\n"

    # Run locust tests
    cd ${LOCUST_DIR}

    # Test 1: Normal load (50 users, 5 minutes)
    echo -e "${BLUE}Test 1: Normal Load (50 users, 5 min)${NC}"
    locust -f locustfile.py \
        --headless \
        --users 50 \
        --spawn-rate 5 \
        --run-time 5m \
        --host http://localhost:8000 \
        --html ${RESULTS_DIR}/e2e/locust-normal-50users.html \
        --csv ${RESULTS_DIR}/e2e/locust-normal

    echo ""

    # Test 2: High load (100 users, 5 minutes)
    echo -e "${BLUE}Test 2: High Load (100 users, 5 min)${NC}"
    locust -f locustfile.py \
        --headless \
        --users 100 \
        --spawn-rate 10 \
        --run-time 5m \
        --host http://localhost:8000 \
        --html ${RESULTS_DIR}/e2e/locust-high-100users.html \
        --csv ${RESULTS_DIR}/e2e/locust-high

    echo ""

    # Test 3: Stress test (200 users, 3 minutes)
    echo -e "${BLUE}Test 3: Stress Test (200 users, 3 min)${NC}"
    echo -e "${YELLOW}This may cause degradation - this is expected${NC}\n"

    locust -f locustfile.py \
        --user-classes StressTestUser \
        --headless \
        --users 200 \
        --spawn-rate 20 \
        --run-time 3m \
        --host http://localhost:8000 \
        --html ${RESULTS_DIR}/e2e/locust-stress-200users.html \
        --csv ${RESULTS_DIR}/e2e/locust-stress

    # Cleanup port-forward if we started it
    if [[ -n "${PF_PID:-}" ]]; then
        echo -e "\n${YELLOW}Cleaning up port-forward...${NC}"
        kill $PF_PID 2>/dev/null || true
    fi

    cd - > /dev/null

    echo -e "\n${GREEN}✓ End-to-end tests completed${NC}"
    echo -e "${CYAN}View HTML reports in: ${RESULTS_DIR}/e2e/${NC}"

    return 0
}

# Generate reports
generate_reports() {
    print_section "Generating Reports"

    if [[ $RUN_VLLM -eq 1 ]]; then
        echo -n "Generating vLLM report... "
        if ${REPORTS_DIR}/generate_report.sh vllm &> /dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠ Failed${NC}"
        fi
    fi

    if [[ $RUN_EMBEDDING -eq 1 ]]; then
        echo -n "Generating embedding report... "
        if ${REPORTS_DIR}/generate_report.sh embedding &> /dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠ Failed${NC}"
        fi
    fi

    echo -e "\n${CYAN}Reports saved in: ../../phase-3/reports/${NC}"
}

# Main execution
main() {
    print_banner

    echo -e "Test Configuration:"
    echo -e "  vLLM:      ${RUN_VLLM}"
    echo -e "  Embedding: ${RUN_EMBEDDING}"
    echo -e "  E2E:       ${RUN_E2E}"
    echo -e "  Skip Breaking: ${SKIP_BREAKING}\n"

    # Create results directories
    mkdir -p ${RESULTS_DIR}/{vllm,embedding,e2e}

    # Pre-flight checks
    preflight_checks

    # Track results
    local tests_run=0
    local tests_passed=0
    local tests_failed=0

    # Start time
    START_TIME=$(date +%s)

    # Run tests
    if [[ $RUN_VLLM -eq 1 ]]; then
        if run_vllm_tests; then
            ((tests_passed++))
        else
            ((tests_failed++))
        fi
        ((tests_run++))
    fi

    if [[ $RUN_EMBEDDING -eq 1 ]]; then
        if run_embedding_tests; then
            ((tests_passed++))
        else
            ((tests_failed++))
        fi
        ((tests_run++))
    fi

    if [[ $RUN_E2E -eq 1 ]]; then
        if run_e2e_tests; then
            ((tests_passed++))
        else
            ((tests_failed++))
        fi
        ((tests_run++))
    fi

    # Generate reports
    generate_reports

    # End time
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    DURATION_MIN=$((DURATION / 60))
    DURATION_SEC=$((DURATION % 60))

    # Final summary
    print_section "Test Suite Complete"

    echo -e "Duration:       ${CYAN}${DURATION_MIN}m ${DURATION_SEC}s${NC}"
    echo -e "Tests Run:      ${BLUE}${tests_run}${NC}"
    echo -e "Tests Passed:   ${GREEN}${tests_passed}${NC}"
    echo -e "Tests Failed:   ${RED}${tests_failed}${NC}"

    echo -e "\n${CYAN}Results Location:${NC}"
    echo -e "  Raw outputs:  ${RESULTS_DIR}"
    echo -e "  Reports:      ../../phase-3/reports/\n"

    echo -e "${CYAN}Next Steps:${NC}"
    echo -e "1. Review test reports in docs/phase-3/reports/"
    echo -e "2. Analyze breaking points and capacity limits"
    echo -e "3. Calculate HPA thresholds based on results"
    echo -e "4. Proceed to Day 3 optimization\n"

    print_banner

    if [[ $tests_failed -gt 0 ]]; then
        exit 1
    fi
}

# Run main
main
