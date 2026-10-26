"""Config sanity - catches a bad address before it burns scan cycles."""
import unittest

from mev_engine.config import NETWORKS, TRADE_SIZES, get_network
from mev_engine.dex import MULTICALL3_ADDRESS

ADDRESSES_OK = ("0x", 42)


class TestVenues(unittest.TestCase):
    def each_venue(self):
        for network in NETWORKS.values():
            for venue in network.venues:
                yield network, venue

    def test_every_network_is_usable(self):
        for name, network in NETWORKS.items():
            self.assertGreaterEqual(len(network.venues), 2, name)
            self.assertGreaterEqual(len(network.rpcs), 2, name)
            self.assertTrue(network.tokens, name)
            self.assertGreater(network.gas_units, 0, name)
            self.assertGreater(network.flash_fee_bps, 0, name)
            self.assertEqual(network.wrapped[:2], "0x", name)

    def test_venue_names_are_unique(self):
        for network in NETWORKS.values():
            names = [v.name for v in network.venues]
            self.assertEqual(len(names), len(set(names)), network.name)

    def test_venue_addresses_are_well_formed(self):
        for network, venue in self.each_venue():
            for addr in (venue.target, venue.factory, venue.quoter):
                if addr:
                    self.assertEqual(len(addr), ADDRESSES_OK[1], f"{network.name}/{venue.name}")
                    self.assertTrue(addr.startswith(ADDRESSES_OK[0]))
                    self.assertNotEqual(int(addr, 16), 0, f"{network.name}/{venue.name}")

    def test_v2_venues_have_factory(self):
        for network, venue in self.each_venue():
            if venue.kind == "v2":
                self.assertTrue(venue.factory, f"{network.name}/{venue.name}")

    def test_v3_venues_have_quoter_and_fee(self):
        for network, venue in self.each_venue():
            if venue.kind == "v3":
                self.assertTrue(venue.quoter, f"{network.name}/{venue.name}")
                self.assertIn(venue.fee, (100, 500, 2500, 3000, 10000), venue.name)

    def test_kind_is_known(self):
        for network, venue in self.each_venue():
            self.assertIn(venue.kind, ("v2", "v3"), f"{network.name}/{venue.name}")

    def test_at_least_two_scannable_venues(self):
        for network in NETWORKS.values():
            self.assertGreaterEqual(len([v for v in network.venues if v.scan]), 2, network.name)

    def test_exactly_one_flash_source(self):
        for network in NETWORKS.values():
            flashable = [v for v in network.venues if v.flashable]
            self.assertEqual(len(flashable), 1, network.name)
            self.assertEqual(flashable[0].kind, "v2")

    def test_lookup_is_case_insensitive(self):
        self.assertIs(get_network("bsc"), NETWORKS["BSC"])
        self.assertIs(get_network(" polygon "), NETWORKS["Polygon"])

    def test_unknown_network_raises(self):
        with self.assertRaises(KeyError):
            get_network("dogechain")

    def test_trade_sizes_are_positive(self):
        self.assertTrue(TRADE_SIZES)
        for size in TRADE_SIZES:
            self.assertGreater(size, 0)

    def test_multicall3_is_deployed_address(self):
        self.assertEqual(MULTICALL3_ADDRESS.lower(), "0xca11bde05977b3631167028862be2a173976ca11")


if __name__ == "__main__":
    unittest.main()
