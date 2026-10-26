#!/bin/bash

echo "============================================"
echo "  MEV BOTS - RUNNING ON LINUX"
echo "============================================"
echo ""

cd "$(dirname "$0")"

# Install Python if not present
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install web3==6.0.0 requests asyncio

echo ""
echo "============================================"
echo "  STARTING 5 NETWORK MEV BOTS"
echo "============================================"
echo ""

# Start BSC bot
echo "[1/3] Starting BSC Bot..."
nohup python3 bsc_simple.py > bsc.log 2>&1 &
echo "✅ BSC Bot started (PID: $!)"

# Start EVM bot
echo "[2/3] Starting EVM Bot (Arbitrum, Polygon, Base)..."
nohup python3 evm_simple.py > evm.log 2>&1 &
echo "✅ EVM Bot started (PID: $!)"

# Start Solana bot
echo "[3/3] Starting Solana Bot..."
nohup python3 solana_simple.py > solana.log 2>&1 &
echo "✅ Solana Bot started (PID: $!)"

echo ""
echo "============================================"
echo "  ALL BOTS RUNNING!"
echo "============================================"
echo ""
echo "Wallets:"
echo "  MetaMask: 0xb28EB4204fbf139EC0af66d81F7B448921238B10"
echo "  Phantom: E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf"
echo ""
echo "To view logs:"
echo "  tail -f bsc.log"
echo "  tail -f evm.log"
echo "  tail -f solana.log"
echo ""
echo "To check running processes:"
echo "  ps aux | grep python"
echo ""
echo "To stop all bots:"
echo "  pkill -f bsc_simple.py"
echo "  pkill -f evm_simple.py"
echo "  pkill -f solana_simple.py"
echo ""
echo "============================================"
echo "  BOTS EXTRACTING PROFITS 24/7!"
echo "============================================"
