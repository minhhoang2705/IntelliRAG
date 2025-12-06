#!/bin/bash
# Script to create cloudflared systemd service

echo "Creating cloudflared.service..."

sudo tee /etc/systemd/system/cloudflared.service > /dev/null <<EOF
[Unit]
Description=CloudFlare Tunnel for IntelliRAG
After=network.target kserve-port-forward.service

[Service]
Type=simple
User=minh-ubs-k8s
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/minh-ubs-k8s/.cloudflared/config.yml --no-autoupdate run af0ef505-d101-4bbb-96e7-ae4b9c8e6c65
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

if [ $? -eq 0 ]; then
    echo "✅ cloudflared.service created successfully at /etc/systemd/system/cloudflared.service"
    sudo systemctl daemon-reload
    echo "✅ Systemd daemon reloaded"
else
    echo "❌ Failed to create cloudflared.service"
    exit 1
fi
