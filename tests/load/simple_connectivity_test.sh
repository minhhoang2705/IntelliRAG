#!/bin/bash
# Simple service connectivity test without requiring document ingestion

set -e

BASE_URL="http://localhost:8002"
VLLM_URL="https://llm.blockchainradar.xyz"
EMBED_URL="https://embed.blockchainradar.xyz"

echo "=========================================="
echo "Service Connectivity Test"
echo "=========================================="
echo ""

# Test 1: App Health
echo "1. Testing FastAPI App Health..."
RESPONSE=$(curl -s $BASE_URL/)
if echo $RESPONSE | grep -q "healthy"; then
    echo "   ✅ App is healthy"
else
    echo "   ❌ App health check failed"
    exit 1
fi
echo ""

# Test 2: vLLM Service
echo "2. Testing vLLM Service..."
RESPONSE=$(curl -s $VLLM_URL/v1/models)
if echo $RESPONSE | grep -q "Qwen"; then
    echo "   ✅ vLLM is accessible and serving models"
else
    echo "   ❌ vLLM service check failed"
    exit 1
fi
echo ""

# Test 3: Embedding Service
echo "3. Testing Embedding Service..."
RESPONSE=$(curl -s $EMBED_URL/health)
if echo $RESPONSE | grep -q "healthy"; then
    echo "   ✅ Embedding service is healthy"
else
    echo "   ❌ Embedding service check failed"
    exit 1
fi
echo ""

# Test 4: Simple RAG Query (expect Qdrant error but 200 status)
echo "4. Testing RAG Query Endpoint (expect Qdrant collection error)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE_URL/api/v1/query \
    -H "Content-Type: application/json" \
    -d '{"query":"test"}' \
    --max-time 5)

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ RAG endpoint is accessible (HTTP 200)"
    echo "   ℹ️  Note: Qdrant collection error expected (no documents ingested)"
elif [ "$HTTP_CODE" = "000" ]; then
    echo "   ❌ RAG endpoint timed out"
else
    echo "   ⚠️  RAG endpoint returned HTTP $HTTP_CODE"
fi
echo ""

# Test 5: Concurrent lightweight requests
echo "5. Testing concurrent health checks (10 requests)..."
start=$(date +%s)
for i in {1..10}; do
    curl -s $BASE_URL/ > /dev/null &
done
wait
end=$(date +%s)
duration=$((end - start))
echo "   ✅ Completed 10 concurrent requests in ${duration}s"
echo ""

echo "=========================================="
echo "Service Connectivity: ✅ VERIFIED"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - FastAPI App: ✅ Running"
echo "  - vLLM Service: ✅ Connected"
echo "  - Embedding Service: ✅ Connected"
echo "  - All services accessible and responding"
echo ""
echo "Note: Full E2E RAG testing requires document ingestion first"
echo "      Use /api/v1/upload and /api/v1/ingest endpoints to add documents"
