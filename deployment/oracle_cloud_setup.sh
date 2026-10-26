#!/bin/bash
# Oracle Cloud Free Tier Deployment Script
# Deploys MEV bots on free Ubuntu VM (24 GB RAM, 4 OCPUs)

echo "=== Oracle Cloud MEV Bot Deployment ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js for additional tools
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Create bot directory
mkdir -p /opt/mev-bot
cd /opt/mev-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install web3==8.0.0 eth-account aiohttp websockets
pip install solana==0.30.1 pyserum==0.10.1

# Create systemd service for EVM bot
cat > /etc/systemd/system/evm-mev-bot.service << EOF
[Unit]
Description=EVM MEV Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/mev-bot
Environment="PATH=/opt/mev-bot/venv/bin"
ExecStart=/opt/mev-bot/venv/bin/python evm_bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for Solana bot
cat > /etc/systemd/system/solana-mev-bot.service << EOF
[Unit]
Description=Solana MEV Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/mev-bot
Environment="PATH=/opt/mev-bot/venv/bin"
ExecStart=/opt/mev-bot/venv/bin/python solana_bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable evm-mev-bot.service
sudo systemctl enable solana-mev-bot.service
sudo systemctl start evm-mev-bot.service
sudo systemctl start solana-mev-bot.service

echo "=== Deployment Complete ==="
echo "Check status with: systemctl status evm-mev-bot"
echo "Check logs with: journalctl -u evm-mev-bot -f"
