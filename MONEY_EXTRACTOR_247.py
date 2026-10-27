#!/usr/bin/env python3
"""
MONEY_EXTRACTOR_247 - the always-on 24/7 supervisor for the MEV engine.

WHAT THIS ADDS (without touching any existing strategy code):
  1. SECURITY-FIRST KEY LOADING - keys come ONLY from bot_keys.local.json
     (git-ignored, verified absent from git history) or environment variables.
     Keys are never hardcoded, never printed, never written to logs.
  2. WALLET FUNDING WATCH - polls the fresh wallets every cycle. The moment
     they are funded it: (a) writes a loud alert file, (b) auto-deploys the
     ArbExecutor contract from the pre-built artifact (no solc needed), and
     (c) switches the engine from DRY-RUN to LIVE.
  3. PROFIT-LOCKED FIRING - inherited from mev_engine (unchanged): a route is
     signed only when BOTH gates pass:
        gate 1: net profit (after gas + flash fee) >= MIN_NET_PROFIT_BPS margin
        gate 2: free on-chain simulation (eth_call) proves the profit
     If either gate fails -> no gas is spent. Unprofitable on-chain routes
     revert atomically inside the flash swap, so worst case is bounded.
  4. NETWORK ROTATION - BSC (primary fire chain) -> Polygon -> Arbitrum ->
     Base -> Ethereum -> Solana, forever, with time slices per chain.
  5. SELF-HEALING - any crash in a segment is logged and the rotation moves on;
     the outer watchdog keeps the process alive indefinitely.
  6. STATUS DASHBOARD - logs/status.json heartbeat + logs/profit_ledger.json
     for every FIRED transaction, so the bot can be monitored at a glance.

Usage:
    python MONEY_EXTRACTOR_247.py                 (runs forever)
    python MONEY_EXTRACTOR_247.py --once          (one full rotation, then exit)
    python MONEY_EXTRACTOR_247.py --minutes 5     (stop after 5 minutes)
"""

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGS = HERE / "logs"
LOGS.mkdir(exist_ok=True)

KEYS_FILE = HERE / "bot_keys.local.json"          # git-ignored, never committed
CONTRACT_ARTIFACT = HERE / "mev_engine" / "build" / "ArbExecutor.json"
STATUS_FILE = LOGS / "status.json"
LEDGER_FILE = LOGS / "profit_ledger.json"
FUNDING_ALERT = LOGS / "FUNDING_DETECTED.txt"
ARB_CONTRACT_STATE = LOGS / "arb_contract.json"    # deployed address cache


# ------------------------------------------------------------------ tuning
SLICE_SECONDS = int(os.getenv("SLICE_SECONDS", "90"))   # per-network time slice
BSC_EXTRA_SLICES = int(os.getenv("BSC_EXTRA_SLICES", "1"))  # BSC gets extra time
# Deploy ArbExecutor automatically once the BSC wallet can afford it.
AUTO_DEPLOY = os.getenv("AUTO_DEPLOY", "1").strip().lower() in ("1", "true", "yes", "on")
# Minimum BNB before we are allowed to spend the (single, tiny) deploy tx.
MIN_DEPLOY_BNB = float(os.getenv("MIN_DEPLOY_BNB", "0.01"))
# Minimum SOL before Solana legs may fire.
MIN_LIVE_SOL = float(os.getenv("MIN_LIVE_SOL", "0.02"))

NETWORKS = ["BSC", "Polygon", "Arbitrum", "Base", "Ethereum"]
RPCS = {
    "BSC": ["https://bsc-dataseed.binance.org/", "https://bsc-rpc.publicnode.com"],
    "Polygon": ["https://polygon-bor-rpc.publicnode.com", "https://polygon.llamarpc.com"],
    "Arbitrum": ["https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com"],
    "Base": ["https://mainnet.base.org", "https://base-rpc.publicnode.com"],
    "Ethereum": ["https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com"],
}
SOLANA_RPC = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com")

_state = {
    "started": datetime.now(timezone.utc).isoformat(),
    "cycles": 0,
    "fired": [],
    "funding_seen": False,
    "arb_contract": None,
    "mode": "DRY-RUN",
    "last_error": None,
    "balances": {},
}


# ------------------------------------------------------------------ secrets
def load_keys():
    """Return dict with evm/solana keys, or empty dict.

    Priority: environment variables first, then bot_keys.local.json.
    Never logs the secrets themselves.
    """
    keys = {}
    if os.getenv("PRIVATE_KEY"):
        keys["evm_private_key"] = os.environ["PRIVATE_KEY"]
    if os.getenv("SOLANA_PRIVATE_KEY"):
        keys["solana_private_key_base58"] = os.environ["SOLANA_PRIVATE_KEY"]

    if KEYS_FILE.exists():
        try:
            data = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
            keys.setdefault("evm_private_key", data.get("evm_private_key"))
            keys.setdefault("evm_address", data.get("evm_address"))
            keys.setdefault("solana_private_key_base58", data.get("solana_private_key_base58"))
            keys.setdefault("solana_address", data.get("solana_address"))
        except Exception as exc:
            print(f"[keys] WARNING: could not parse {KEYS_FILE.name}: {exc}")

    if not keys.get("evm_private_key") and not keys.get("solana_private_key_base58"):
        return {}
    return keys


def evm_address_of(keys):
    addr = keys.get("evm_address")
    if addr:
        return addr
    try:
        from web3 import Web3
        acct = Web3().eth.account.from_key(keys["evm_private_key"])
        return acct.address
    except Exception:
        return None

# ------------------------------------------------------------------ balances
def evm_balances(address):
    """Native balances on all chains. Returns {chain: float}."""
    from web3 import Web3
    out = {}
    for chain, rpcs in RPCS.items():
        out[chain] = 0.0
        for rpc in rpcs:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 8}))
                if w3.is_connected():
                    out[chain] = w3.from_wei(w3.eth.get_balance(address), "ether")
                    break
            except Exception:
                continue
    return out


def sol_balance(address):
    try:
        import requests
        r = requests.post(
            SOLANA_RPC,
            json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]},
            timeout=8,
        )
        return int(r.json()["result"]["value"]) / 1e9
    except Exception:
        return 0.0


# ------------------------------------------------------------------ status
def write_status(extra=None):
    payload = {
        "heartbeat": datetime.now(timezone.utc).isoformat(),
        "mode": _state["mode"],
        "uptime_started": _state["started"],
        "cycles": _state["cycles"],
        "fired_count": len(_state["fired"]),
        "fired": _state["fired"][-20:],
        "wallet_funded": _state["funding_seen"],
        "arb_contract": _state["arb_contract"],
        "balances": _state["balances"],
        "last_error": _state["last_error"],
    }
    if extra:
        payload.update(extra)
    STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def record_fired(line):
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "detail": line.strip()[:300],
    }
    _state["fired"].append(entry)
    try:
        ledger = []
        if LEDGER_FILE.exists():
            ledger = json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
        ledger.append(entry)
        LEDGER_FILE.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    except Exception:
        pass


# ------------------------------------------------------------------ deploy
def deploy_arb_executor(private_key):
    """Deploy ArbExecutor from the pre-built artifact (no solc needed).

    Costs one small tx (~0.001-0.002 BNB on BSC) - the only gas this
    orchestrator itself ever spends, and only after the wallet is funded.
    """
    if not CONTRACT_ARTIFACT.exists():
        print("[deploy] artifact missing; run: python -m mev_engine.contract_tools compile")
        return None
    artifact = json.loads(CONTRACT_ARTIFACT.read_text(encoding="utf-8"))
    from web3 import Web3
    for rpc in RPCS["BSC"]:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
            if not w3.is_connected():
                continue
            account = w3.eth.account.from_key(private_key)
            factory = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
            tx = factory.constructor().build_transaction({
                "from": account.address,
                "chainId": 56,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gas": 1_600_000,
                "gasPrice": int(w3.eth.gas_price * 1.15),
            })
            signed = account.sign_transaction(tx)
            raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction")
            tx_hash = w3.eth.send_raw_transaction(raw)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
            if receipt.status != 1:
                print(f"[deploy] deploy tx reverted: {tx_hash.hex()}")
                return None
            address = receipt["contractAddress"]
            ARB_CONTRACT_STATE.write_text(
                json.dumps({"address": address, "tx": tx_hash.hex(), "chain": "BSC",
                            "deployed": datetime.now(timezone.utc).isoformat()}, indent=2),
                encoding="utf-8")
            print(f"[deploy] ArbExecutor LIVE at {address} (tx {tx_hash.hex()})")
            return address
        except Exception as exc:
            print(f"[deploy] {rpc} failed: {exc}")
    return None


def cached_contract():
    if ARB_CONTRACT_STATE.exists():
        try:
            return json.loads(ARB_CONTRACT_STATE.read_text(encoding="utf-8"))["address"]
        except Exception:
            return None
    return os.getenv("ARB_CONTRACT") or None


# ------------------------------------------------------------------ funding watch
def check_funding(keys):
    """Poll wallet balances; on first funding, alert + deploy + go live."""
    addr = evm_address_of(keys)
    balances = {}
    sol = 0.0
    if addr:
        balances = evm_balances(addr)
    if keys.get("solana_address"):
        sol = sol_balance(keys["solana_address"])
    balances["Solana"] = sol
    _state["balances"] = balances

    bnb = balances.get("BSC", 0.0)
    funded = bnb > 0 or sol > 0

    if funded and not _state["funding_seen"]:
        _state["funding_seen"] = True
        alert = (
            "=" * 60 + "\n"
            f"  FUNDING DETECTED @ {datetime.now(timezone.utc).isoformat()}\n"
            f"  EVM wallet : {addr}\n"
            f"  BSC        : {bnb:.6f} BNB\n"
            f"  Solana     : {sol:.6f} SOL\n" + "=" * 60 + "\n"
        )
        FUNDING_ALERT.write_text(alert, encoding="utf-8")
        print(alert)

    # --- auto-deploy once, when BSC can afford it -------------------------
    contract = cached_contract()
    if (not contract and AUTO_DEPLOY and bnb >= MIN_DEPLOY_BNB
            and keys.get("evm_private_key")):
        print("[funding] wallet funded - deploying ArbExecutor (one small tx)...")
        contract = deploy_arb_executor(keys["evm_private_key"])
    _state["arb_contract"] = contract

    # --- decide LIVE vs DRY-RUN -------------------------------------------
    evm_live = bool(contract and keys.get("evm_private_key") and bnb >= MIN_DEPLOY_BNB)
    sol_live = bool(keys.get("solana_private_key_base58") and sol >= MIN_LIVE_SOL)
    _state["mode"] = "LIVE" if (evm_live or sol_live) else "DRY-RUN"
    return evm_live, sol_live


# ------------------------------------------------------------------ engine run
def run_segment(network, seconds, live, keys, sol_live=False):
    """Run one mev_engine segment as a subprocess and stream-parse output."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["DRY_RUN"] = "0" if live else "1"
    env["LIVE"] = "1" if live else "0"
    if live:
        env["ARB_CONTRACT"] = _state["arb_contract"] or ""
        env["ARB_NETWORK"] = "BSC"
        env["PRIVATE_KEY"] = keys["evm_private_key"]
    if network == "Solana":
        # Only hand the key to the engine when the wallet can afford fees -
        # otherwise it stays a pure quote-only dry-run (0 lamports possible).
        if sol_live and keys.get("solana_private_key_base58"):
            env["SOLANA_PRIVATE_KEY"] = keys["solana_private_key_base58"]
        cmd = [sys.executable, "-m", "mev_engine.solana",
               "--seconds", str(seconds), "--interval", "8"]
    else:
        cmd = [sys.executable, "-m", "mev_engine.run_engine",
               "--network", network, "--seconds", str(seconds), "--interval", "8"]

    print(f"[segment] {network} for {seconds}s | mode={'LIVE' if live else 'DRY-RUN (0 gas)'}")
    proc = subprocess.Popen(cmd, cwd=str(HERE), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    deadline = time.time() + seconds + 45
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                print(f"  {network} | {line}")
                if ">>> FIRED" in line or "FIRED:" in line:
                    record_fired(f"{network} {line}")
            if time.time() > deadline and proc.poll() is None:
                proc.kill()
                break
    except Exception:
        pass
    finally:
        if proc.poll() is None:
            proc.kill()
        try:
            proc.wait(timeout=15)
        except Exception:
            pass
    return proc.returncode


# ------------------------------------------------------------------ main loop
_t0 = time.time()


def rotation(keys, stop_after_minutes=None, once=False):
    evm_live, sol_live = False, False
    while True:
        _state["cycles"] += 1
        try:
            evm_live, sol_live = check_funding(keys)
            write_status()
        except Exception as exc:
            _state["last_error"] = f"funding-watch: {exc}"
            print(f"[watch] funding check failed: {exc}")

        schedule = ["BSC"] * (1 + BSC_EXTRA_SLICES)
        schedule += ["Polygon", "Arbitrum", "Base", "Ethereum"]
        if keys.get("solana_private_key_base58"):
            schedule.append("Solana")

        for network in schedule:
            try:
                live = sol_live if network == "Solana" else evm_live
                run_segment(network, SLICE_SECONDS, live, keys)
            except Exception as exc:
                _state["last_error"] = f"{network}: {exc}"
                print(f"[watch] {network} crashed: {exc}")
                traceback.print_exc()
                write_status()

        write_status()
        if once:
            break
        if stop_after_minutes and (time.time() - _t0) / 60 >= stop_after_minutes:
            print("[watch] time budget reached - stopping")
            break


def main():
    parser = argparse.ArgumentParser(description="24/7 MEV money extractor supervisor")
    parser.add_argument("--once", action="store_true", help="one rotation then exit")
    parser.add_argument("--minutes", type=float, default=None, help="stop after N minutes")
    args = parser.parse_args()

    print("=" * 70)
    print("  MONEY EXTRACTOR 24/7 - profit-locked, gas-safe supervisor")
    print("  fires ONLY when: profit gate (bps) AND free on-chain simulation pass")
    print("  keys: env vars or bot_keys.local.json (never committed)")
    print("=" * 70)

    keys = load_keys()
    if not keys:
        print("[keys] NO KEYS FOUND - set PRIVATE_KEY / SOLANA_PRIVATE_KEY env vars")
        print("       or create bot_keys.local.json. Running scan-only (0 gas).")
    else:
        print(f"[keys] loaded. EVM wallet: {evm_address_of(keys)}")
        if keys.get("solana_address"):
            print(f"[keys] Solana wallet: {keys['solana_address']}")

    contract = cached_contract()
    if contract:
        _state["arb_contract"] = contract
        print(f"[keys] ArbExecutor already deployed: {contract}")

    write_status()
    rotation(keys, stop_after_minutes=args.minutes, once=args.once)
    write_status()
    print("[watch] supervisor stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

