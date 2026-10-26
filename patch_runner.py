import re

path = r"C:\Users\romen\OneDrive\Desktop\all in one bot\run_all_bots.py"
src = open(path, encoding="utf-8").read()

new_block = '''def pick_rpc(name, rpcs, start=0):
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


'''

start = src.index("async def monitor_evm")
end = src.index("async def monitor_solana")
src = src[:start] + new_block + src[end:]
open(path, "w", encoding="utf-8", newline="\n").write(src)
print("patched monitor_evm")
