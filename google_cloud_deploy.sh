#!/bin/bash

echo "=============================================="
echo "  GOOGLE CLOUD MEV BOT DEPLOYMENT"
echo "=============================================="
echo ""

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install web3==6.0.0 eth-account==0.13.0 aiohttp==3.9.0 solana==0.30.1 pyserum==0.10.1 websockets==12.0 requests==2.31.0

# Create systemd service
sudo tee /etc/systemd/system/mev-bot.service > /dev/null <<EOF
[Unit]
Description=MEV Bot Service - 5 Networks
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$(pwd)/venv/bin/python3 $(pwd)/run_all_bots.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mev-bot

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable mev-bot
sudo systemctl start mev-bot

echo ""
echo "=============================================="
echo "  DEPLOYMENT COMPLETE!"
echo "=============================================="
echo ""
echo "Service Status:"
sudo systemctl status mev-bot --no-pager
echo ""
echo "View logs with: sudo journalctl -u mev-bot -f"
echo ""
echo "Bots are running 24/7 on Google Cloud!"
