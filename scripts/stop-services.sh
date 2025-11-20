#!/bin/bash
# Script to stop both services (useful for troubleshooting)

echo "=== Stopping Services ==="
echo ""

echo "Stopping cloudflared.service..."
sudo systemctl stop cloudflared
if [ $? -eq 0 ]; then
    echo "✅ cloudflared.service stopped"
else
    echo "❌ Failed to stop cloudflared.service"
fi

echo "Stopping kserve-port-forward.service..."
sudo systemctl stop kserve-port-forward
if [ $? -eq 0 ]; then
    echo "✅ kserve-port-forward.service stopped"
else
    echo "❌ Failed to stop kserve-port-forward.service"
fi

echo ""
echo "=== Services Stopped ==="
