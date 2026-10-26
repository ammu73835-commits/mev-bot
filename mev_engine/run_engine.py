"""Continuous profit-gated arbitrage loop.

Usage:
    python -m mev_engine.run_engine --network BSC --seconds 600
    DRY_RUN=0 ARB_CONTRACT=0x... PRIVATE_KEY=0x... python -m mev_engine.run_engine --network BSC

Default is DRY-RUN: quotes + profit gate + optional simulation, never broadcasts.
"""
import argparse
import os
import sys
import time

from . import profit
from .config import DRY_RUN, MIN_NET_PROFIT_BPS, TRADE_SIZES, get_network
from .dex import Chain
from .executor import Executor
from .scanner import Opportunity, best, profitable, scan

WEI = 10**18


def parse_tokens(network, only):
    if not only:
        return network.tokens
    wanted = {t.strip().upper() for t in only.split(",") if t.strip()}
    return {k: v for k, v in network.tokens.items() if k.upper() in wanted}


def main(argv=None):
    parser = argparse.ArgumentParser(description="MEV arbitrage engine (profit-gated)")
    parser.add_argument("--network", default=os.getenv("NETWORK", "BSC"))
    parser.add_argument("--seconds", type=int, default=int(os.getenv("RUN_SECONDS", "300")))
    parser.add_argument("--interval", type=float, default=float(os.getenv("SCAN_INTERVAL", "8")))
    parser.add_argument("--min-bps", type=int, default=MIN_NET_PROFIT_BPS)
    parser.add_argument("--tokens", default=os.getenv("TOKENS", ""))
    parser.add_argument("--live", action="store_true", help="broadcast when profitable")
    args = parser.parse_args(argv)

    try:
        network = get_network(args.network)
    except KeyError as exc:
        print(exc)
        return 2

    dry_run = DRY_RUN and not args.live
    chain = Chain(network)
    chain.connect()

    executor = Executor(
        chain,
        network,
        contract=os.getenv("ARB_CONTRACT"),
        private_key=os.getenv("PRIVATE_KEY") if not DRY_RUN else None,
        min_margin_bps=args.min_bps,
    )

    tokens = parse_tokens(network, args.tokens)
    deadline = time.time() + args.seconds
    cycles = 0
    fired = 0
    best_net = 0
    seen_best: Opportunity | None = None

    print("=" * 78)
    print(f"  MEV ENGINE | {network.name} | {len(tokens)} tokens x {len(TRADE_SIZES)} sizes "
          f"| {len(network.venues)} DEX venues")
    print(f"  mode={'DRY-RUN (0 gas possible)' if dry_run else 'LIVE'} | "
          f"min margin={args.min_bps} bps | executor={'ready' if executor.ready else 'not deployed'}")
    dead = chain.dead_venues()
    if dead:
        print(f"  WARNING: no contract at {', '.join(dead)} - check the address")
    print("=" * 78)


    while time.time() < deadline:
        cycles += 1
        try:
            if not chain.w3.is_connected():
                chain.connect()
            opportunities = scan(chain, network, TRADE_SIZES, tokens, args.min_bps)
        except Exception as exc:
            print(f"[cycle {cycles}] error: {exc}; rotating RPC")
            try:
                chain.rotate()
            except Exception:
                pass
            time.sleep(min(5, args.interval))
            continue

        top = best(opportunities)
        if top:
            if top.net_wei > best_net:
                best_net, seen_best = top.net_wei, top
            print(f"[cycle {cycles}] best: {top.as_row()}")
        else:
            print(f"[cycle {cycles}] no routes quoted (RPC/pools)")

        winners = profitable(opportunities)
        for opp in winners:
            ok, note = executor.fire(opp)
            if ok:
                fired += 1
                print(f"  >>> FIRED: {note}")
            else:
                print(f"  >>> WOULD FIRE: {opp.net_wei / WEI:+.6f} {network.name} via "
                      f"{opp.buy_router}->{opp.sell_router} ({note})")

        time.sleep(args.interval)

    print("-" * 78)
    print(f"  cycles={cycles} profitable-routes={fired} quotes={chain.stats['quotes']} "
          f"quote-misses={chain.stats['errors']}")
    if seen_best:
        print(f"  best net seen: {seen_best.net_wei / WEI:+.6f} native "
              f"({seen_best.net_bps:+} bps) on {seen_best.token_symbol} "
              f"{seen_best.buy_router}->{seen_best.sell_router}")
    else:
        print("  best net seen: none (no cross-DEX spread beat gas + fees)")
    print(f"  gas spent: {'0 (dry-run)' if dry_run else f'{fired} tx'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
