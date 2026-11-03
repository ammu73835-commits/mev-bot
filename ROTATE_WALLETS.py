#!/usr/bin/env python3
"""
ROTATE_WALLETS.py - swap in YOUR OWN wallet keys, safely, in 30 seconds.

Why this is safe:
  - You paste keys into a LOCAL hidden prompt (getpass) - nothing is echoed,
    nothing is committed, nothing goes to any chat or public place.
  - Keys are saved ONLY to bot_keys.local.json (git-ignored) and to
    GitHub Secrets (encrypted on GitHub's servers, unreadable to sweepers).
  - A pre-commit hook also blocks keys from ever entering git history.

Run:  python ROTATE_WALLETS.py
Then: fund YOUR wallet addresses from any wallet/exchange you like.
"""
import getpass
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS_FILE = HERE / "bot_keys.local.json"
REPO = "ammu73835-commits/mev-bot"


def main():
    print("=" * 62)
    print("  WALLET ROTATION - your keys never leave this PC + GitHub Secrets")
    print("=" * 62)

    evm_key = getpass.getpass("Paste NEW EVM private key (hidden, Enter when done): ").strip()
    sol_key = getpass.getpass("Paste NEW Solana secret key base58 (hidden): ").strip()
    if not evm_key and not sol_key:
        print("Nothing entered - nothing changed.")
        return 0

    data = {}
    if evm_key:
        if evm_key.startswith("0x"):
            evm_key = evm_key[2:]
        from web3 import Web3
        acct = Web3().eth.account.from_key(evm_key)
        data["evm_private_key"] = evm_key
        data["evm_address"] = acct.address
        print(f"\nEVM wallet address: {acct.address}  <-- fund BNB (BSC) here")
    if sol_key:
        try:
            from solders.keypair import Keypair
            kp = Keypair.from_base58_string(sol_key)
            data["solana_private_key_base58"] = sol_key
            data["solana_address"] = str(kp.pubkey())
            print(f"Solana wallet address: {kp.pubkey()}  <-- fund SOL here")
        except Exception as exc:
            print(f"Solana key rejected ({exc}) - skipped.")
    if not data:
        print("No valid keys - nothing changed.")
        return 1

    # keep old note out; write fresh
    KEYS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nSaved locally to {KEYS_FILE.name} (git-ignored).")

    # push to GitHub Secrets (encrypted server-side)
    try:
        if "evm_private_key" in data:
            subprocess.run(["gh", "secret", "set", "PRIVATE_KEY", "-R", REPO,
                           "--body", data["evm_private_key"]], check=True)
            print("GitHub Secret PRIVATE_KEY updated.")
        if "solana_private_key_base58" in data:
            subprocess.run(["gh", "secret", "set", "SOLANA_PRIVATE_KEY", "-R", REPO,
                           "--body", data["solana_private_key_base58"]], check=True)
            print("GitHub Secret SOLANA_PRIVATE_KEY updated.")
    except Exception as exc:
        print(f"WARNING: GitHub Secrets not updated ({exc}).")
        print("Cloud still uses the previous keys until you re-run this.")

    print("\nDONE. Restart not needed - both bots pick the file up next cycle.")
    print("Fund the addresses shown above, then you are finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
