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
from typing import Dict, List, Optional, Tuple

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
# The two legs are sequential, not atomic: demand a wider edge than the EVM side.
SOL_MIN_BPS = int(os.getenv("SOLANA_MIN_BPS", "25"))
STATS = {"quotes": 0, "errors": 0}

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
                STATS["errors"] += 1
                return None
            data = resp.json()
            if int(data.get("outAmount", 0)) > 0:
                STATS["quotes"] += 1
                return data
            STATS["errors"] += 1
            return None
        except (requests.RequestException, ValueError):
            STATS["errors"] += 1
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


# --------------------------------------------------------------------- execution
class SolanaExecutor:
    """Sends the two Jupiter swaps that make up one Solana round trip.

    Solana has no flash-loan primitive we can call permissionlessly, so a route is
    executed as two sequential Jupiter swaps (buy leg, then sell leg). The first
    leg is the only real risk: it is sent only after the profit gate passes, and
    the sell leg is quoted immediately before signing. A failure on leg two can
    leave us holding the intermediate token - that is why min_margin_bps defaults
    higher here than on the EVM side.
    """

    def __init__(self, private_key: Optional[str] = None, min_margin_bps: int = SOL_MIN_BPS,
                 rpc: str = RPC_URL):
        self.private_key = private_key
        self.min_margin_bps = min_margin_bps
        self.rpc = rpc
        self._keypair = None
        if private_key:
            try:
                from solders.keypair import Keypair  # optional dependency

                self._keypair = Keypair.from_base58_string(private_key)
            except Exception:
                self._keypair = None

    @property
    def ready(self) -> bool:
        return self._keypair is not None

    @property
    def address(self) -> Optional[str]:
        return str(self._keypair.pubkey()) if self._keypair else None

    # ------------------------------------------------------------------ helpers
    def _swap_tx(self, amount: int, token_in: str, token_out: str, dex: str) -> Optional[str]:
        """Ask Jupiter to build the swap transaction for one pinned route."""
        q = quote(amount, token_in, token_out, dex)
        if not q:
            return None
        body = {
            "quoteResponse": q,
            "userPublicKey": self.address,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
        }
        try:
            resp = _session.post(SWAP_URL, json=body, timeout=20)
            if resp.status_code != 200:
                return None
            return resp.json().get("swapTransaction")
        except (requests.RequestException, ValueError):
            return None

    def _send(self, tx_b64: str) -> Optional[str]:
        """Sign a Jupiter v0 transaction with solders and broadcast it."""
        from solders.transaction import VersionedTransaction

        raw = base64.b64decode(tx_b64)
        tx = VersionedTransaction.from_bytes(raw)
        signed = VersionedTransaction(tx.message, [self._keypair])
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [
                base64.b64encode(bytes(signed)).decode(),
                {"encoding": "base64", "skipPreflight": False, "maxRetries": 3},
            ],
        }
        try:
            resp = _session.post(self.rpc, json=payload, timeout=25)
            data = resp.json()
            return data.get("result") or (data.get("error", {}) or {}).get("message")
        except (requests.RequestException, ValueError):
            return None

    # --------------------------------------------------------------------- fire
    def fire(self, opp: SolanaOpp) -> Tuple[bool, str]:
        if not self.ready:
            return False, "DRY-RUN (no Solana keypair configured)"
        if not opp.passes_gate:
            return False, "profit gate failed"

        buy_tx = self._swap_tx(opp.amount_in, WSOL, opp.token_mint, opp.buy_dex)
        if not buy_tx:
            return False, f"buy leg rejected by Jupiter ({opp.buy_dex})"
        buy_sig = self._send(buy_tx)
        if not buy_sig or len(str(buy_sig)) < 32:
            return False, f"buy leg not sent: {buy_sig}"
        time.sleep(1.0)  # let the balance settle before quoting the sell leg

        sell_tx = self._swap_tx(opp.amount_out, opp.token_mint, WSOL, opp.sell_dex)
        if not sell_tx:
            return True, f"bought on {opp.buy_dex} ({buy_sig}); sell quote lost on {opp.sell_dex}"
        sell_sig = self._send(sell_tx)
        return True, f"{opp.buy_dex} {buy_sig} -> {opp.sell_dex} {sell_sig}"


# ------------------------------------------------------------------------- loop
def run(seconds: int = 120, interval: float = 8.0, min_bps: int = SOL_MIN_BPS,
        tokens: Optional[List[str]] = None, executor: Optional[SolanaExecutor] = None) -> dict:
    """Scan Solana for `seconds` and return a summary shaped like the EVM rows."""
    if executor is None:
        executor = SolanaExecutor(os.getenv("SOLANA_PRIVATE_KEY") or None, min_bps)

    deadline = time.time() + seconds
    cycles = 0
    fired = 0
    best: Optional[SolanaOpp] = None

    print("=" * 78)
    print(f"  MEV ENGINE | Solana | {len(SWEEP_TOKENS)} tokens x {len(SIZES)} sizes "
          f"| {len(DEXES)} DEX venues")
    print(f"  mode={'DRY-RUN (0 lamports possible)' if not executor.ready else 'LIVE'}"
          f" | min margin={min_bps} bps | wallet={executor.address or 'none'}")
    print("=" * 78)

    while time.time() < deadline:
        cycles += 1
        try:
            routes = scan_cycle(min_bps, cycles - 1, tokens)
        except Exception as exc:
            print(f"[cycle {cycles}] error: {exc}")
            time.sleep(min(5, interval))
            continue

        if not routes:
            print(f"[cycle {cycles}] no routes quoted (Jupiter/rate-limit)")
            time.sleep(interval)
            continue

        top = max(routes, key=lambda r: r.net)
        if best is None or top.net > best.net:
            best = top
        print(f"[cycle {cycles}] best: {top.as_row()}")

        for opp in routes:
            if not opp.passes_gate:
                continue
            ok, note = executor.fire(opp)
            if ok:
                fired += 1
                print(f"  >>> FIRED: {note}")
            else:
                print(f"  >>> WOULD FIRE: {opp.net / LAMPORTS:+.6f} SOL {opp.buy_dex}->"
                      f"{opp.sell_dex} ({note})")

        time.sleep(interval)

    summary = {
        "name": "Solana",
        "cycles": cycles,
        "fired": fired,
        "quotes": STATS["quotes"],
        "misses": STATS["errors"],
        "best": (f"{best.net / LAMPORTS:+.6f} SOL ({best.net_bps:+} bps) {best.token_symbol} "
                 f"{best.buy_dex}->{best.sell_dex}" if best else "none"),
    }
    print("-" * 78)
    print(f"  cycles={cycles} profitable-routes={fired} quotes={summary['quotes']} "
          f"quote-misses={summary['misses']}")
    print(f"  best net seen: {summary['best']}")
    print(f"  lamports spent: {'0 (dry-run)' if not executor.ready else f'{fired} legs'}")
    print("=" * 78)
    return summary


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Solana cross-DEX scanner (Jupiter, per-DEX)")
    ap.add_argument("--seconds", type=int, default=int(os.getenv("RUN_SECONDS", "120")))
    ap.add_argument("--interval", type=float, default=float(os.getenv("SCAN_INTERVAL", "8")))
    ap.add_argument("--min-bps", type=int, default=SOL_MIN_BPS)
    ap.add_argument("--tokens", default="")
    ns = ap.parse_args()
    picked = [t.strip().upper() for t in ns.tokens.split(",") if t.strip()] or None
    run(ns.seconds, ns.interval, ns.min_bps, picked)

