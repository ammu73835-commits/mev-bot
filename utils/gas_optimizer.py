"""
Advanced Gas Optimizer for EVM Networks
- Dynamic gas pricing
- Priority fee calculation
- Gas limit optimization
- Never waste gas - only fire when profit is locked
"""

import asyncio
import aiohttp
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GasOptimizationResult:
    """Result of gas optimization calculation"""
    gas_price_gwei: int
    priority_fee_gwei: int
    gas_limit: int
    estimated_cost_usd: Decimal
    recommended: bool
    reason: str


class GasOptimizer:
    """
    Advanced gas optimization engine for EVM networks
    Ensures minimal gas waste while beating other bots
    """
    
    def __init__(self, chain_id: int, ws_url: str, http_url: str):
        self.chain_id = chain_id
        self.ws_url = ws_url
        self.http_url = http_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_base_fee: int = 0
        self.last_priority_fee: int = 0
        
    async def start(self):
        """Initialize the gas optimizer"""
        self.session = aiohttp.ClientSession()
        logger.info(f"Gas Optimizer started for chain {self.chain_id}")
        
    async def stop(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            
    async def get_current_gas_price(self) -> tuple[int, int, int]:
        """
        Get current base fee and priority fee
        Returns: (base_fee, priority_fee, max_fee) in gwei
        """
        try:
            async with self.session.get(f"{self.http_url}") as response:
                data = await response.json()
                
            block = data.get('result', {})
            base_fee = int(block.get('baseFeePerGas', '0x0'), 16)
            
            priority_fee = await self._get_priority_fee()
            max_fee = base_fee + (priority_fee * 2)
            
            self.last_base_fee = base_fee
            self.last_priority_fee = priority_fee
            
            return (base_fee // 10**9, priority_fee // 10**9, max_fee // 10**9)
        except Exception as e:
            logger.error(f"Error fetching gas price: {e}")
            return (30, 1.5, 63)
            
    async def _get_priority_fee(self) -> int:
        """Get recommended priority fee from network"""
        try:
            async with self.session.post(
                self.http_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_maxPriorityFeePerGas",
                    "params": [],
                    "id": 1
                }
            ) as response:
                data = await response.json()
                return int(data.get('result', '0x3b9aca00'), 16)
        except:
            return 1_000_000_000
            
    async def optimize_gas_for_tx(
        self,
        tx_data: Dict[str, Any],
        beat_other_bots: bool = True
    ) -> GasOptimizationResult:
        """Optimize gas settings for a specific transaction"""
        base_fee_gwei, priority_fee_gwei, max_fee_gwei = await self.get_current_gas_price()
        
        if beat_other_bots:
            priority_fee_gwei = int(Decimal(priority_fee_gwei) * Decimal("1.25"))
            
        gas_limit = await self._estimate_gas_limit(tx_data)
        native_token_price = await self._get_native_token_price()
        
        estimated_cost_usd = (
            Decimal(max_fee_gwei) * Decimal(gas_limit) * Decimal(10**9) * native_token_price / Decimal(10**18)
        )
        
        recommended = estimated_cost_usd < Decimal("5.0")
        reason = "Gas optimized to beat competition" if beat_other_bots else "Gas optimized"
            
        return GasOptimizationResult(
            gas_price_gwei=max_fee_gwei,
            priority_fee_gwei=priority_fee_gwei,
            gas_limit=gas_limit,
            estimated_cost_usd=estimated_cost_usd,
            recommended=recommended,
            reason=reason
        )
        
    async def _estimate_gas_limit(self, tx_data: Dict[str, Any]) -> int:
        """Estimate optimal gas limit for transaction"""
        try:
            async with self.session.post(
                self.http_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_estimateGas",
                    "params": [{"to": tx_data.get("to"), "data": tx_data.get("data", "0x")}],
                    "id": 1
                }
            ) as response:
                data = await response.json()
                estimated = int(data.get('result', '0x0'), 16)
                return int(Decimal(estimated) * Decimal("1.2"))
        except:
            return 300_000
            
    async def _get_native_token_price(self) -> Decimal:
        """Get current native token price in USD"""
        try:
            async with self.session.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "ethereum,matic-network", "vs_currencies": "usd"}
            ) as response:
                data = await response.json()
                if self.chain_id == 137:
                    return Decimal(str(data.get('matic-network', {}).get('usd', 1.0)))
                return Decimal(str(data.get('ethereum', {}).get('usd', 2000)))
        except:
            return Decimal("2000")
            
    def should_fire_tx(self, expected_profit_usd: Decimal, gas_opt: GasOptimizationResult) -> bool:
        """Determine if transaction should be fired based on profit vs gas cost"""
        return gas_opt.recommended and expected_profit_usd >= (gas_opt.estimated_cost_usd * Decimal("1.5"))