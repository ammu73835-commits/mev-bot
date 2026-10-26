"""MEV engine: profit-gated cross-DEX arbitrage (dry-run by default).

Design rules:
  * NEVER send a transaction unless simulated net profit > gas + fees + margin.
  * Atomic execution (Uniswap-V2 flash swap) so no capital and no gas is wasted.
  * Every decision is logged with the exact numbers used (auditable).
"""

__version__ = "1.0.0"
