#!/bin/bash
# Generic hey Load Test Runner
# Usage: ./run-hey-test.sh --endpoint URL --concurrent N --requests N [OPTIONS]

set -euo pipefail

# Default values
CONCURRENT=50
TOTAL_REQUESTS=1000
METHOD="POST"
CONTENT_TYPE="application/json"
TIMEOUT=30
OUTPUT_DIR="../results"
TEST_NAME="generic-test"
VERBOSE=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print usage
usage() {
    cat <<EOF
Usage: $0 --endpoint URL --data JSON [OPTIONS]

Required Arguments:
  --endpoint URL          Target endpoint URL
  --data JSON             Request body as JSON string

Optional Arguments:
  --concurrent N          Number of concurrent connections (default: 50)
  --requests N            Total number of requests (default: 1000)
  --method METHOD         HTTP method (default: POST)
  --content-type TYPE     Content-Type header (default: application/json)
  --timeout SECONDS       Request timeout (default: 30)
  --output-dir DIR        Output directory for results (default: ../results)
  --test-name NAME        Test name for output file (default: generic-test)
  --verbose               Enable verbose output
  --help                  Show this help message

Examples:
  # Simple POST test
  $0 --endpoint https://api.example.com/test \\
     --data '{"key":"value"}' \\
     --concurrent 100 --requests 2000

  # Custom test name and output
  $0 --endpoint https://api.example.com/test \\
     --data '{"key":"value"}' \\
     --test-name my-baseline-test \\
     --output-dir /tmp/results
EOF
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --endpoint)
            ENDPOINT="$2"
            shift 2
            ;;
        --data)
            REQUEST_DATA="$2"
            shift 2
            ;;
        --concurrent)
            CONCURRENT="$2"
            shift 2
            ;;
        --requests)
            TOTAL_REQUESTS="$2"
            shift 2
            ;;
        --method)
            METHOD="$2"
            shift 2
            ;;
        --content-type)
            CONTENT_TYPE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --test-name)
            TEST_NAME="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=1
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

# Validate required arguments
if [[ -z "${ENDPOINT:-}" ]]; then
    echo -e "${RED}Error: --endpoint is required${NC}"
    usage
fi

if [[ -z "${REQUEST_DATA:-}" ]] && [[ "$METHOD" != "GET" ]]; then
    echo -e "${RED}Error: --data is required for $METHOD requests${NC}"
    usage
fi

# Check if hey is installed
if ! command -v hey &> /dev/null; then
    echo -e "${RED}Error: hey is not installed${NC}"
    echo "Install with: go install github.com/rakyll/hey@latest"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/${TEST_NAME}_${TIMESTAMP}.txt"

# Print test configuration
echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}  Load Test Configuration${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "Test Name:         ${GREEN}${TEST_NAME}${NC}"
echo -e "Endpoint:          ${GREEN}${ENDPOINT}${NC}"
echo -e "Method:            ${GREEN}${METHOD}${NC}"
echo -e "Concurrent:        ${GREEN}${CONCURRENT}${NC}"
echo -e "Total Requests:    ${GREEN}${TOTAL_REQUESTS}${NC}"
echo -e "Timeout:           ${GREEN}${TIMEOUT}s${NC}"
echo -e "Output:            ${GREEN}${OUTPUT_FILE}${NC}"
echo -e "${BLUE}===========================================${NC}"

# Run pre-flight health check
echo -e "\n${YELLOW}Running pre-flight health check...${NC}"
if curl -s --max-time 5 "${ENDPOINT%/*}/health" &> /dev/null || \
   curl -s --max-time 5 "${ENDPOINT}" &> /dev/null; then
    echo -e "${GREEN}✓ Endpoint is reachable${NC}"
else
    echo -e "${RED}✗ Warning: Could not reach endpoint${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build hey command
HEY_CMD="hey -n ${TOTAL_REQUESTS} -c ${CONCURRENT} -m ${METHOD} -t ${TIMEOUT}"
HEY_CMD="${HEY_CMD} -H \"Content-Type: ${CONTENT_TYPE}\""

if [[ -n "${REQUEST_DATA:-}" ]]; then
    HEY_CMD="${HEY_CMD} -d '${REQUEST_DATA}'"
fi

HEY_CMD="${HEY_CMD} ${ENDPOINT}"

# Print command if verbose
if [[ $VERBOSE -eq 1 ]]; then
    echo -e "\n${YELLOW}Command:${NC}"
    echo "$HEY_CMD"
fi

# Run the test
echo -e "\n${YELLOW}Starting load test...${NC}"
echo -e "Started at: ${GREEN}$(date)${NC}"

START_TIME=$(date +%s)

# Execute hey and save output
eval "$HEY_CMD" | tee "$OUTPUT_FILE"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "\n${GREEN}✓ Test completed${NC}"
echo -e "Duration: ${GREEN}${DURATION}s${NC}"
echo -e "Results saved to: ${GREEN}${OUTPUT_FILE}${NC}"

# Parse and display key metrics
echo -e "\n${BLUE}===========================================${NC}"
echo -e "${BLUE}  Key Metrics Summary${NC}"
echo -e "${BLUE}===========================================${NC}"

if [[ -f "$OUTPUT_FILE" ]]; then
    # Extract success rate
    SUCCESS_COUNT=$(grep -oP '\[200\]\s+\K\d+' "$OUTPUT_FILE" || echo "0")
    ERROR_COUNT=$(grep -oP 'Error distribution:' "$OUTPUT_FILE" -A 10 | grep -oP '\[\d+\]\s+\K\d+' | awk '{s+=$1} END {print s}' || echo "0")
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.2f\", ($SUCCESS_COUNT / $TOTAL_REQUESTS) * 100}")

    # Extract latency metrics
    P50=$(grep -oP '50% in \K[\d.]+' "$OUTPUT_FILE" || echo "N/A")
    P95=$(grep -oP '95% in \K[\d.]+' "$OUTPUT_FILE" || echo "N/A")
    P99=$(grep -oP '99% in \K[\d.]+' "$OUTPUT_FILE" || echo "N/A")
    RPS=$(grep -oP 'Requests/sec:\s+\K[\d.]+' "$OUTPUT_FILE" || echo "N/A")

    echo -e "Success Rate:      ${GREEN}${SUCCESS_RATE}%${NC} (${SUCCESS_COUNT}/${TOTAL_REQUESTS})"
    echo -e "Throughput:        ${GREEN}${RPS} req/s${NC}"
    echo -e "Latency P50:       ${GREEN}${P50}s${NC}"
    echo -e "Latency P95:       ${GREEN}${P95}s${NC}"
    echo -e "Latency P99:       ${GREEN}${P99}s${NC}"

    if [[ $ERROR_COUNT -gt 0 ]]; then
        echo -e "Errors:            ${RED}${ERROR_COUNT}${NC}"
    fi
fi

echo -e "${BLUE}===========================================${NC}"

# Return success if no errors
if [[ "${SUCCESS_RATE%%.*}" -ge 99 ]]; then
    exit 0
else
    echo -e "${RED}Warning: Success rate below 99%${NC}"
    exit 1
fi
