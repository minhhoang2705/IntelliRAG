#!/bin/bash
# Script to check status of services

echo "=== Service Status ==="
echo ""

echo "### kserve-port-forward.service ###"
sudo systemctl status kserve-port-forward --no-pager -l
echo ""

echo "### cloudflared.service ###"
sudo systemctl status cloudflared --no-pager -l
echo ""

echo "=== Port Listening Check ==="
ss -tulpn | grep -E ":(8000|8001)" || echo "No services listening on ports 8000/8001"
echo ""

echo "=== Recent Logs ==="
echo "### kserve-port-forward logs (last 20 lines) ###"
sudo journalctl -u kserve-port-forward -n 20 --no-pager
echo ""

echo "### cloudflared logs (last 20 lines) ###"
sudo journalctl -u cloudflared -n 20 --no-pager
