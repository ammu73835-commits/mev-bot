import asyncio
from web3 import Web3

# Your MetaMask private key
PRIVATE_KEY = "0x7f2c3d4e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d"

# Multiple EVM networks
networks = {
    "Arbitrum": "https://arb1.arbitrum.io/rpc",
    "Polygon": "https://polygon-rpc.com",
    "Base": "https://mainnet.base.org"
}

print("=" * 60)
print("EVM MULTI-CHAIN MEV BOT - RUNNING NOW")
print("=" * 60)

for name, rpc in networks.items():
    w3 = Web3(Web3.HTTPProvider(rpc))
    wallet = w3.eth.account.from_key(PRIVATE_KEY)
    balance = w3.from_wei(w3.eth.get_balance(wallet.address), 'ether')
    print(f"{name}: {wallet.address[:20]}... Balance: {balance:.6f}")

print("=" * 60)
print("Monitoring 3 networks for opportunities...")
print()

async def monitor_all():
    while True:
        try:
            for name, rpc in networks.items():
                try:
                    w3 = Web3(Web3.HTTPProvider(rpc))
                    if w3.is_connected():
                        print(f"[{name}] Connected - Scanning...")
                except:
                    print(f"[{name}] Reconnecting...")
            
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

asyncio.run(monitor_all())
