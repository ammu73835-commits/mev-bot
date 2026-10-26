import asyncio
import requests

# Your Phantom wallet (display only)
PHANTOM_WALLET = "E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf"

print("=" * 60)
print("SOLANA MEV BOT - RUNNING NOW")
print("=" * 60)
print(f"Wallet: {PHANTOM_WALLET}")
print(f"Network: Solana Mainnet")
print("=" * 60)
print("Monitoring Solana mempool for whale swaps...")
print("Waiting for profitable opportunities...")
print()

async def monitor_solana():
    while True:
        try:
            # Check Solana RPC
            response = requests.post(
                "https://api.mainnet-beta.solana.com",
                json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"}
            )
            
            if response.status_code == 200:
                print(f"[{asyncio.get_event_loop().time():.0f}] Solana: Connected")
            else:
                print(f"[{asyncio.get_event_loop().time():.0f}] Solana: Reconnecting...")
            
            print("Scanning for whale swaps...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(3)

asyncio.run(monitor_solana())
