"""Continuous profit-gated arbitrage loop.

Usage:
    python -m mev_engine.run_engine --network BSC --seconds 600
    python -m mev_engine.run_engine --network all --seconds 300   # all 5 networks
    DRY_RUN=0 ARB_CONTRACT=0x... PRIVATE_KEY=0x... python -m mev_engine.run_engine --network BSC

Default is DRY-RUN: quotes + profit gate + optional simulation, never broadcasts.
"""
import argparse
import os
import sys
import time

from . import profit
from .config import DRY_RUN, MIN_NET_PROFIT_BPS, NETWORKS, TRADE_SIZES, get_network
from .dex import Chain
from .executor import Executor
from .scanner import Opportunity, best, profitable, scan

WEI = 10**18
ALL_ALIASES = ("all", "*", "every", "networks")
SOLANA_ALIASES = ("solana", "sol", "spl")
SOLANA_NAME = "Solana"


def parse_tokens(network, only):
    if not only:
        return network.tokens
    wanted = {t.strip().upper() for t in only.split(",") if t.strip()}
    return {k: v for k, v in network.tokens.items() if k.upper() in wanted}


def run_network(network, seconds, args) -> dict:
    """Scan one chain for `seconds` and return a one-line summary."""
    dry_run = DRY_RUN and not args.live
    chain = Chain(network)
    chain.connect()

    # The ArbExecutor lives on ONE chain: never broadcast on any other chain.
    contract = os.getenv("ARB_CONTRACT")
    private_key = os.getenv("PRIVATE_KEY") if not DRY_RUN else None
    live_chain = os.getenv("ARB_NETWORK", "BSC").strip().lower()
    if network.name.lower() != live_chain:
        contract = private_key = None

    executor = Executor(
        chain,
        network,
        contract=contract,
        private_key=private_key,
        min_margin_bps=args.min_bps,
    )

    tokens = parse_tokens(network, args.tokens)
    deadline = time.time() + seconds
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

    summary = {
        "name": network.name,
        "cycles": cycles,
        "fired": fired,
        "quotes": chain.stats["quotes"],
        "misses": chain.stats["errors"],
        "best": (f"{seen_best.net_wei / WEI:+.6f} native ({seen_best.net_bps:+} bps) "
                 f"{seen_best.token_symbol} {seen_best.buy_router}->{seen_best.sell_router}"
                 if seen_best else "none"),
    }
    print("-" * 78)
    print(f"  cycles={cycles} profitable-routes={fired} quotes={summary['quotes']} "
          f"quote-misses={summary['misses']}")
    if seen_best:
        print(f"  best net seen: {summary['best']}")
    else:
        print("  best net seen: none (no cross-DEX spread beat gas + fees)")
    print(f"  gas spent: {'0 (dry-run)' if dry_run else f'{fired} tx'}")
    print("=" * 78)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="MEV arbitrage engine (profit-gated)")
    parser.add_argument("--network", default=os.getenv("NETWORK", "BSC"),
                        help="network name, or 'all' for every configured chain")
    parser.add_argument("--seconds", type=int, default=int(os.getenv("RUN_SECONDS", "300")))
    parser.add_argument("--interval", type=float, default=float(os.getenv("SCAN_INTERVAL", "8")))
    parser.add_argument("--min-bps", type=int, default=MIN_NET_PROFIT_BPS)
    parser.add_argument("--tokens", default=os.getenv("TOKENS", ""))
    parser.add_argument("--live", action="store_true", help="broadcast when profitable")
    args = parser.parse_args(argv)

    requested = (args.network or "BSC").strip()
    if requested.lower() in ALL_ALIASES:
        names = list(NETWORKS) + [SOLANA_NAME]
    else:
        names = [requested]
    per_network = max(15, args.seconds // max(1, len(names)))

    rows = []
    for name in names:
        if name.lower() in SOLANA_ALIASES:
            try:
                from . import solana

                rows.append(solana.run(per_network, args.interval, args.min_bps))
            except Exception as exc:            # never let Solana kill the EVM loop
                print(f"  Solana skipped: {exc}")
            continue
        try:
            network = get_network(name)
        except KeyError as exc:
            print(exc)
            return 2
        rows.append(run_network(network, per_network, args))

    if len(rows) > 1:
        print("  RECAP (all networks)")
        for row in rows:
            print(f"  {row['name']:<9} cycles={row['cycles']:<4} quotes={row['quotes']:<7} "
                  f"misses={row['misses']:<6} profitable={row['fired']:<3} best={row['best']}")
        print("  TOTAL     quotes=" + str(sum(r["quotes"] for r in rows))
              + " profitable-routes=" + str(sum(r["fired"] for r in rows)))
        print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
