"""Networks, DEX venues (V2 + V3), tokens and the hard safety limits."""
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ---------------------------------------------------------------- safety locks
# Only fire when net profit (after gas + flash fee + slippage) is at least
# MIN_NET_PROFIT_BPS of the trade size. 10 bps = 0.10 %.
MIN_NET_PROFIT_BPS = int(os.getenv("MIN_NET_PROFIT_BPS", "10"))
# Extra gas head-room on the estimate (protects against gas spikes).
GAS_LIMIT_MULTIPLIER = float(os.getenv("GAS_LIMIT_MULTIPLIER", "1.25"))
# Priority tip added on top of the node gas price (basis points).
PRIORITY_TIP_BPS = int(os.getenv("PRIORITY_TIP_BPS", "1500"))  # +15 %
# Hard cap on gas price we are willing to pay (gwei). 0 = no cap.
MAX_GAS_PRICE_GWEI = float(os.getenv("MAX_GAS_PRICE_GWEI", "0"))
# Dry run: compute + simulate only, never broadcast (default ON).
#   DRY_RUN=1 / DRY_RUN=0 wins over LIVE; otherwise LIVE=1 flips it off.
_dry_env = os.getenv("DRY_RUN")
if _dry_env is None:
    DRY_RUN = os.getenv("LIVE", "0").strip().lower() not in ("1", "true", "yes", "on")
else:
    DRY_RUN = _dry_env.strip().lower() not in ("0", "false", "no", "off")


@dataclass(frozen=True)
class Venue:
    """One tradable execution venue.

    kind="v2": constant-product router, quoted with getAmountsOut.
    kind="v3": concentrated liquidity, quoted with QuoterV2. The fee tier is the
               whole point: 100 = 0.01 % (2 bps round-trip) vs 2 x 0.25 % on V2.
    """

    name: str
    kind: str
    target: str           # router actually called to swap (v2 router / v3 swap router)
    factory: str = ""
    quoter: str = ""      # v3 only
    fee: int = 0          # v3 fee tier
    flashable: bool = False  # can we borrow the flash loan from this V2 pair?


@dataclass(frozen=True)
class Network:
    name: str
    chain_id: int
    rpcs: List[str]
    wrapped: str
    venues: Tuple[Venue, ...]
    tokens: Dict[str, str]
    gas_units: int         # expected gas for a flash-swap arbitrage
    flash_fee_bps: int     # fee of the V2 pool we borrow from (Pancake = 25)
    explorer: str

    def venue(self, name: str) -> Venue:
        for item in self.venues:
            if item.name == name:
                return item
        raise KeyError(name)

    def flash_venue(self) -> Venue:
        for item in self.venues:
            if item.flashable:
                return item
        raise KeyError("no flashable venue configured")


PANCAKE_V3_ROUTER = "0x1b81D678ffb9C0263b24A97847620C99d213eB14"
PANCAKE_V3_QUOTER = "0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997"
PANCAKE_V3_FACTORY = "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865"
UNI_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
UNI_V3_QUOTER = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"

BSC = Network(
    name="BSC",
    chain_id=56,
    rpcs=[
        "https://bsc-dataseed.binance.org/",
        "https://bsc-rpc.publicnode.com",
        "https://binance.llamarpc.com",
    ],
    wrapped="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
    venues=(
        Venue("PancakeV2", "v2", "0x10ED43C718714eb63d5aA57B78B54704E256024E",
              factory="0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73", flashable=True),
        Venue("BiswapV2", "v2", "0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8",
              factory="0x858E3312ed3A876947EA49d572A7C42DE08af7EE"),
        Venue("SushiBSC", "v2", "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
              factory="0xc35DADB65012eC5796536bD9864eD8773aBc74C4"),
        Venue("BakeryV2", "v2", "0xCDe540d7eAFE93aC5fE6233Bee57E1270D3E330F",
              factory="0x01bF7C66c6BD861915CdaaE475042d3c4BaE16A7"),
        Venue("PancakeV3-100", "v3", PANCAKE_V3_ROUTER,
              factory=PANCAKE_V3_FACTORY, quoter=PANCAKE_V3_QUOTER, fee=100),
        Venue("PancakeV3-500", "v3", PANCAKE_V3_ROUTER,
              factory=PANCAKE_V3_FACTORY, quoter=PANCAKE_V3_QUOTER, fee=500),
        Venue("PancakeV3-2500", "v3", PANCAKE_V3_ROUTER,
              factory=PANCAKE_V3_FACTORY, quoter=PANCAKE_V3_QUOTER, fee=2500),
    ),
    tokens={
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
        "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
        "ETH": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
        "BTCB": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
        "BSW": "0x965F527D9159dCe6288a2219DB51fc6Eef120dD1",
        "XVS": "0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63",
        "TWT": "0x4B0F1812e5Df2A09796481Ff14017e6005508003",
        "ALPACA": "0x8F0528cE5eF7B51152A59745bEfDD91D97091d2F",
    },
    gas_units=280_000,
    flash_fee_bps=25,
    explorer="https://bscscan.com",
)

POLYGON = Network(
    name="Polygon",
    chain_id=137,
    rpcs=[
        "https://polygon-bor-rpc.publicnode.com",
        "https://polygon.llamarpc.com",
        "https://1rpc.io/matic",
    ],
    wrapped="0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
    venues=(
        Venue("QuickSwapV2", "v2", "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
              factory="0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32", flashable=True),
        Venue("SushiV2", "v2", "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
              factory="0xc35DADB65012eC5796536bD9864eD8773aBc74C4"),
        Venue("UniV3-500", "v3", UNI_V3_ROUTER, quoter=UNI_V3_QUOTER, fee=500),
        Venue("UniV3-3000", "v3", UNI_V3_ROUTER, quoter=UNI_V3_QUOTER, fee=3000),
    ),
    tokens={
        "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
        "WBTC": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",
    },
    gas_units=280_000,
    flash_fee_bps=25,
    explorer="https://polygonscan.com",
)

NETWORKS = {"BSC": BSC, "Polygon": POLYGON}


def get_network(name: str) -> Network:
    """Case-insensitive network lookup."""
    wanted = (name or "").strip().lower()
    for key, network in NETWORKS.items():
        if key.lower() == wanted:
            return network
    raise KeyError(f"unknown network '{name}'; choose from {list(NETWORKS)}")


# Trade sizes scanned, in whole wrapped-native units (BNB / MATIC).
TRADE_SIZES = [float(x) for x in os.getenv("TRADE_SIZES", "0.5,1,2").split(",")]
# Multicall chunk size (calls per eth_call).
SCAN_WORKERS = int(os.getenv("SCAN_WORKERS", "10"))


