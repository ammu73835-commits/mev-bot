"""Decoding tests for the V2/V3 quote paths (no RPC needed)."""
import unittest

from eth_abi import encode as abi_encode
from web3 import Web3

from mev_engine.config import BSC
from mev_engine.dex import Chain


class TestVenueOfKey(unittest.TestCase):
    def test_buy_key_returns_the_venue(self):
        self.assertEqual(Chain.venue_of_key(("CAKE", 1.0, "PancakeV3-100")), "PancakeV3-100")

    def test_sell_key_returns_the_sell_venue(self):
        key = ("CAKE", 1.0, "PancakeV3-100", "PancakeV2")
        self.assertEqual(Chain.venue_of_key(key), "PancakeV2")

    def test_plain_string_key_passes_through(self):
        self.assertEqual(Chain.venue_of_key("PancakeV2"), "PancakeV2")

    def test_every_scanner_key_shape_maps_to_a_configured_venue(self):
        venues = {v.name for v in BSC.venues}
        self.assertIn(Chain.venue_of_key(("USDT", 2.0, "BiswapV2")), venues)
        self.assertIn(Chain.venue_of_key(("USDT", 2.0, "BiswapV2", "PancakeV3-500")), venues)


class TestDecode(unittest.TestCase):
    def setUp(self):
        self.chain = Chain(BSC)

    def test_v2_amounts_out_takes_the_last_hop(self):
        venue = self.chain.venues["PancakeV2"]
        raw = abi_encode(["uint256[]"], [[10**18, 3 * 10**18]])
        self.assertEqual(self.chain._decode(venue, raw), 3 * 10**18)

    def test_v3_quote_takes_amount_out(self):
        venue = self.chain.venues["PancakeV3-100"]
        raw = abi_encode(["uint256", "uint160", "uint32", "uint256"], [7 * 10**18, 0, 0, 12345])
        self.assertEqual(self.chain._decode(venue, raw), 7 * 10**18)

    def test_zero_output_is_none(self):
        venue = self.chain.venues["PancakeV2"]
        raw = abi_encode(["uint256[]"], [[10**18, 0]])
        self.assertIsNone(self.chain._decode(venue, raw))

    def test_empty_payload_is_none(self):
        venue = self.chain.venues["PancakeV2"]
        self.assertIsNone(self.chain._decode(venue, b""))

    def test_target_is_quoter_for_v3_and_router_for_v2(self):
        v3 = self.chain.venues["PancakeV3-100"]
        v2 = self.chain.venues["PancakeV2"]
        self.assertEqual(Chain.target(v3), Web3.to_checksum_address(v3.quoter))
        self.assertEqual(Chain.target(v2), Web3.to_checksum_address(v2.target))


if __name__ == "__main__":
    unittest.main()
