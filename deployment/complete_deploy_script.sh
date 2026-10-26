#!/bin/bash
# Complete Oracle Cloud Deployment Script
# Automated setup for MEV bots

echo "========================================"
echo "MEV BOT - ORACLE CLOUD DEPLOYMENT"
echo "========================================"

# Update system
echo "[1/7] Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
echo "[2/7] Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Create bot directory
echo "[3/7] Setting up bot directory..."
mkdir -p /opt/mev-bot
cd /opt/mev-bot

# Copy files (assuming uploaded to /tmp/mev-bot-deploy.zip)
if [ -f /tmp/mev-bot-deploy.zip ]; then
    echo "[4/7] Extracting deployment package..."
    unzip /tmp/mev-bot-deploy.zip -d /opt/mev-bot/
elif [ -d /tmp/mev-bot ]; then
    echo "[4/7] Copying bot files..."
    cp -r /tmp/mev-bot/* /opt/mev-bot/
else
    echo "[ERROR] Deployment package not found!"
    echo "Please upload mev-bot-deploy.zip to /tmp/"
    exit 1
fi

# Create virtual environment
echo "[5/7] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "[6/7] Installing Python packages..."
pip install --upgrade pip
pip install web3==8.0.0 eth-account==0.14.0 aiohttp==3.14.3 solana==0.30.1 pyserum asyncstdlib websockets

# Create systemd service
echo "[7/7] Creating systemd service..."
cat > /etc/systemd/system/mev-bot.service << 'EOF'
[Unit]
Description=MEV Bot - 24/7 Money Extraction
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/mev-bot
Environment="PATH=/opt/mev-bot/venv/bin"
ExecStart=/opt/mev-bot/venv/bin/python AUTOMATED_LAUNCHER.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable mev-bot
sudo systemctl start mev-bot

echo ""
echo "========================================"
echo "DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "Bot Status:"
sudo systemctl status mev-bot --no-pager
echo ""
echo "View Live Profits:"
echo "  sudo journalctl -u mev-bot -f"
echo ""
echo "View Only Profits:"
echo "  sudo journalctl -u mev-bot -f | grep profit"
echo ""
echo "Restart Bot:"
echo "  sudo systemctl restart mev-bot"
echo ""
echo "========================================"
echo "BOTS ARE NOW RUNNING 24/7!"
echo "You can safely disconnect!"
echo "========================================"
