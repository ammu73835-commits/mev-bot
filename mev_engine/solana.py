"""Solana cross-DEX arbitrage - real-time quotes via Jupiter (no SDK needed).

Jupiter routes to every Solana DEX; passing `dexes=<name>` pins the quote to a
single venue, which is exactly what a cross-DEX spread needs:

    buy on Raydium  ->  sell on Orca     (same lamports in/out)

The profit gate is the same one the EVM side uses (profit.py): net profit must
beat gas + the required margin in bps, otherwise nothing is signed.
"""
import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from . import profit as profitlib

LAMPORTS = 10**9
JUP_BASE = os.getenv("JUPITER_API", "https://lite-api.jup.ag/swap/v1")
QUOTE_URL = JUP_BASE.rstrip("/") + "/quote"
SWAP_URL = JUP_BASE.rstrip("/") + "/swap"
RPC_URL = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com")

WSOL = "So11111111111111111111111111111111111111112"

# Venues quoted independently. Jupiter rejects unknown labels, so a label that
# never answers is simply left out of the comparison.
DEXES = tuple(d.strip() for d in os.getenv("SOLANA_DEXES", "Raydium,Whirlpool,Meteora").split(",") if d.strip())

TOKENS: Dict[str, str] = {
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "JITOSOL": "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
}
# One token per cycle keeps us well inside the free Jupiter rate limit.
SWEEP_TOKENS = [t.strip().upper() for t in os.getenv("SOLANA_TOKENS", "USDC,JUP").split(",") if t.strip()]
SIZES = [float(x) for x in os.getenv("SOLANA_SIZES", "0.5,1,2").split(",") if x.strip()]
# 1 tx = 5_000 lamports signature fee + priority-fee head-room.
GAS_LAMPORTS = int(os.getenv("SOLANA_GAS_LAMPORTS", "20000"))
SLIPPAGE_BPS = int(os.getenv("SOLANA_SLIPPAGE_BPS", "50"))

_session = requests.Session()
_session.headers.update({"User-Agent": "mev-engine/solana"})


@dataclass
class SolanaOpp:
    token_symbol: str
    token_mint: str
    amount_in: int
    amount_out: int
    gas: int
    buy_dex: str
    sell_dex: str
    net: int
    min_margin_bps: int

    @property
    def net_bps(self) -> int:
        return profitlib.net_profit_bps(self.amount_in, self.net)

    @property
    def passes_gate(self) -> bool:
        return profitlib.is_profitable(self.amount_in, self.net, self.min_margin_bps)

    def as_row(self) -> str:
        verdict = "FIRE" if self.passes_gate else "skip"
        return (
            f"Solana   {self.token_symbol:<6} {self.buy_dex:>8} -> {self.sell_dex:<8} "
            f"in={self.amount_in / LAMPORTS:>6.3f} out={self.amount_out / LAMPORTS:>6.3f} "
            f"net={self.net / LAMPORTS:+.6f} ({self.net_bps:+4d} bps) "
            f"gas={self.gas / LAMPORTS:.5f} {verdict}"
        )


def quote(amount: int, token_in: str, token_out: str, dex: str, retries: int = 2) -> Optional[dict]:
    """One Jupiter quote pinned to a single DEX. None on any failure."""
    params = {
        "inputMint": token_in,
        "outputMint": token_out,
        "amount": int(amount),
        "slippageBps": SLIPPAGE_BPS,
        "onlyDirectRoutes": "true",
        "dexes": dex,
        "restrictIntermediateTokens": "true",
    }
    for attempt in range(retries + 1):
        try:
            resp = _session.get(QUOTE_URL, params=params, timeout=10)
            if resp.status_code == 429:          # rate limited: back off, retry
                time.sleep(1.5 * (attempt + 1))
                continue
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data if int(data.get("outAmount", 0)) > 0 else None
        except (requests.RequestException, ValueError):
            time.sleep(0.4 * (attempt + 1))
    return None


def scan_token(symbol: str, mint: str, sizes: List[float], min_margin_bps: int) -> List[SolanaOpp]:
    """Buy SOL->token on every DEX, sell token->SOL on every other DEX."""
    found: List[SolanaOpp] = []
    for size in sizes:
        amount = int(size * LAMPORTS)
        buys = {}
        for dex in DEXES:
            q = quote(amount, WSOL, mint, dex)
            if q:
                buys[dex] = int(q["outAmount"])
        if len(buys) < 2:
            continue
        for buy_dex, tokens_out in buys.items():
            for sell_dex in DEXES:
                if sell_dex == buy_dex:
                    continue
                q = quote(tokens_out, mint, WSOL, sell_dex)
                if not q:
                    continue
                out = int(q["outAmount"])
                net = profitlib.net_profit_wei(amount, out, 0, GAS_LAMPORTS)
                found.append(
                    SolanaOpp(symbol, mint, amount, out, GAS_LAMPORTS, buy_dex, sell_dex, net, min_margin_bps)
                )
    return found


def scan_cycle(min_margin_bps: int, cycle: int, tokens: Optional[List[str]] = None) -> List[SolanaOpp]:
    """Quote one token per cycle (rate-limit safe) and return every route."""
    chosen = tokens or SWEEP_TOKENS
    if not chosen:
        return []
    symbol = chosen[cycle % len(chosen)]
    mint = TOKENS.get(symbol)
    if not mint:
        return []
    return scan_token(symbol, mint, SIZES, min_margin_bps)
