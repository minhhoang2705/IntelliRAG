#!/bin/bash
# vLLM Load Testing Suite
# Tests vLLM endpoint with multiple profiles: baseline, stress, breaking point

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Source files
CONFIG_DIR="${SCRIPT_DIR}/../config"
RESULTS_DIR="${SCRIPT_DIR}/../results/vllm"
RUNNER="${SCRIPT_DIR}/run-hey-test.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration (from YAML - hardcoded for bash simplicity)
VLLM_ENDPOINT="https://llm.blockchainradar.xyz/v1/chat/completions"
MODEL="Qwen/Qwen3-0.6B"

# Test profiles
declare -A BASELINE=(
    [concurrent]=50
    [requests]=1000
    [max_tokens]=20
    [content]="Hello"
)

declare -A STRESS=(
    [concurrent]=100
    [requests]=2000
    [max_tokens]=50
    [content]="Explain AI in 30 words"
)

declare -A BREAKING=(
    [start]=100
    [step]=50
    [max]=300
    [requests_per_step]=500
    [max_tokens]=10
    [content]="Test"
)

# Usage
usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --profile PROFILE    Run specific profile: baseline, stress, breaking, sustained, all (default: all)
  --skip-baseline      Skip baseline test
  --skip-stress        Skip stress test
  --skip-breaking      Skip breaking point test
  --skip-sustained     Skip sustained load test
  --verbose            Enable verbose output
  --help               Show this help message

Examples:
  # Run all tests
  $0

  # Run only baseline test
  $0 --profile baseline

  # Run all except breaking point
  $0 --skip-breaking

  # Verbose output
  $0 --verbose
EOF
    exit 1
}

# Parse arguments
PROFILE="all"
SKIP_BASELINE=0
SKIP_STRESS=0
SKIP_BREAKING=0
SKIP_SUSTAINED=0
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --skip-baseline)
            SKIP_BASELINE=1
            shift
            ;;
        --skip-stress)
            SKIP_STRESS=1
            shift
            ;;
        --skip-breaking)
            SKIP_BREAKING=1
            shift
            ;;
        --skip-sustained)
            SKIP_SUSTAINED=1
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

# Build request payload
build_payload() {
    local content="$1"
    local max_tokens="$2"

    cat <<EOF
{
  "model": "${MODEL}",
  "messages": [{"role": "user", "content": "${content}"}],
  "max_tokens": ${max_tokens}
}
EOF
}

# Run a single test
run_test() {
    local test_name="$1"
    local concurrent="$2"
    local requests="$3"
    local content="$4"
    local max_tokens="$5"

    echo -e "${YELLOW}Running ${test_name}...${NC}"
    echo -e "Concurrent: ${concurrent}, Requests: ${requests}, Max tokens: ${max_tokens}"

    local payload=$(build_payload "$content" "$max_tokens")

    $RUNNER \
        --endpoint "$VLLM_ENDPOINT" \
        --data "$payload" \
        --concurrent "$concurrent" \
        --requests "$requests" \
        --timeout 30 \
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
    echo -e "${YELLOW}Checking vLLM endpoint health...${NC}"

    if curl -s --max-time 5 "${VLLM_ENDPOINT%/*}/health" &> /dev/null; then
        echo -e "${GREEN}✓ vLLM endpoint is healthy${NC}\n"
        return 0
    else
        echo -e "${RED}✗ vLLM endpoint is not reachable${NC}"
        echo -e "URL: ${VLLM_ENDPOINT}"
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
    print_header "vLLM Load Test Suite"

    echo -e "Endpoint:     ${GREEN}${VLLM_ENDPOINT}${NC}"
    echo -e "Model:        ${GREEN}${MODEL}${NC}"
    echo -e "Results Dir:  ${GREEN}${RESULTS_DIR}${NC}"
    echo -e "Test Profile: ${GREEN}${PROFILE}${NC}\n"

    # Health check
    check_health

    local test_count=0
    local passed_count=0
    local failed_count=0

    # Test 1: Baseline
    if [[ "$PROFILE" == "all" || "$PROFILE" == "baseline" ]] && [[ $SKIP_BASELINE -eq 0 ]]; then
        print_header "Test 1: Baseline Performance"

        if run_test \
            "vllm-baseline" \
            "${BASELINE[concurrent]}" \
            "${BASELINE[requests]}" \
            "${BASELINE[content]}" \
            "${BASELINE[max_tokens]}"; then
            ((passed_count++))
        else
            ((failed_count++))
        fi
        ((test_count++))
    fi

    # Test 2: Stress
    if [[ "$PROFILE" == "all" || "$PROFILE" == "stress" ]] && [[ $SKIP_STRESS -eq 0 ]]; then
        print_header "Test 2: Stress Test"

        if run_test \
            "vllm-stress" \
            "${STRESS[concurrent]}" \
            "${STRESS[requests]}" \
            "${STRESS[content]}" \
            "${STRESS[max_tokens]}"; then
            ((passed_count++))
        else
            ((failed_count++))
        fi
        ((test_count++))
    fi

    # Test 3: Breaking Point Analysis
    if [[ "$PROFILE" == "all" || "$PROFILE" == "breaking" ]] && [[ $SKIP_BREAKING -eq 0 ]]; then
        print_header "Test 3: Breaking Point Analysis"

        echo -e "${YELLOW}Testing incrementally from ${BREAKING[start]} to ${BREAKING[max]} concurrent users...${NC}\n"

        local breaking_point=0
        local last_success=${BREAKING[start]}

        for concurrent in $(seq ${BREAKING[start]} ${BREAKING[step]} ${BREAKING[max]}); do
            echo -e "${BLUE}Testing with ${concurrent} concurrent connections...${NC}"

            if run_test \
                "vllm-breaking-${concurrent}" \
                "$concurrent" \
                "${BREAKING[requests_per_step]}" \
                "${BREAKING[content]}" \
                "${BREAKING[max_tokens]}"; then
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
            echo -e "${GREEN}✓ System is performing well!${NC}\n"
            ((passed_count++))
        else
            echo -e "${YELLOW}Breaking point identified: ${breaking_point} concurrent users${NC}"
            echo -e "${GREEN}Safe operating range: 0-${last_success} concurrent users${NC}\n"
        fi
        ((test_count++))
    fi

    # Test 4: Sustained Load (optional)
    if [[ "$PROFILE" == "sustained" ]] && [[ $SKIP_SUSTAINED -eq 0 ]]; then
        print_header "Test 4: Sustained Load"

        echo -e "${YELLOW}This test runs for 10 minutes at 80% of baseline capacity${NC}"
        read -p "Continue? (y/N): " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            local sustained_concurrent=80

            echo -e "${YELLOW}Running sustained load test for 10 minutes...${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop early${NC}\n"

            # Run with timeout
            if timeout 600 $RUNNER \
                --endpoint "$VLLM_ENDPOINT" \
                --data "$(build_payload 'Describe machine learning concepts' 30)" \
                --concurrent "$sustained_concurrent" \
                --requests 10000 \
                --timeout 30 \
                --output-dir "$RESULTS_DIR" \
                --test-name "vllm-sustained" \
                $VERBOSE; then
                ((passed_count++))
            else
                ((failed_count++))
            fi
            ((test_count++))
        fi
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
    echo -e "2. Generate report with: python ../reports/generate_report.py --service vllm"
    echo -e "3. Compare against thresholds in: ${CONFIG_DIR}/thresholds.yaml"

    print_header "vLLM Load Test Complete"

    if [[ $failed_count -gt 0 ]]; then
        exit 1
    fi
}

# Run main
main
