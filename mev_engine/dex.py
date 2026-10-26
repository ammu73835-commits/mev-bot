"""Minimal Uniswap-V2 / V3 bindings with RPC rotation and Multicall3 batching."""
from typing import Dict, List, Optional

from eth_abi import decode as abi_decode
from web3 import Web3

from .config import Network, Venue

ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

QUOTER_V2_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "internalType": "struct IQuoterV2.QuoteExactInputSingleParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
        ],
        "name": "getPair",
        "outputs": [{"internalType": "address", "name": "pair", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]

PAIR_ABI = [
    {"inputs": [], "name": "token0", "outputs": [{"internalType": "address", "name": ""}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"internalType": "address", "name": ""}], "stateMutability": "view", "type": "function"},
    {
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "blockTimestampLast", "type": "uint32"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

MULTICALL3_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "target", "type": "address"},
                    {"internalType": "bool", "name": "allowFailure", "type": "bool"},
                    {"internalType": "bytes", "name": "callData", "type": "bytes"},
                ],
                "internalType": "struct Multicall3.Call3[]",
                "name": "calls",
                "type": "tuple[]",
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [
                    {"internalType": "bool", "name": "success", "type": "bool"},
                    {"internalType": "bytes", "name": "returnData", "type": "bytes"},
                ],
                "internalType": "struct Multicall3.Result[]",
                "name": "returnData",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "payable",
        "type": "function",
    }
]

# Multicall3 lives at the same address on BSC, Polygon, Arbitrum, Base, ...
MULTICALL3_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"


class Chain:
    """A live connection to one network with RPC rotation."""

    def __init__(self, network: Network, timeout: int = 12):
        self.network = network
        self.timeout = timeout
        self._index = 0
        self.w3: Optional[Web3] = None
        self.venues: Dict[str, Venue] = {v.name: v for v in network.venues}
        self._quotes = 0
        self._errors = 0

    # ------------------------------------------------------------------ connect
    def connect(self) -> Web3:
        for offset in range(len(self.network.rpcs)):
            idx = (self._index + offset) % len(self.network.rpcs)
            rpc = self.network.rpcs[idx]
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": self.timeout}))
                if w3.is_connected():
                    self.w3 = w3
                    self._index = idx
                    return w3
            except Exception:
                continue
        raise ConnectionError(f"{self.network.name}: no RPC answered")

    def rotate(self) -> Web3:
        self._index = (self._index + 1) % len(self.network.rpcs)
        return self.connect()

    def dead_venues(self) -> List[str]:
        """Venues whose target has no bytecode (typo'd address / wrong network)."""
        dead: List[str] = []
        checked: Dict[str, bool] = {}
        for name, venue in self.venues.items():
            try:
                addr = Web3.to_checksum_address(self.target(venue))
                if addr not in checked:
                    checked[addr] = bool(self.w3.eth.get_code(addr))
                if not checked[addr]:
                    dead.append(name)
            except Exception:
                continue
        return dead


    # -------------------------------------------------------------------- reads
    def gas_price_wei(self) -> int:
        try:
            return int(self.w3.eth.gas_price)
        except Exception:
            return 0

    @staticmethod
    def target(venue: Venue) -> str:
        return venue.quoter if venue.kind == "v3" else venue.target

    def _calldata(self, venue_name: str, token_in: str, token_out: str, amount_in: int) -> bytes:
        venue = self.venues[venue_name]
        token_in = Web3.to_checksum_address(token_in)
        token_out = Web3.to_checksum_address(token_out)
        if venue.kind == "v3":
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(venue.quoter), abi=QUOTER_V2_ABI
            )
            fn = contract.functions.quoteExactInputSingle(
                (token_in, token_out, amount_in, venue.fee, 0)
            )
        else:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(venue.target), abi=ROUTER_ABI
            )
            fn = contract.functions.getAmountsOut(amount_in, [token_in, token_out])
        data = fn._encode_transaction_data()
        return bytes.fromhex(data[2:]) if isinstance(data, str) else data

    @staticmethod
    def _decode(venue: Venue, raw: bytes) -> Optional[int]:
        if not raw:
            return None
        if venue.kind == "v3":
            out = abi_decode(["uint256", "uint160", "uint32", "uint256"], raw)[0]
        else:
            amounts = abi_decode(["uint256[]"], raw)[0]
            out = amounts[-1] if amounts else 0
        return int(out) if out and int(out) > 0 else None

    def quote(self, venue_name: str, token_in: str, token_out: str, amount_in: int) -> Optional[int]:
        """Single-venue quote (fallback path / manual checks)."""
        venue = self.venues[venue_name]
        try:
            raw = self.w3.eth.call(
                {
                    "to": Web3.to_checksum_address(self.target(venue)),
                    "data": self._calldata(venue_name, token_in, token_out, amount_in),
                }
            )
            out = self._decode(venue, raw)
            self._quotes += 1
            return out
        except Exception:
            self._errors += 1
            return None

    def quote_many(self, requests) -> Dict[str, Optional[int]]:
        """Quote many routes in ONE eth_call (V2 and V3 mixed).

        requests: (key, venue_name, token_in, token_out, amount_in)
        returns:  {key: amount_out_wei or None}

        Multicall3 collapses a whole sweep into a single round-trip, which is what
        keeps the scanner fast enough to compete with colocated bots.
        Falls back to individual calls if the multicall itself fails.
        """
        requests = list(requests)
        if not requests:
            return {}
        result: Dict[str, Optional[int]] = {}
        try:
            calls = []
            keys = []
            for key, venue_name, token_in, token_out, amount_in in requests:
                venue = self.venues[venue_name]
                calls.append(
                    (
                        Web3.to_checksum_address(self.target(venue)),
                        True,
                        self._calldata(venue_name, token_in, token_out, amount_in),
                    )
                )
                keys.append(key)
            multicall = self.w3.eth.contract(
                address=Web3.to_checksum_address(MULTICALL3_ADDRESS), abi=MULTICALL3_ABI
            )
            raw_results = multicall.functions.aggregate3(calls).call()
            for key, item in zip(keys, raw_results):
                venue_name = key[2] if isinstance(key, tuple) and len(key) > 2 else key
                venue = self.venues.get(venue_name) or next(iter(self.venues.values()))
                success, return_data = item[0], item[1]
                if not success or not return_data:
                    result[key] = None
                    self._errors += 1
                    continue
                try:
                    result[key] = self._decode(venue, return_data)
                    self._quotes += 1
                except Exception:
                    result[key] = None
                    self._errors += 1
            return result
        except Exception:
            for key, venue_name, token_in, token_out, amount_in in requests:
                result[key] = self.quote(venue_name, token_in, token_out, amount_in)
            return result

    def pair_address(self, factory: str, token_a: str, token_b: str) -> Optional[str]:
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(factory), abi=FACTORY_ABI
            )
            pair = contract.functions.getPair(
                Web3.to_checksum_address(token_a), Web3.to_checksum_address(token_b)
            ).call()
            return None if int(pair, 16) == 0 else pair
        except Exception:
            return None

    def pair_tokens(self, pair: str):
        contract = self.w3.eth.contract(address=Web3.to_checksum_address(pair), abi=PAIR_ABI)
        return contract.functions.token0().call(), contract.functions.token1().call()

    @property
    def stats(self):
        return {"quotes": self._quotes, "errors": self._errors}

    @property
    def scan_venues(self) -> List[str]:
        """Venue names worth quoting (flash-only / dust pools are excluded)."""
        return [name for name, venue in self.venues.items() if venue.scan]



