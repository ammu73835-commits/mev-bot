"""Atomic execution layer.

Nothing here spends gas unless:
  1. the scanner says net profit > margin (gas + flash fee + slippage already
     deducted), and
  2. the on-chain simulation (eth_call, free) returns a profit >= minProfit.

Execution is a Uniswap-V2 flash swap: the capital is borrowed inside the same
transaction, so a non-profitable route reverts atomically and the only possible
loss is the gas of that single transaction - which is why the profit gate runs
first.
"""
import os
from typing import Optional, Tuple

from web3 import Web3

from . import profit as profitlib
from .config import (
    GAS_LIMIT_MULTIPLIER,
    MAX_GAS_PRICE_GWEI,
    PRIORITY_TIP_BPS,
    Network,
)
from .dex import Chain
from .scanner import Opportunity

WEI = 10**18
GWEI = 10**9
ZERO_ADDRESS = "0x0000000000000000000000000000000000000001"

LEG_COMPONENTS = [
    {"internalType": "uint8", "name": "kind", "type": "uint8"},
    {"internalType": "address", "name": "target", "type": "address"},
    {"internalType": "address", "name": "tokenIn", "type": "address"},
    {"internalType": "address", "name": "tokenOut", "type": "address"},
    {"internalType": "uint24", "name": "fee", "type": "uint24"},
]

ARB_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "flashPair", "type": "address"},
            {"internalType": "address", "name": "tokenIn", "type": "address"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "minProfit", "type": "uint256"},
            {"internalType": "uint16", "name": "flashFeeBps", "type": "uint16"},
            {"components": LEG_COMPONENTS, "internalType": "struct ArbExecutor.Leg", "name": "buy", "type": "tuple"},
            {"components": LEG_COMPONENTS, "internalType": "struct ArbExecutor.Leg", "name": "sell", "type": "tuple"},
        ],
        "name": "arb",
        "outputs": [{"internalType": "uint256", "name": "profit", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]



class Executor:
    def __init__(
        self,
        chain: Chain,
        network: Network,
        contract: Optional[str] = None,
        private_key: Optional[str] = None,
        min_margin_bps: int = 10,
    ):
        self.chain = chain
        self.network = network
        self.contract = Web3.to_checksum_address(contract) if contract else None
        self.private_key = private_key
        self.min_margin_bps = min_margin_bps
        self.account = None
        if private_key:
            self.account = self.chain.w3.eth.account.from_key(private_key)

    # ------------------------------------------------------------------ helpers
    @property
    def ready(self) -> bool:
        return bool(self.contract and self.account)

    def flash_pair(self, opp: Opportunity) -> Optional[str]:
        """V2 pair we borrow the flash loan from (must hold wrapped + token)."""
        venue = self.network.flash_venue()
        if not venue.factory:
            return None
        return self.chain.pair_address(venue.factory, self.network.wrapped, opp.token_address)

    def leg(self, venue_name: str, token_in: str, token_out: str) -> tuple:
        """Encode one swap leg for ArbExecutor (kind 0 = V2 router, 1 = V3 router)."""
        venue = self.chain.venues[venue_name]
        return (
            0 if venue.kind == "v2" else 1,
            Web3.to_checksum_address(venue.target),
            Web3.to_checksum_address(token_in),
            Web3.to_checksum_address(token_out),
            int(venue.fee or 0),
        )

    def build_args(self, opp: Opportunity) -> Optional[tuple]:
        pair = self.flash_pair(opp)
        if not pair:
            return None
        wrapped = Web3.to_checksum_address(self.network.wrapped)
        min_profit = max(int(opp.net_wei * 0.5), 1)  # on-chain guard: half of expected
        return (
            Web3.to_checksum_address(pair),
            wrapped,
            opp.amount_in_wei,
            min_profit,
            self.network.flash_fee_bps,
            self.leg(opp.buy_router, wrapped, opp.token_address),
            self.leg(opp.sell_router, opp.token_address, wrapped),
        )

    # --------------------------------------------------------------- simulation
    def simulate(self, opp: Opportunity) -> Tuple[bool, int, str]:
        """Free on-chain check via eth_call. Returns (ok, profit_wei, note)."""
        if not self.contract:
            return False, 0, "ArbExecutor not deployed"
        args = self.build_args(opp)
        if not args:
            return False, 0, "flash pair missing"
        try:
            contract = self.chain.w3.eth.contract(address=self.contract, abi=ARB_ABI)
            sender = self.account.address if self.account else ZERO_ADDRESS
            simulated = int(contract.functions.arb(*args).call({"from": sender}))
            ok = simulated > 0
            return ok, simulated, f"simulated profit {simulated / WEI:.6f}"
        except Exception as exc:
            return False, 0, str(exc).splitlines()[0][:180]


    # -------------------------------------------------------------------- fire
    def fire(self, opp: Opportunity) -> Tuple[bool, str]:
        """Send the atomic arbitrage transaction. Returns (sent, info)."""
        if not self.ready:
            return False, "DRY-RUN (no contract/private key configured)"
        if not profitlib.is_profitable(opp.amount_in_wei, opp.net_wei, self.min_margin_bps):
            return False, "profit gate failed"

        args = self.build_args(opp)
        if not args:
            return False, "flash pair missing"

        ok, simulated, note = self.simulate(opp)
        if not ok:
            return False, f"simulation rejected: {note}"

        w3 = self.chain.w3
        gas_price = int(w3.eth.gas_price * (1 + PRIORITY_TIP_BPS / 10_000))
        if MAX_GAS_PRICE_GWEI > 0:
            gas_price = min(gas_price, int(MAX_GAS_PRICE_GWEI * GWEI))
        gas_limit = int(self.network.gas_units * GAS_LIMIT_MULTIPLIER)

        contract = w3.eth.contract(address=self.contract, abi=ARB_ABI)
        tx = contract.functions.arb(*args).build_transaction(
            {
                "from": self.account.address,
                "chainId": self.network.chain_id,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "nonce": w3.eth.get_transaction_count(self.account.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction")
        tx_hash = w3.eth.send_raw_transaction(raw)
        return True, f"{self.network.explorer}/tx/{tx_hash.hex()}"
