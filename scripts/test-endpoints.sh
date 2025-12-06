#!/bin/bash
# Script to test endpoints (local and external)

echo "=== Testing Endpoints ==="
echo ""

echo "### Test 1: Local vLLM (localhost:8000) ###"
curl -s http://localhost:8000/v1/models 2>&1 | head -20
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ Local vLLM service is responding"
else
    echo "❌ Local vLLM service is NOT responding"
fi
echo ""

echo "### Test 2: Local Embedding (localhost:8001) ###"
curl -s http://localhost:8001/health 2>&1
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ Local embedding service is responding"
else
    echo "❌ Local embedding service is NOT responding"
fi
echo ""

echo "### Test 3: External vLLM (https://llm.blockchainradar.xyz) ###"
curl -s https://llm.blockchainradar.xyz/v1/models 2>&1 | head -20
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ External vLLM endpoint is responding"
else
    echo "❌ External vLLM endpoint is NOT responding"
fi
echo ""

echo "### Test 4: External Embedding (https://embed.blockchainradar.xyz) ###"
curl -s https://embed.blockchainradar.xyz/health 2>&1
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ External embedding endpoint is responding"
else
    echo "❌ External embedding endpoint is NOT responding"
fi
echo ""

echo "=== Testing Complete ==="
