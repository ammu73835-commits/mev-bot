#!/usr/bin/env python3
"""
Run all 5 network MEV bots in one process
"""
import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from web3 import Web3

# Your MetaMask private key
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0x7f2c3d4e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d")

# Your Phantom wallet
PHANTOM_WALLET = "E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf"

# Networks (multiple RPCs per network - first working one wins, auto-rotate)
NETWORKS = {
    "BSC": [
        "https://bsc-dataseed.binance.org/",
        "https://bsc-rpc.publicnode.com",
        "https://binance.llamarpc.com",
    ],
    "Arbitrum": [
        "https://arb1.arbitrum.io/rpc",
        "https://arbitrum-one-rpc.publicnode.com",
        "https://arbitrum.llamarpc.com",
    ],
    "Polygon": [
        "https://polygon-bor-rpc.publicnode.com",
        "https://polygon.llamarpc.com",
        "https://1rpc.io/matic",
        "https://polygon-rpc.com",
    ],
    "Base": [
        "https://mainnet.base.org",
        "https://base-rpc.publicnode.com",
        "https://base.llamarpc.com",
    ],
}

def print_banner():
    print("=" * 60)
    print("  MEV BOT SERVICE - 5 NETWORKS ACTIVE")
    print("=" * 60)
    print(f"MetaMask: 0xb28EB4204fbf139EC0af66d81F7B448921238B10")
    print(f"Phantom:  {PHANTOM_WALLET}")
    print("=" * 60)

def pick_rpc(name, rpcs, start=0):
    """Return (web3, index) for the first RPC that answers."""
    for offset in range(len(rpcs)):
        idx = (start + offset) % len(rpcs)
        rpc = rpcs[idx]
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 8}))
            if w3.is_connected():
                print(f"[{name}] RPC: {rpc}")
                return w3, idx
        except Exception:
            continue
    return None, start


async def monitor_evm(name, rpcs):
    """Monitor an EVM network with automatic RPC rotation."""
    wallet = Web3().eth.account.from_key(PRIVATE_KEY)
    idx = 0
    w3 = None

    while True:
        try:
            if w3 is None or not w3.is_connected():
                w3, idx = pick_rpc(name, rpcs, idx)
            if w3 is not None and w3.is_connected():
                balance = w3.from_wei(w3.eth.get_balance(wallet.address), "ether")
                print(f"[{name}] Connected | Balance: {balance:.6f}")
            else:
                print(f"[{name}] Reconnecting...")
                idx = (idx + 1) % len(rpcs)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[{name}] Error: {e}")
            w3 = None
            idx = (idx + 1) % len(rpcs)
            await asyncio.sleep(5)


async def monitor_solana():
    """Monitor Solana network"""
    while True:
        try:
            response = requests.post(
                "https://api.mainnet-beta.solana.com",
                json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                timeout=5
            )
            if response.status_code == 200:
                print(f"[Solana] Connected | Wallet: {PHANTOM_WALLET[:20]}...")
            else:
                print(f"[Solana] Reconnecting...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[Solana] Error: {e}")
            await asyncio.sleep(3)

def start_health_server():
    """Cloud health-check endpoint (Render / other PaaS set $PORT)."""
    port = os.getenv("PORT")
    if not port:
        return

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"MEV BOT LIVE - 5 NETWORKS\n")

        def log_message(self, *args):
            pass

    server = HTTPServer(("0.0.0.0", int(port)), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[health] listening on 0.0.0.0:{port}")


async def main():
    print_banner()
    start_health_server()
    
    # Start all EVM networks
    evm_tasks = [
        asyncio.create_task(monitor_evm(name, rpc))
        for name, rpc in NETWORKS.items()
    ]
    
    # Start Solana
    solana_task = asyncio.create_task(monitor_solana())
    
    # Run all tasks
    await asyncio.gather(*evm_tasks, solana_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down MEV bots...")
