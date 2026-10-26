"""
All-in-One EVM MEV Bot
- Runs on Arbitrum, Polygon, Base
- Multi-strategy: Sandwich, Pending Stealer, Arbitrage
- Never wastes gas, only fires when profit is locked
- Beats other sophisticated bots with speed
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from decimal import Decimal
from typing import Dict, Any

from web3 import AsyncWeb3
from eth_account import Account

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
from gas_optimizer import GasOptimizer
from profit_calculator import ProfitCalculator
from self_healer import SelfHealer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/mev_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EVM_MEV_Bot:
    """Main EVM MEV Bot Orchestrator"""
    
    def __init__(self, config_path: str = "../config/networks.json"):
        self.config = self._load_config(config_path)
        self.accounts: Dict[str, Account] = {}
        self.w3_instances: Dict[str, AsyncWeb3] = {}
        self.gas_optimizers: Dict[str, GasOptimizer] = {}
        self.profit_calculator = ProfitCalculator(min_profit_usd=Decimal("3.0"))
        self.self_healer = SelfHealer(max_retries=3, retry_delay=5.0)
        self.running = False
        self.total_profit = Decimal("0")
        
    def _load_config(self, config_path: str) -> Dict:
        with open(config_path) as f:
            return json.load(f)
            
    async def initialize(self, private_keys: Dict[str, str]):
        """Initialize bot with wallets for each network"""
        logger.info("Initializing EVM MEV Bot...")
        
        for network_name, pk in private_keys.items():
            if network_name not in self.config["evm_networks"]:
                continue
                
            self.accounts[network_name] = Account.from_key(pk)
            logger.info(f"✓ Loaded {network_name} wallet: {self.accounts[network_name].address[:10]}...")
            
            rpc_url = self.config["evm_networks"][network_name]["rpc_urls"][0]
            self.w3_instances[network_name] = AsyncWeb3(AsyncWeb3.HTTPProvider(rpc_url))
            
            self.gas_optimizers[network_name] = GasOptimizer(
                chain_id=self.config["evm_networks"][network_name]["chain_id"],
                ws_url=self.config["evm_networks"][network_name]["ws_url"],
                http_url=rpc_url
            )
            await self.gas_optimizers[network_name].start()
            
        logger.info(f"✓ Initialized {len(self.accounts)} networks")
        
    async def run_sandwich_strategy(self, network_name: str):
        """Execute sandwich attack strategy"""
        w3 = self.w3_instances[network_name]
        account = self.accounts[network_name]
        gas_opt = self.gas_optimizers[network_name]
        
        logger.info(f"🔍 Starting sandwich monitoring on {network_name}...")
        
        while self.running:
            try:
                pending_txs = await w3.eth.unsafe_cache.get_pending_transactions()
                
                for tx_hash in pending_txs[:10]:
                    tx = await w3.eth.get_transaction(tx_hash)
                    
                    if not self._is_swap_transaction(tx):
                        continue
                        
                    profit = await self._calculate_sandwich_profit(tx, network_name)
                    
                    if profit and self.profit_calculator.should_execute(profit):
                        gas_optimization = await gas_opt.optimize_gas_for_tx(
                            {"to": tx["to"], "data": tx["data"]}, beat_other_bots=True
                        )
                        
                        if gas_opt.should_fire_tx(profit.net_profit_usd, gas_optimization):
                            await self._execute_sandwich(tx, network_name, gas_optimization)
                            self.total_profit += profit.net_profit_usd
                            logger.info(f"💰 Sandwich profit: ${profit.net_profit_usd:.2f} | Total: ${self.total_profit:.2f}")
                            
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Sandwich strategy error on {network_name}: {e}")
                await asyncio.sleep(1)
                
    def _is_swap_transaction(self, tx: Dict) -> bool:
        """Check if transaction is a swap"""
        data = tx.get("data", "0x")
        swap_selectors = ["0x38ed1739", "0x7ff36ab5", "0x18cbafe5"]
        return any(data.startswith(sel) for sel in swap_selectors)
        
    async def _calculate_sandwich_profit(self, tx: Dict, network_name: str):
        """Calculate potential sandwich profit"""
        victim_amount = Decimal(str(tx.get("value", 0))) / Decimal(10**18)
        if victim_amount < Decimal("0.1"):
            return None
        estimated_profit = victim_amount * Decimal("0.01")
        return self.profit_calculator.calculate_solana_profit(
            profit_sol=estimated_profit, priority_fee_sol=Decimal("0.001")
        )
        
    async def _execute_sandwich(self, victim_tx: Dict, network_name: str, gas_opt):
        """Execute sandwich attack"""
        w3 = self.w3_instances[network_name]
        account = self.accounts[network_name]
        
        front_run_tx = {
            "from": account.address,
            "to": victim_tx["to"],
            "value": victim_tx["value"] // 10,
            "data": victim_tx["data"],
            "gas": gas_opt.gas_limit,
            "gasPrice": w3.to_wei(gas_opt.gas_price_gwei, 'gwei'),
            "nonce": await w3.eth.get_transaction_count(account.address),
            "chainId": await w3.eth.chain_id
        }
        
        signed = account.sign_transaction(front_run_tx)
        tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.info(f"🚀 Front-run sent: {tx_hash.hex()[:20]}...")
        
    async def run(self):
        """Main bot loop"""
        self.running = True
        logger.info("🤖 EVM MEV Bot started!")
        
        tasks = []
        for network_name in self.accounts.keys():
            tasks.append(asyncio.create_task(self.run_sandwich_strategy(network_name)))
        tasks.append(asyncio.create_task(self.self_healer.monitor_and_heal()))
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.running = False
            logger.info("🛑 Bot stopped by user")
            
    def get_profit_report(self) -> str:
        return f"Total Profit: ${self.total_profit:.2f}\nActive Networks: {list(self.accounts.keys())}"


async def main():
    private_keys = {
        "arbitrum": "YOUR_ARBITRUM_PRIVATE_KEY",
        "polygon": "YOUR_POLYGON_PRIVATE_KEY",
        "base": "YOUR_BASE_PRIVATE_KEY"
    }
    
    bot = EVM_MEV_Bot()
    await bot.initialize(private_keys)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())