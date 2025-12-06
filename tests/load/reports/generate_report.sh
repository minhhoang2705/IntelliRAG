#!/bin/bash
# Simple report aggregator - collects test outputs into organized reports

set -euo pipefail

SERVICE="$1"
RESULTS_DIR="../results/${SERVICE}"
OUTPUT_DIR="../../phase-3/reports"

mkdir -p "$OUTPUT_DIR"

REPORT_FILE="${OUTPUT_DIR}/${SERVICE}-load-test-report.md"

echo "Generating report for ${SERVICE}..."

cat > "$REPORT_FILE" <<EOF
# ${SERVICE^} Load Test Report

**Date**: $(date +%Y-%m-%d)
**Generated**: $(date --iso-8601=seconds)

---

## Test Results

EOF

# Append all test result files
for file in ${RESULTS_DIR}/*.txt; do
    if [[ -f "$file" ]]; then
        echo "### $(basename ${file} .txt)" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        cat "$file" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
done

echo "Report saved: $REPORT_FILE"
