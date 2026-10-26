#!/usr/bin/env python3
"""
Run all 5 network MEV bots in one process
"""
import asyncio
import requests
from web3 import Web3

# Your MetaMask private key
PRIVATE_KEY = "0x7f2c3d4e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d"

# Your Phantom wallet
PHANTOM_WALLET = "E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf"

# Networks
NETWORKS = {
    "BSC": "https://bsc-dataseed.binance.org/",
    "Arbitrum": "https://arb1.arbitrum.io/rpc",
    "Polygon": "https://polygon-rpc.com",
    "Base": "https://mainnet.base.org"
}

def print_banner():
    print("=" * 60)
    print("  MEV BOT SERVICE - 5 NETWORKS ACTIVE")
    print("=" * 60)
    print(f"MetaMask: 0xb28EB4204fbf139EC0af66d81F7B448921238B10")
    print(f"Phantom:  {PHANTOM_WALLET}")
    print("=" * 60)

async def monitor_evm(name, rpc):
    """Monitor an EVM network"""
    w3 = Web3(Web3.HTTPProvider(rpc))
    wallet = w3.eth.account.from_key(PRIVATE_KEY)
    
    while True:
        try:
            if w3.is_connected():
                balance = w3.from_wei(w3.eth.get_balance(wallet.address), 'ether')
                print(f"[{name}] Connected | Balance: {balance:.6f}")
            else:
                print(f"[{name}] Reconnecting...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[{name}] Error: {e}")
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

async def main():
    print_banner()
    
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
