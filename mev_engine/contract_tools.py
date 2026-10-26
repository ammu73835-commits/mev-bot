"""Compile / deploy the ArbExecutor contract (needs `solc` and a funded key)."""
import json
import os
import subprocess
import sys

from web3 import Web3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCE = os.path.join(ROOT, "contracts", "ArbExecutor.sol")
BUILD = os.path.join(HERE, "build")
ARTIFACT = os.path.join(BUILD, "ArbExecutor.json")


def compile_contract() -> dict:
    os.makedirs(BUILD, exist_ok=True)
    out = subprocess.run(
        ["solc", "--combined-json", "abi,bin", "--optimize", "--via-ir", SOURCE],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:400])
    data = json.loads(out.stdout)
    key = next(k for k in data["contracts"] if k.endswith(":ArbExecutor"))
    info = data["contracts"][key]
    abi = info["abi"]
    if isinstance(abi, str):
        abi = json.loads(abi)
    artifact = {"abi": abi, "bytecode": info["bin"]}
    with open(ARTIFACT, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)
    return artifact


def deploy_contract(rpc: str, private_key: str, chain_id: int) -> str:
    artifact = compile_contract()
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        raise ConnectionError(f"cannot reach {rpc}")
    account = w3.eth.account.from_key(private_key)
    factory = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    tx = factory.constructor().build_transaction(
        {
            "from": account.address,
            "chainId": chain_id,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 1_500_000,
            "gasPrice": int(w3.eth.gas_price * 1.15),
        }
    )
    signed = account.sign_transaction(tx)
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction")
    tx_hash = w3.eth.send_raw_transaction(raw)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return receipt["contractAddress"]


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "compile":
        artifact = compile_contract()
        print(f"compiled: {ARTIFACT} ({len(artifact['bytecode']) // 2} bytes)")
        return 0
    if sys.argv[1] == "deploy":
        rpc = os.getenv("RPC_URL")
        key = os.getenv("PRIVATE_KEY")
        chain_id = int(os.getenv("CHAIN_ID", "56"))
        if not rpc or not key:
            print("set RPC_URL and PRIVATE_KEY")
            return 2
        address = deploy_contract(rpc, key, chain_id)
        print(f"ArbExecutor deployed at {address}")
        print(f"export ARB_CONTRACT={address}")
        return 0
    print("usage: python -m mev_engine.contract_tools [compile|deploy]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
