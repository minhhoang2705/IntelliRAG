#!/bin/bash
# Embedding Service Load Testing Suite
# Tests embedding endpoint with multiple batch sizes and concurrency levels

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Source files
CONFIG_DIR="${SCRIPT_DIR}/../config"
RESULTS_DIR="${SCRIPT_DIR}/../results/embedding"
RUNNER="${SCRIPT_DIR}/run-hey-test.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
EMBEDDING_ENDPOINT="https://embed.blockchainradar.xyz/vectorize"
MODEL="embeddinggemma-300m"

# Test profiles
declare -A STANDARD=(
    [concurrent]=100
    [requests]=2000
    [batch_size]=5
)

declare -A LARGE_BATCH=(
    [concurrent]=50
    [requests]=1000
    [batch_size]=10
)

declare -A BREAKING=(
    [start]=100
    [step]=50
    [max]=300
    [requests_per_step]=500
    [batch_size]=3
)

# Batch sizes for optimization test
BATCH_SIZES=(1 3 5 10 20)

# Usage
usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --profile PROFILE         Run specific profile: standard, large-batch, breaking, optimize, all (default: all)
  --skip-standard           Skip standard load test
  --skip-large-batch        Skip large batch test
  --skip-breaking           Skip breaking point test
  --skip-optimize           Skip batch optimization test
  --verbose                 Enable verbose output
  --help                    Show this help message

Examples:
  # Run all tests
  $0

  # Run only batch optimization
  $0 --profile optimize

  # Run all except breaking point
  $0 --skip-breaking

  # Verbose output
  $0 --verbose
EOF
    exit 1
}

# Parse arguments
PROFILE="all"
SKIP_STANDARD=0
SKIP_LARGE_BATCH=0
SKIP_BREAKING=0
SKIP_OPTIMIZE=0
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --skip-standard)
            SKIP_STANDARD=1
            shift
            ;;
        --skip-large-batch)
            SKIP_LARGE_BATCH=1
            shift
            ;;
        --skip-breaking)
            SKIP_BREAKING=1
            shift
            ;;
        --skip-optimize)
            SKIP_OPTIMIZE=1
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

# Create results directory
mkdir -p "$RESULTS_DIR"

# Print header
print_header() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Build request payload for embedding
build_payload() {
    local batch_size="$1"

    # Generate array of text samples
    local texts="["
    for i in $(seq 1 "$batch_size"); do
        if [[ $i -gt 1 ]]; then
            texts+=","
        fi
        texts+="\"sample text ${i} for embedding test\""
    done
    texts+="]"

    cat <<EOF
{
  "texts": ${texts},
  "normalize": true
}
EOF
}

# Run a single test
run_test() {
    local test_name="$1"
    local concurrent="$2"
    local requests="$3"
    local batch_size="$4"

    echo -e "${YELLOW}Running ${test_name}...${NC}"
    echo -e "Concurrent: ${concurrent}, Requests: ${requests}, Batch size: ${batch_size}"

    local payload=$(build_payload "$batch_size")

    $RUNNER \
        --endpoint "$EMBEDDING_ENDPOINT" \
        --data "$payload" \
        --concurrent "$concurrent" \
        --requests "$requests" \
        --timeout 10 \
        --output-dir "$RESULTS_DIR" \
        --test-name "${test_name}" \
        $VERBOSE

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}✓ ${test_name} completed successfully${NC}\n"
    else
        echo -e "${RED}✗ ${test_name} failed or had degraded performance${NC}\n"
    fi

    return $exit_code
}

# Check endpoint health
check_health() {
    echo -e "${YELLOW}Checking embedding endpoint health...${NC}"

    if curl -s --max-time 5 "${EMBEDDING_ENDPOINT%/*}/health" &> /dev/null; then
        echo -e "${GREEN}✓ Embedding endpoint is healthy${NC}\n"
        return 0
    else
        echo -e "${RED}✗ Embedding endpoint is not reachable${NC}"
        echo -e "URL: ${EMBEDDING_ENDPOINT}"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        return 1
    fi
}

# Main test suite
main() {
    print_header "Embedding Service Load Test Suite"

    echo -e "Endpoint:     ${GREEN}${EMBEDDING_ENDPOINT}${NC}"
    echo -e "Model:        ${GREEN}${MODEL}${NC}"
    echo -e "Results Dir:  ${GREEN}${RESULTS_DIR}${NC}"
    echo -e "Test Profile: ${GREEN}${PROFILE}${NC}\n"

    # Health check
    check_health

    local test_count=0
    local passed_count=0
    local failed_count=0

    # Test 1: Standard Load
    if [[ "$PROFILE" == "all" || "$PROFILE" == "standard" ]] && [[ $SKIP_STANDARD -eq 0 ]]; then
        print_header "Test 1: Standard Load"

        if run_test \
            "embedding-standard" \
            "${STANDARD[concurrent]}" \
            "${STANDARD[requests]}" \
            "${STANDARD[batch_size]}"; then
            ((passed_count++))
        else
            ((failed_count++))
        fi
        ((test_count++))
    fi

    # Test 2: Large Batch
    if [[ "$PROFILE" == "all" || "$PROFILE" == "large-batch" ]] && [[ $SKIP_LARGE_BATCH -eq 0 ]]; then
        print_header "Test 2: Large Batch Test"

        if run_test \
            "embedding-large-batch" \
            "${LARGE_BATCH[concurrent]}" \
            "${LARGE_BATCH[requests]}" \
            "${LARGE_BATCH[batch_size]}"; then
            ((passed_count++))
        else
            ((failed_count++))
        fi
        ((test_count++))
    fi

    # Test 3: Batch Size Optimization
    if [[ "$PROFILE" == "all" || "$PROFILE" == "optimize" ]] && [[ $SKIP_OPTIMIZE -eq 0 ]]; then
        print_header "Test 3: Batch Size Optimization"

        echo -e "${YELLOW}Testing different batch sizes to find optimal configuration...${NC}\n"

        declare -A batch_results

        for batch_size in "${BATCH_SIZES[@]}"; do
            echo -e "${BLUE}Testing batch size: ${batch_size}${NC}"

            if run_test \
                "embedding-batch-${batch_size}" \
                30 \
                500 \
                "$batch_size"; then
                batch_results[$batch_size]="PASS"
            else
                batch_results[$batch_size]="FAIL"
            fi

            # Short pause between tests
            sleep 3
        done

        # Display batch optimization summary
        echo -e "\n${CYAN}Batch Size Optimization Results:${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

        for batch_size in "${BATCH_SIZES[@]}"; do
            local status="${batch_results[$batch_size]}"
            if [[ "$status" == "PASS" ]]; then
                echo -e "Batch size ${batch_size}: ${GREEN}${status}${NC}"
            else
                echo -e "Batch size ${batch_size}: ${RED}${status}${NC}"
            fi
        done

        echo -e "\n${YELLOW}Review detailed results to identify optimal batch size based on:${NC}"
        echo -e "  - Throughput (texts/second)"
        echo -e "  - Latency (P95/P99)"
        echo -e "  - CPU utilization\n"

        ((test_count++))
        ((passed_count++))
    fi

    # Test 4: Breaking Point Analysis
    if [[ "$PROFILE" == "all" || "$PROFILE" == "breaking" ]] && [[ $SKIP_BREAKING -eq 0 ]]; then
        print_header "Test 4: Breaking Point Analysis"

        echo -e "${YELLOW}Testing incrementally from ${BREAKING[start]} to ${BREAKING[max]} concurrent users...${NC}\n"

        local breaking_point=0
        local last_success=${BREAKING[start]}

        for concurrent in $(seq ${BREAKING[start]} ${BREAKING[step]} ${BREAKING[max]}); do
            echo -e "${BLUE}Testing with ${concurrent} concurrent connections...${NC}"

            if run_test \
                "embedding-breaking-${concurrent}" \
                "$concurrent" \
                "${BREAKING[requests_per_step]}" \
                "${BREAKING[batch_size]}"; then
                last_success=$concurrent
            else
                breaking_point=$concurrent
                echo -e "${RED}Breaking point found at ${concurrent} concurrent users${NC}\n"
                break
            fi

            # Short pause between tests
            echo -e "${YELLOW}Cooling down for 5 seconds...${NC}"
            sleep 5
        done

        if [[ $breaking_point -eq 0 ]]; then
            echo -e "${GREEN}✓ No breaking point found up to ${BREAKING[max]} concurrent users${NC}"
            echo -e "${GREEN}✓ CPU capacity is sufficient!${NC}\n"
            ((passed_count++))
        else
            echo -e "${YELLOW}Breaking point identified: ${breaking_point} concurrent users${NC}"
            echo -e "${GREEN}Safe operating range: 0-${last_success} concurrent users${NC}\n"
        fi
        ((test_count++))
    fi

    # Summary
    print_header "Test Suite Summary"

    echo -e "Total Tests:    ${BLUE}${test_count}${NC}"
    echo -e "Passed:         ${GREEN}${passed_count}${NC}"
    echo -e "Failed/Warning: ${YELLOW}${failed_count}${NC}"
    echo -e "\nResults saved in: ${GREEN}${RESULTS_DIR}${NC}"

    # Next steps
    echo -e "\n${CYAN}Next Steps:${NC}"
    echo -e "1. Review detailed results in: ${RESULTS_DIR}"
    echo -e "2. Generate report with: python ../reports/generate_report.py --service embedding"
    echo -e "3. Monitor CPU utilization: kubectl top pods -n kserve"
    echo -e "4. Compare against thresholds in: ${CONFIG_DIR}/thresholds.yaml"

    print_header "Embedding Load Test Complete"

    if [[ $failed_count -gt 0 ]]; then
        exit 1
    fi
}

# Run main
main
