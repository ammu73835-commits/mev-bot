"""Executor arg encoding - the tuple that the on-chain contract must decode."""
import unittest

from eth_abi import decode as abi_decode
from web3 import Web3

from mev_engine.config import BSC
from mev_engine.executor import ARB_ABI, ZERO_ADDRESS, Executor
from mev_engine.scanner import Opportunity

WEI = 10**18
WRAPPED = Web3.to_checksum_address(BSC.wrapped)
TOKEN = Web3.to_checksum_address(BSC.tokens["USDT"])
PAIR = Web3.to_checksum_address("0x83C5b5b309EE8E232Fe9dB217d394e262a71bCC0")


class FakeChain:
    """Only the bits Executor touches - no RPC needed."""

    def __init__(self, network):
        self.network = network
        self.venues = {v.name: v for v in network.venues}
        self.w3 = None

    def pair_address(self, factory, token_a, token_b):
        return PAIR


def _encode_arb(contract, args) -> str:
    """web3>=7 uses encode_abi(), web3 6.x uses encodeABI() - support both."""
    if hasattr(contract, "encode_abi"):
        return contract.encode_abi("arb", args=list(args))
    return contract.encodeABI("arb", args=list(args))


def make_opp(**overrides) -> Opportunity:
    base = dict(
        network="BSC",
        token_symbol="USDT",
        token_address=TOKEN,
        buy_router="PancakeV2",
        sell_router="PancakeV3-100",
        amount_in_wei=WEI,
        token_amount_wei=2 * WEI,
        amount_out_wei=WEI + WEI // 100,
        fee_wei=0,
        gas_wei=0,
        net_wei=WEI // 100,
        net_bps=100,
        gas_price_wei=5 * 10**9,
        profitable=True,
    )
    base.update(overrides)
    return Opportunity(**base)


class TestExecutorArgs(unittest.TestCase):
    def setUp(self):
        self.network = BSC
        self.executor = Executor(FakeChain(BSC), BSC)

    def test_v2_leg_is_kind_zero(self):
        leg = self.executor.leg("PancakeV2", WRAPPED, TOKEN)
        self.assertEqual(leg[0], 0)
        self.assertEqual(leg[1], Web3.to_checksum_address(self.executor.chain.venues["PancakeV2"].target))
        self.assertEqual((leg[2], leg[3]), (WRAPPED, TOKEN))
        self.assertEqual(leg[4], 0)

    def test_v3_leg_is_kind_one_with_fee_tier(self):
        leg = self.executor.leg("PancakeV3-100", TOKEN, WRAPPED)
        self.assertEqual(leg[0], 1)
        self.assertEqual(leg[4], 100)

    def test_build_args_layout(self):
        opp = make_opp()
        args = self.executor.build_args(opp)
        self.assertIsNotNone(args)
        self.assertEqual(len(args), 7)
        flash_pair, token_in, amount_in, min_profit, fee_bps, buy, sell = args
        self.assertEqual(flash_pair, PAIR)
        self.assertEqual(token_in, WRAPPED)
        self.assertEqual(amount_in, opp.amount_in_wei)
        self.assertEqual(fee_bps, BSC.flash_fee_bps)
        # buy: native -> token, sell: token -> native
        self.assertEqual((buy[2], buy[3]), (WRAPPED, TOKEN))
        self.assertEqual((sell[2], sell[3]), (TOKEN, WRAPPED))
        self.assertEqual(min_profit, max(int(opp.net_wei * 0.5), 1))

    def test_build_args_are_checksummed(self):
        args = self.executor.build_args(make_opp())
        flattened = [args[0], args[1], args[5][1], args[5][2], args[5][3], args[6][1]]
        for addr in flattened:
            self.assertTrue(Web3.is_checksum_address(addr), addr)

    def test_missing_flash_pair_returns_none(self):
        executor = Executor(FakeChain(BSC), BSC)
        executor.chain.pair_address = lambda *a, **k: None
        self.assertIsNone(executor.build_args(make_opp()))

    def test_args_encode_against_the_contract_abi(self):
        """The real proof: what web3 encodes is exactly what Solidity abi.decode reads."""
        args = self.executor.build_args(make_opp())
        contract = Web3().eth.contract(address=ZERO_ADDRESS, abi=ARB_ABI)
        encoded = _encode_arb(contract, args)
        self.assertTrue(encoded.startswith("0x"))

        leg = "(uint8,address,address,address,uint24)"
        types = ["address", "address", "uint256", "uint256", "uint16", leg, leg]
        body = bytes.fromhex(encoded[10:])  # strip 0x + 4-byte selector
        decoded = abi_decode(types, body)

        self.assertEqual(decoded[0].lower(), str(args[0]).lower())
        self.assertEqual(decoded[1].lower(), str(args[1]).lower())
        self.assertEqual(decoded[2], args[2])
        self.assertEqual(decoded[3], args[3])
        self.assertEqual(decoded[4], args[4])
        for i in (5, 6):
            self.assertEqual(decoded[i][0], args[i][0])          # kind
            self.assertEqual(decoded[i][1].lower(), args[i][1].lower())  # target
            self.assertEqual(decoded[i][2].lower(), args[i][2].lower())  # tokenIn
            self.assertEqual(decoded[i][3].lower(), args[i][3].lower())  # tokenOut
            self.assertEqual(decoded[i][4], args[i][4])          # fee


    def test_abi_inputs_match_the_contract(self):
        fn = next(item for item in ARB_ABI if item.get("name") == "arb")
        types = [i["type"] for i in fn["inputs"]]
        self.assertEqual(
            types, ["address", "address", "uint256", "uint256", "uint16", "tuple", "tuple"]
        )


if __name__ == "__main__":
    unittest.main()
