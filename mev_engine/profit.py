"""Pure profit math - no web3 dependency, fully unit-testable.

All amounts are integers in wei unless the name says otherwise.
"""
from typing import Optional

BPS_DENOMINATOR = 10_000
WEI_PER_ETHER = 10**18


def apply_bps(amount: int, bps: int) -> int:
    """amount * bps / 10_000 (floored)."""
    return amount * bps // BPS_DENOMINATOR


def flash_fee(amount_in: int, fee_bps: int) -> int:
    """Flash-loan premium owed back on `amount_in`."""
    return apply_bps(amount_in, fee_bps)


def gas_cost_wei(gas_units: int, gas_price_wei: int) -> int:
    """Total gas cost in native wei."""
    return gas_units * gas_price_wei


def net_profit_wei(amount_in: int, amount_out: int, fee_wei: int, gas_wei: int) -> int:
    """Profit left after repaying the flash loan and paying gas.

    amount_out is what the sell leg returns in the borrowed token.
    """
    gross = amount_out - amount_in
    return gross - fee_wei - gas_wei


def net_profit_bps(amount_in: int, net_wei: int) -> int:
    """Net profit expressed in basis points of the trade size."""
    if amount_in <= 0:
        return 0
    return net_wei * BPS_DENOMINATOR // amount_in


def is_profitable(amount_in: int, net_wei: int, min_margin_bps: int) -> bool:
    """The one and only gas-spending gate.

    True only when net profit (already net of gas and flash fee) is above the
    required margin in bps of the trade size. Nothing else may spend gas.
    """
    if amount_in <= 0 or net_wei <= 0:
        return False
    return net_profit_bps(amount_in, net_wei) >= min_margin_bps


def worst_case_out(amount_out: int, slippage_bps: int) -> int:
    """Amount to require on-chain when we cannot simulate (defensive)."""
    return amount_out - apply_bps(amount_out, slippage_bps)


def best_route(
    quotes: dict,
) -> Optional[tuple]:
    """Pick the (buy_router, sell_router) with the highest output.

    quotes: {(buy, sell): amount_out_wei}
    """
    if not quotes:
        return None
    (buy, sell), out = max(quotes.items(), key=lambda kv: kv[1])
    return buy, sell, out
