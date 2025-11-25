#!/bin/bash
# CloudFlare DNS Configuration Script
# Usage: CF_API_TOKEN="your-token" CF_ZONE_ID="your-zone-id" bash configure-cloudflare-dns.sh

set -e

# Configuration
DOMAIN="api.blockchainradar.xyz"
INGRESS_IP=$(cat /tmp/ingress-ip.txt 2>/dev/null || echo "")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "CloudFlare DNS Configuration"
echo "=========================================="
echo ""

# Validate inputs
if [ -z "$CF_API_TOKEN" ]; then
    echo -e "${RED}❌ Error: CF_API_TOKEN environment variable not set${NC}"
    echo "Usage: CF_API_TOKEN=\"your-token\" CF_ZONE_ID=\"your-zone-id\" bash $0"
    exit 1
fi

if [ -z "$CF_ZONE_ID" ]; then
    echo -e "${RED}❌ Error: CF_ZONE_ID environment variable not set${NC}"
    echo "Usage: CF_API_TOKEN=\"your-token\" CF_ZONE_ID=\"your-zone-id\" bash $0"
    exit 1
fi

if [ -z "$INGRESS_IP" ]; then
    echo -e "${RED}❌ Error: Ingress IP not found in /tmp/ingress-ip.txt${NC}"
    exit 1
fi

echo "Domain: $DOMAIN"
echo "IP Address: $INGRESS_IP"
echo "Zone ID: ${CF_ZONE_ID:0:8}..." # Show first 8 chars only
echo ""

# Check if DNS record already exists
echo "Checking for existing DNS record..."
EXISTING_RECORD=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records?name=$DOMAIN" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json")

RECORD_ID=$(echo "$EXISTING_RECORD" | jq -r '.result[0].id // empty')
CURRENT_IP=$(echo "$EXISTING_RECORD" | jq -r '.result[0].content // empty')

if [ -n "$RECORD_ID" ] && [ "$RECORD_ID" != "null" ]; then
    echo -e "${YELLOW}ℹ️  DNS record already exists${NC}"
    echo "Current IP: $CURRENT_IP"
    echo "Target IP: $INGRESS_IP"

    if [ "$CURRENT_IP" == "$INGRESS_IP" ]; then
        echo -e "${GREEN}✅ DNS record is already correctly configured!${NC}"
        exit 0
    fi

    echo ""
    echo "Updating DNS record..."
    RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records/$RECORD_ID" \
      -H "Authorization: Bearer $CF_API_TOKEN" \
      -H "Content-Type: application/json" \
      --data "{
        \"type\": \"A\",
        \"name\": \"$DOMAIN\",
        \"content\": \"$INGRESS_IP\",
        \"ttl\": 120,
        \"proxied\": false
      }")

    SUCCESS=$(echo "$RESPONSE" | jq -r '.success')

    if [ "$SUCCESS" == "true" ]; then
        echo -e "${GREEN}✅ DNS record updated successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to update DNS record${NC}"
        echo "$RESPONSE" | jq '.errors'
        exit 1
    fi
else
    echo "Creating new DNS record..."
    RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
      -H "Authorization: Bearer $CF_API_TOKEN" \
      -H "Content-Type: application/json" \
      --data "{
        \"type\": \"A\",
        \"name\": \"$DOMAIN\",
        \"content\": \"$INGRESS_IP\",
        \"ttl\": 120,
        \"proxied\": false
      }")

    SUCCESS=$(echo "$RESPONSE" | jq -r '.success')

    if [ "$SUCCESS" == "true" ]; then
        echo -e "${GREEN}✅ DNS record created successfully!${NC}"
        RECORD_ID=$(echo "$RESPONSE" | jq -r '.result.id')
        echo "Record ID: $RECORD_ID"
    else
        echo -e "${RED}❌ Failed to create DNS record${NC}"
        echo "$RESPONSE" | jq '.errors'
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "DNS Configuration Complete"
echo "=========================================="
echo ""
echo "Verifying DNS propagation..."
echo "This may take 2-10 minutes..."
echo ""

# Wait for DNS propagation
MAX_ATTEMPTS=60
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    RESOLVED_IP=$(dig +short $DOMAIN @8.8.8.8 | head -1)

    if [ "$RESOLVED_IP" == "$INGRESS_IP" ]; then
        echo -e "${GREEN}✅ DNS propagated successfully!${NC}"
        echo "Domain: $DOMAIN"
        echo "Resolves to: $RESOLVED_IP"
        echo ""

        # Verify from multiple DNS servers
        echo "Verifying from multiple DNS servers:"
        echo -n "  Google DNS (8.8.8.8): "
        dig +short $DOMAIN @8.8.8.8 | head -1
        echo -n "  CloudFlare DNS (1.1.1.1): "
        dig +short $DOMAIN @1.1.1.1 | head -1
        echo ""

        echo -e "${GREEN}✅ Ready to proceed with cert-manager installation${NC}"
        exit 0
    else
        ATTEMPT=$((ATTEMPT + 1))
        echo "Attempt $ATTEMPT/$MAX_ATTEMPTS: Resolved to '$RESOLVED_IP', waiting for '$INGRESS_IP'..."
        sleep 10
    fi
done

echo -e "${YELLOW}⚠️  DNS propagation taking longer than expected${NC}"
echo "Current resolution: $RESOLVED_IP"
echo "Expected: $INGRESS_IP"
echo ""
echo "You can manually check DNS propagation with:"
echo "  dig $DOMAIN +short"
echo "  nslookup $DOMAIN"
echo ""
echo "Once DNS is propagated, you can proceed with cert-manager installation"
