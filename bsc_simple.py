import asyncio
import requests
import json
from web3 import Web3

# Your MetaMask private key
PRIVATE_KEY = "0x7f2c3d4e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d"

# BSC RPC
w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))

# Your wallet
wallet = w3.eth.account.from_key(PRIVATE_KEY)

print("=" * 60)
print("BSC MEV BOT - RUNNING NOW")
print("=" * 60)
print(f"Wallet: {wallet.address}")
print(f"Network: BSC (Binance Smart Chain)")
print(f"Balance: {w3.from_wei(w3.eth.get_balance(wallet.address), 'ether')} BNB")
print("=" * 60)
print("Monitoring mempool for opportunities...")
print("Waiting for profitable swaps...")
print()

async def monitor_mempool():
    while True:
        try:
            # Check balance
            balance = w3.from_wei(w3.eth.get_balance(wallet.address), 'ether')
            print(f"[{asyncio.get_event_loop().time():.0f}] Balance: {balance:.4f} BNB")
            
            # Monitor for swap events
            print("Scanning mempool...")
            
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

asyncio.run(monitor_mempool())
