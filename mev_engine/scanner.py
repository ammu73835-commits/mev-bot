"""Cross-DEX arbitrage scanner. Finds opportunities and prices them net of gas.

Speed: a whole sweep (tokens x sizes x routers) is priced with two Multicall3
round-trips instead of hundreds of individual eth_calls. That is the difference
between "a script" and a bot that can still catch a fresh imbalance.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from web3 import Web3

from . import profit
from .config import GAS_LIMIT_MULTIPLIER, MIN_NET_PROFIT_BPS, SCAN_WORKERS, Network
from .dex import Chain

WEI = 10**18
CALLS_PER_MULTICALL = 150


@dataclass
class Opportunity:
    network: str
    token_symbol: str
    token_address: str
    buy_router: str
    sell_router: str
    amount_in_wei: int
    token_amount_wei: int
    amount_out_wei: int
    fee_wei: int
    gas_wei: int
    net_wei: int
    net_bps: int
    gas_price_wei: int
    profitable: bool
    reason: str = ""

    def as_row(self) -> str:
        return (
            f"{self.network:<8} {self.token_symbol:<6} {self.buy_router:>11} -> "
            f"{self.sell_router:<11} in={self.amount_in_wei / WEI:>6.3f} "
            f"out={self.amount_out_wei / WEI:>6.3f} "
            f"net={self.net_wei / WEI:>+9.6f} ({self.net_bps:>+4} bps) "
            f"gas={self.gas_wei / WEI:.6f} "
            f"{'FIRE' if self.profitable else 'skip'}"
        )


def _quote_chunked(chain: Chain, requests, chunk_size: int = CALLS_PER_MULTICALL) -> Dict:
    """Run multicall requests in chunks (parallel) and merge the results."""
    requests = list(requests)
    if len(requests) <= chunk_size:
        return chain.quote_many(requests)
    chunks = [requests[i:i + chunk_size] for i in range(0, len(requests), chunk_size)]
    merged: Dict = {}
    with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as pool:
        for part in pool.map(chain.quote_many, chunks):
            merged.update(part)
    return merged


def price_route(
    network: Network,
    symbol: str,
    token: str,
    buy_router: str,
    sell_router: str,
    amount_in_wei: int,
    token_amount_wei: int,
    amount_out_wei: int,
    gas_price_wei: int,
    min_margin_bps: int = MIN_NET_PROFIT_BPS,
) -> Opportunity:
    """Apply the complete cost model to one route (gas + flash fee included)."""
    fee = profit.flash_fee(amount_in_wei, network.flash_fee_bps)
    gas = profit.gas_cost_wei(int(network.gas_units * GAS_LIMIT_MULTIPLIER), gas_price_wei)
    net = profit.net_profit_wei(amount_in_wei, amount_out_wei, fee, gas)
    bps = profit.net_profit_bps(amount_in_wei, net)
    ok = profit.is_profitable(amount_in_wei, net, min_margin_bps)
    reason = ""
    if not ok:
        reason = "below margin" if net > 0 else "negative after gas+fee"
    return Opportunity(
        network=network.name,
        token_symbol=symbol,
        token_address=token,
        buy_router=buy_router,
        sell_router=sell_router,
        amount_in_wei=amount_in_wei,
        token_amount_wei=token_amount_wei,
        amount_out_wei=amount_out_wei,
        fee_wei=fee,
        gas_wei=gas,
        net_wei=net,
        net_bps=bps,
        gas_price_wei=gas_price_wei,
        profitable=ok,
        reason=reason,
    )


def scan_pair(
    chain: Chain,
    network: Network,
    symbol: str,
    token: str,
    amount_in_wei: int,
    gas_price_wei: int,
    min_margin_bps: int = MIN_NET_PROFIT_BPS,
) -> List[Opportunity]:
    """Quote one token against the native coin on every router, both directions."""
    wrapped = Web3.to_checksum_address(network.wrapped)
    token = Web3.to_checksum_address(token)

    buys = chain.quote_many(
        [(name, name, wrapped, token, amount_in_wei) for name in chain.scan_venues]
    )
    buys = {name: out for name, out in buys.items() if out}
    if len(buys) < 2:
        return []

    best_buy = max(buys, key=buys.get)
    token_amount = buys[best_buy]
    sell_names = [name for name in chain.scan_venues if name != best_buy]
    sells = chain.quote_many(
        [(name, name, token, wrapped, token_amount) for name in sell_names]
    )

    return [
        price_route(
            network, symbol, token, best_buy, sell_name,
            amount_in_wei, token_amount, sells[sell_name],
            gas_price_wei, min_margin_bps,
        )
        for sell_name in sell_names
        if sells.get(sell_name)
    ]


def scan(
    chain: Chain,
    network: Network,
    trade_sizes,
    tokens: Optional[dict] = None,
    min_margin_bps: int = MIN_NET_PROFIT_BPS,
    workers: int = SCAN_WORKERS,
) -> List[Opportunity]:
    """Full sweep in two multicall rounds: all buys, then all sells."""
    tokens = tokens or network.tokens
    gas_price = chain.gas_price_wei()
    wrapped = Web3.to_checksum_address(network.wrapped)
    tasks: List[Tuple[str, str, float]] = [
        (symbol, Web3.to_checksum_address(address), size)
        for symbol, address in tokens.items()
        for size in trade_sizes
    ]

    # ---- round 1: native -> token on every router
    buy_reqs = []
    for symbol, address, size in tasks:
        amount_in = int(size * WEI)
        for router_name in chain.scan_venues:
            buy_reqs.append(
                ((symbol, size, router_name), router_name, wrapped, address, amount_in)
            )
    buy_quotes = _quote_chunked(chain, buy_reqs)

    # ---- cheapest router per (token, size) -> round 2: token -> native
    best_buys: Dict[Tuple[str, float], Tuple[str, int]] = {}
    for symbol, address, size in tasks:
        options = {
            name: buy_quotes.get((symbol, size, name)) for name in chain.scan_venues
        }
        options = {k: v for k, v in options.items() if v}
        if len(options) >= 2:
            cheapest = max(options, key=options.get)
            best_buys[(symbol, size)] = (cheapest, options[cheapest])

    sell_reqs = []
    token_by_key = {(symbol, size): address for symbol, address, size in tasks}
    for (symbol, size), (cheapest, token_amount) in best_buys.items():
        for router_name in chain.scan_venues:
            if router_name == cheapest:
                continue
            sell_reqs.append(
                (
                    (symbol, size, cheapest, router_name),
                    router_name,
                    token_by_key[(symbol, size)],
                    wrapped,
                    token_amount,
                )
            )
    sell_quotes = _quote_chunked(chain, sell_reqs)

    opportunities: List[Opportunity] = []
    for (symbol, size), (cheapest, token_amount) in best_buys.items():
        for router_name in chain.scan_venues:
            if router_name == cheapest:
                continue
            amount_out = sell_quotes.get((symbol, size, cheapest, router_name))
            if not amount_out:
                continue
            opportunities.append(
                price_route(
                    network,
                    symbol,
                    token_by_key[(symbol, size)],
                    cheapest,
                    router_name,
                    int(size * WEI),
                    token_amount,
                    amount_out,
                    gas_price,
                    min_margin_bps,
                )
            )

    opportunities.sort(key=lambda o: o.net_wei, reverse=True)
    return opportunities


def best(opportunities: List[Opportunity]) -> Optional[Opportunity]:
    return opportunities[0] if opportunities else None


def profitable(opportunities: List[Opportunity]) -> List[Opportunity]:
    return [o for o in opportunities if o.profitable]

