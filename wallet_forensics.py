"""Where did the money go?  Read-only forensic trace of the configured wallets.

Usage:  python wallet_forensics.py
"""
import json
import os
import time

import requests
from web3 import Web3

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config", "bot_config.json")

RPCS = {
    "BSC": "https://bsc-dataseed.binance.org/",
    "Polygon": "https://polygon-bor-rpc.publicnode.com",
    "Arbitrum": "https://arb1.arbitrum.io/rpc",
    "Base": "https://mainnet.base.org",
    "Ethereum": "https://ethereum-rpc.publicnode.com",
}
TOKENS = {
    "BSC": {"USDT": "0x55d398326f99059fF775485246999027B3197955",
            "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"},
    "Polygon": {"USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
                "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"},
}
EXPLORERS = {
    "BSC": "https://bsc.blockscout.com",
    "Polygon": "https://polygon.blockscout.com",
    "Arbitrum": "https://arbitrum.blockscout.com",
    "Base": "https://base.blockscout.com",
    "Ethereum": "https://eth.blockscout.com",
}
BAL_ABI = "0x70a08231"  # balanceOf(address)


def load():
    with open(CONFIG, "r", encoding="utf-8") as fh:
        return json.load(fh)


def evm_report(cfg):
    key = cfg.get("evm_private_key", "")
    addr = cfg.get("evm_receiving_address", "")
    print(f"\n=== EVM wallet {addr} ===")
    if key:
        derived = Web3().eth.account.from_key(key).address
        print(f"key in config/bot_config.json -> {derived} | match: {derived.lower() == addr.lower()}")
    for name, rpc in RPCS.items():
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 12}))
            native = w3.eth.get_balance(addr)
            nonce = w3.eth.get_transaction_count(addr)
            print(f"  {name:<9} native={native / 1e18:.6f}  outgoing-txs={nonce}")
            for symbol, token in TOKENS.get(name, {}).items():
                data = BAL_ABI + "0" * 24 + addr[2:].lower()
                out = w3.eth.call({"to": Web3.to_checksum_address(token), "data": data})
                bal = int.from_bytes(out, "big")
                if bal:
                    print(f"  {name:<9} {symbol}={bal / 10**18:.6f}")
        except Exception as exc:
            print(f"  {name:<9} ERR {str(exc)[:70]}")


def evm_history(cfg, chain="BSC", pages=2):
    addr = cfg.get("evm_receiving_address", "")
    base = EXPLORERS[chain]
    print(f"\n--- {chain} transactions (newest first) ---")
    url = f"{base}/api/v2/addresses/{addr}/transactions"
    for page in range(pages):
        try:
            resp = requests.get(url, params={"filter": "to | from"}, timeout=20)
            if resp.status_code != 200:
                print(f"  explorer HTTP {resp.status_code}")
                return
            items = resp.json().get("items", [])
        except Exception as exc:
            print(f"  ERR {str(exc)[:80]}")
            return
        for item in items:
            ts = item.get("timestamp", "")
            method = item.get("method")
            value = int(item.get("value", "0")) / 1e18
            frm = (item.get("from") or {}).get("hash", "")
            to = (item.get("to") or {}).get("hash", "")
            status = item.get("status")
            direction = "OUT" if frm.lower() == addr.lower() else "IN "
            print(f"  {ts} {direction} {value:+.6f} -> {to[:12]}… from {frm[:12]}… "
                  f"status={status} method={method}")
        if not items:
            break


def solana_report(cfg):
    key = cfg.get("solana_keypair", "")
    addr = cfg.get("solana_receiving_address", "")
    print(f"\n=== Solana wallet {addr} ===")
    if key:
        try:
            from solders.keypair import Keypair

            derived = str(Keypair.from_base58_string(key).pubkey())
            print(f"key in config/bot_config.json -> {derived} | match: {derived == addr}")
        except Exception as exc:
            print(f"  (solders not installed: {str(exc)[:60]})")
    rpc = "https://api.mainnet-beta.solana.com"

    def call(method, params):
        resp = requests.post(rpc, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=20)
        return resp.json()

    bal = call("getBalance", [addr]).get("result", {}).get("value")
    print(f"  native={0 if bal is None else bal / 1e9:.6f} SOL")
    sigs = call("getSignaturesForAddress", [addr, {"limit": 15}]).get("result", [])
    print(f"  last {len(sigs)} signatures:")
    for sig in sigs:
        when = time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(sig["blockTime"])) if sig.get("blockTime") else "?"
        err = "FAILED" if sig.get("err") else "ok"
        print(f"    {when} {sig['signature'][:24]}… {err}")
    if sigs:
        newest = sigs[0]["signature"]
        tx = call("getTransaction", [newest, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
        result = (tx.get("result") or {})
        meta = result.get("meta") or {}
        keys = [k.get("pubkey") for k in (result.get("transaction") or {}).get("message", {}).get("accountKeys", [])][:6]
        print(f"  newest tx accounts: {keys}")
        print(f"  fee={meta.get('fee')} lamports  err={meta.get('err')}")


if __name__ == "__main__":
    cfg = load()
    evm_report(cfg)
    evm_history(cfg, "BSC")
    solana_report(cfg)
