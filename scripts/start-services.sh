#!/bin/bash
# Script to enable and start both services

echo "=== Enabling and Starting Services ==="
echo ""

# Enable kserve-port-forward service
echo "Enabling kserve-port-forward.service..."
sudo systemctl enable kserve-port-forward
if [ $? -eq 0 ]; then
    echo "✅ kserve-port-forward.service enabled"
else
    echo "❌ Failed to enable kserve-port-forward.service"
fi

# Start kserve-port-forward service
echo "Starting kserve-port-forward.service..."
sudo systemctl start kserve-port-forward
if [ $? -eq 0 ]; then
    echo "✅ kserve-port-forward.service started"
else
    echo "❌ Failed to start kserve-port-forward.service"
fi

echo ""
echo "Waiting 10 seconds for port-forwards to establish..."
sleep 10

# Enable cloudflared service
echo "Enabling cloudflared.service..."
sudo systemctl enable cloudflared
if [ $? -eq 0 ]; then
    echo "✅ cloudflared.service enabled"
else
    echo "❌ Failed to enable cloudflared.service"
fi

# Start cloudflared service
echo "Starting cloudflared.service..."
sudo systemctl start cloudflared
if [ $? -eq 0 ]; then
    echo "✅ cloudflared.service started"
else
    echo "❌ Failed to start cloudflared.service"
fi

echo ""
echo "=== Services Started ==="
echo "Run ./check-services.sh to verify status"
