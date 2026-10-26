"""Profit-gate unit tests - the rules that decide whether gas may be spent."""
import unittest

from mev_engine import profit
from mev_engine.config import BSC
from mev_engine.scanner import Opportunity, price_route

WEI = 10**18


class TestPriceRoute(unittest.TestCase):
    """The full cost model that decides FIRE vs skip."""

    def make(self, out_wei, gas_price=5 * 10**9, min_bps=10):
        return price_route(
            BSC, "USDT", BSC.tokens["USDT"], "PancakeV2", "BiswapV2",
            WEI, 2 * WEI, out_wei, gas_price, min_bps,
        )

    def test_one_percent_spread_fires(self):
        opp = self.make(WEI + WEI // 100)          # +1.00 %
        self.assertGreater(opp.net_wei, 0)
        self.assertTrue(opp.profitable, opp.reason)
        self.assertGreaterEqual(opp.net_bps, 10)

    def test_pool_fees_alone_do_not_fire(self):
        # classic 2 x 0.30 % round trip => negative
        opp = self.make(WEI - WEI * 60 // 10_000)
        self.assertLess(opp.net_wei, 0)
        self.assertFalse(opp.profitable)

    def test_gas_can_kill_a_small_edge(self):
        cheap_gas = self.make(WEI + WEI * 60 // 10_000, gas_price=1 * 10**9)
        pricey_gas = self.make(WEI + WEI * 60 // 10_000, gas_price=400 * 10**9)
        self.assertTrue(cheap_gas.profitable, cheap_gas.reason)
        self.assertFalse(pricey_gas.profitable, pricey_gas.reason)

    def test_fee_is_flash_pool_rate(self):
        opp = self.make(WEI + WEI // 100)
        self.assertEqual(opp.fee_wei, WEI * BSC.flash_fee_bps // 10_000)

    def test_net_bps_math(self):
        opp = self.make(WEI + WEI // 100)
        self.assertEqual(opp.net_bps, opp.net_wei * 10_000 // WEI)

    def test_row_is_readable(self):
        row = self.make(WEI + WEI // 100).as_row()
        self.assertIn("FIRE", row)
        self.assertIn("PancakeV2", row)

WEI = 10**18


class TestProfitGate(unittest.TestCase):
    def test_apply_bps(self):
        self.assertEqual(profit.apply_bps(10_000, 25), 25)
        self.assertEqual(profit.apply_bps(0, 25), 0)

    def test_flash_fee_matches_aave_v3(self):
        # 0.09 % of 1 BNB
        self.assertEqual(profit.flash_fee(WEI, 9), WEI * 9 // 10_000)

    def test_gas_cost(self):
        self.assertEqual(profit.gas_cost_wei(200_000, 5 * 10**9), 10**15)

    def test_net_profit_subtracts_fee_and_gas(self):
        amount_in = WEI
        amount_out = WEI + 3 * 10**15      # +0.003 BNB gross
        fee = profit.flash_fee(amount_in, 9)   # 0.0009 BNB
        gas = 10**15                            # 0.001 BNB
        net = profit.net_profit_wei(amount_in, amount_out, fee, gas)
        self.assertEqual(net, 3 * 10**15 - fee - gas)

    def test_gate_rejects_negative(self):
        self.assertFalse(profit.is_profitable(WEI, -1, 10))

    def test_gate_rejects_below_margin(self):
        # 5 bps net but 10 bps required
        self.assertFalse(profit.is_profitable(WEI, WEI * 5 // 10_000, 10))

    def test_gate_accepts_above_margin(self):
        self.assertTrue(profit.is_profitable(WEI, WEI * 15 // 10_000, 10))

    def test_gate_rejects_zero_size(self):
        self.assertFalse(profit.is_profitable(0, WEI, 10))

    def test_worst_case_out(self):
        self.assertEqual(profit.worst_case_out(1_000_000, 50), 995_000)

    def test_best_route(self):
        quotes = {("A", "B"): 100, ("A", "C"): 120, ("D", "B"): 90}
        self.assertEqual(profit.best_route(quotes), ("A", "C", 120))
        self.assertIsNone(profit.best_route({}))


if __name__ == "__main__":
    unittest.main()
