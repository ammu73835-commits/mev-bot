# MEV Engine — cross-DEX arbitrage on BSC + Polygon

Profit-gated, gas-safe arbitrage across Uniswap-V2 **and** Uniswap-V3 style
venues. Default mode is **dry-run**: it quotes everything, prices every route,
simulates on-chain (free `eth_call`) and spends **zero gas** until you provide
`ARB_CONTRACT` + `PRIVATE_KEY` and set `LIVE=1`.

```
python -m mev_engine.run_engine --network BSC --seconds 60
python -m mev_engine.run_engine --network polygon --tokens USDC,USDT --min-bps 15
python -m unittest discover -s tests -t .
```

## How a cycle works

1. **Sweep** (`scanner.scan`): round 1 quotes native→token on *every* venue for
   every trade size; round 2 quotes token→native only for the best buy of each
   (token, size). Each round is a single `eth_call` via Multicall3
   (`0xcA11…CA11`, same address on every chain) — 1–2 RTTs per full sweep.
2. **Cost model** (`scanner.price_route` → `profit.py`): a route must survive
   flash fee + gas + margin. `net = out − amount_in − flash_fee − gas`;
   FIRE only when `net ≥ MIN_NET_PROFIT_BPS` of `amount_in` (default 10 bps).
3. **Simulate** (`executor.simulate`): `eth_call` of `ArbExecutor.arb(...)`,
   still free. A revert here costs nothing.
4. **Fire** (`executor.fire`): one atomic transaction. The capital is borrowed
   from a V2 pair (flash swap), swapped twice, repaid; if the route is not
   profitable on-chain the whole tx reverts, so the worst case is the gas of
   that single tx — and only after the gate + simulation both passed.

## Venues

| Network | V2 | V3 fee tiers |
|---|---|---|
| BSC (56) | PancakeV2 (flash), BiswapV2, SushiBSC, BakeryV2 | PancakeV3 100 / 500 / 2500 |
| Polygon (137) | QuickSwapV2 (flash), SushiV2 | UniV3 500 / 3000 |

Each `Venue` (`config.py`) is either `kind="v2"` (quoted with
`getAmountsOut`) or `kind="v3"` (quoted with `QuoterV2.quoteExactInputSingle`
for one fee tier). V3 is the edge: a 0.01 % pool is 2 bps round-trip versus
2 × 0.25 % on V2, which is often the difference between a live and dead spread.
`Chain.dead_venues()` warns at start-up if a configured address has no bytecode.

## Layout

| File | Role |
|---|---|
| `config.py` | `Venue` / `Network` dataclasses, tokens, RPCs, safety locks |
| `dex.py` | RPC rotation, V2/V3 calldata + decode, Multicall3 `quote_many` |
| `scanner.py` | two-round sweep, `Opportunity`, full cost model |
| `profit.py` | pure profit math (no I/O) — unit-tested |
| `executor.py` | `ArbExecutor` ABI, simulation, atomic fire |
| `run_engine.py` | CLI loop, dry-run by default, RPC failover |
| `contract_tools.py` | `solc --via-ir` compile + deploy |
| `../contracts/ArbExecutor.sol` | V2 flash swap, V2 **or** V3 legs, minProfit guard |

## Safety locks (env vars)

| Var | Default | Meaning |
|---|---|---|
| `MIN_NET_PROFIT_BPS` | `10` | minimum net profit, in bps of trade size |
| `GAS_LIMIT_MULTIPLIER` | `1.25` | gas head-room on the estimate |
| `PRIORITY_TIP_BPS` | `1500` | +15 % on the node gas price |
| `MAX_GAS_PRICE_GWEI` | `0` | hard gas-price cap (0 = off) |
| `DRY_RUN` / `LIVE` | `1` / — | `LIVE=1` disables dry-run |
| `TRADE_SIZES` | `0.5,1,2` | native sizes scanned, in BNB / MATIC |
| `ARB_CONTRACT`, `PRIVATE_KEY` | — | required to actually broadcast |

## Going live

```
python -m mev_engine.contract_tools compile
# fund the key with a little BNB, then:
set ARB_CONTRACT=0x...   &  set PRIVATE_KEY=0x...  &  set LIVE=1
python -m mev_engine.run_engine --network BSC --seconds 900
```

Cloud: `.github/workflows/mev-engine-cloud.yml` runs the tests, then the engine
(cron every 5 h + manual dispatch). It stays dry-run unless the `ARB_CONTRACT`,
`PRIVATE_KEY` and `LIVE=1` repo secrets/vars are set.
