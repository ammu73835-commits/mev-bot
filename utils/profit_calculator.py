"""
Profit Calculator - Locks in profit before firing transactions
- Simulates transactions before execution
- Calculates exact profit/loss
- Never fires unless profit is guaranteed
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProfitCalculation:
    """Result of profit calculation"""
    expected_profit_usd: Decimal
    expected_profit_percentage: Decimal
    gas_cost_usd: Decimal
    net_profit_usd: Decimal
    slippage_impact_usd: Decimal
    is_profitable: bool
    confidence_score: float
    details: str


class ProfitCalculator:
    """Advanced profit calculator with simulation"""
    
    def __init__(self, min_profit_usd: Decimal = Decimal("3.0")):
        self.min_profit_usd = min_profit_usd
        
    def calculate_sandwich_profit(
        self,
        victim_amount_in: Decimal,
        pool_reserve_in: Decimal,
        pool_reserve_out: Decimal,
        front_run_amount: Decimal,
        token_price_usd: Decimal,
        gas_cost_usd: Decimal
    ) -> ProfitCalculation:
        """Calculate sandwich attack profit"""
        front_run_out = self._calculate_swap_output(
            front_run_amount, pool_reserve_in, pool_reserve_out
        )
        
        new_reserve_in = pool_reserve_in + front_run_amount
        new_reserve_out = pool_reserve_out - front_run_out
        
        victim_out_after_front = self._calculate_swap_output(
            victim_amount_in, new_reserve_in, new_reserve_out
        )
        
        new_reserve_in += victim_amount_in
        new_reserve_out -= victim_out_after_front
        
        back_run_amount = front_run_out * Decimal("0.997")
        back_run_in = self._calculate_swap_output(
            back_run_amount, new_reserve_out, new_reserve_in
        )
        
        gross_profit = back_run_in - front_run_amount
        gross_profit_usd = gross_profit * token_price_usd
        net_profit = gross_profit_usd - gas_cost_usd
        
        ideal_victim_out = self._calculate_swap_output(
            victim_amount_in, pool_reserve_in, pool_reserve_out
        )
        slippage_impact = (ideal_victim_out - victim_out_after_front) * token_price_usd
        
        confidence = self._calculate_confidence(gross_profit, gas_cost_usd, slippage_impact)
        
        return ProfitCalculation(
            expected_profit_usd=gross_profit_usd,
            expected_profit_percentage=(gross_profit / front_run_amount * 100),
            gas_cost_usd=gas_cost_usd,
            net_profit_usd=net_profit,
            slippage_impact_usd=slippage_impact,
            is_profitable=net_profit > self.min_profit_usd,
            confidence_score=confidence,
            details=f"Front-run: {front_run_out:.4f}, Back-run: {back_run_in:.4f}"
        )
        
    def _calculate_swap_output(
        self, amount_in: Decimal, reserve_in: Decimal, reserve_out: Decimal
    ) -> Decimal:
        """Calculate swap output using constant product formula (with 0.3% fee)"""
        amount_in_with_fee = amount_in * Decimal("0.997")
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        return numerator / denominator
        
    def _calculate_confidence(
        self, gross_profit: Decimal, gas_cost: Decimal, slippage: Decimal
    ) -> float:
        """Calculate confidence score (0-100)"""
        if gross_profit <= 0:
            return 0
        score = 50
        profit_margin = gross_profit / (gas_cost + Decimal("1"))
        if profit_margin > 5:
            score += 20
        elif profit_margin > 2:
            score += 10
        if slippage > gross_profit * Decimal("0.5"):
            score -= 20
        if gas_cost > gross_profit:
            score -= 30
        return min(100, max(0, score))
        
    def should_execute(self, calc: ProfitCalculation) -> bool:
        """Determine if opportunity should be executed"""
        return calc.is_profitable and calc.confidence_score >= 60 and calc.net_profit_usd >= self.min_profit_usd
        
    def calculate_solana_profit(
        self, profit_sol: Decimal, priority_fee_sol: Decimal, sol_price_usd: Decimal = Decimal("150")
    ) -> ProfitCalculation:
        """Calculate Solana-specific profit"""
        net_profit_sol = profit_sol - priority_fee_sol
        net_profit_usd = net_profit_sol * sol_price_usd
        return ProfitCalculation(
            expected_profit_usd=profit_sol * sol_price_usd,
            expected_profit_percentage=Decimal("0"),
            gas_cost_usd=priority_fee_sol * sol_price_usd,
            net_profit_usd=net_profit_usd,
            slippage_impact_usd=Decimal("0"),
            is_profitable=net_profit_usd >= self.min_profit_usd,
            confidence_score=80.0,
            details=f"Solana: {profit_sol:.6f} SOL profit, {priority_fee_sol:.6f} SOL fee"
        )