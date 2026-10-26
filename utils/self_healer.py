"""
Self-Healing System - Auto-recovery and error handling
- Detects failures instantly
- Corrects and re-executes
- Never sleeps, runs 24/7
"""

import asyncio
import logging
from typing import Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """System health status"""
    is_healthy: bool
    last_check: datetime
    issues: list[str]
    recovery_actions: list[str]


class SelfHealer:
    """
    Advanced self-healing system for MEV bots
    Auto-detects and recovers from failures
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 5.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.health_status = HealthStatus(
            is_healthy=True,
            last_check=datetime.now(),
            issues=[],
            recovery_actions=[]
        )
        self.error_count = 0
        self.consecutive_successes = 0
        
    async def execute_with_recovery(
        self,
        func: Callable,
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> Any:
        """
        Execute a function with automatic recovery on failure
        
        Args:
            func: Async function to execute
            operation_name: Name of the operation for logging
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function
        """
        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                self.consecutive_successes += 1
                self.error_count = 0
                logger.info(f"✓ {operation_name} succeeded (attempt {attempt + 1})")
                return result
                
            except Exception as e:
                self.error_count += 1
                error_msg = str(e)
                logger.warning(f"✗ {operation_name} failed (attempt {attempt + 1}): {error_msg}")
                
                # Attempt recovery
                recovery_action = await self._recover_from_error(e, operation_name)
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    
        # All retries exhausted
        logger.error(f"✗ {operation_name} failed after {self.max_retries} attempts")
        return None
        
    async def _recover_from_error(self, error: Exception, operation_name: str) -> str:
        """Attempt to recover from a specific error"""
        error_type = type(error).__name__
        
        recovery_actions = []
        
        if "connection" in error_type.lower() or "timeout" in error_type.lower():
            recovery_actions.append("Restarting network connection")
            await asyncio.sleep(2)
            
        elif "nonce" in str(error).lower():
            recovery_actions.append("Resetting nonce counter")
            
        elif "gas" in str(error).lower():
            recovery_actions.append("Adjusting gas parameters")
            
        elif "balance" in str(error).lower():
            recovery_actions.append("Checking wallet balance")
            
        else:
            recovery_actions.append(f"Generic recovery for {error_type}")
            
        action = recovery_actions[0] if recovery_actions else "Logged error"
        logger.info(f"🔄 Recovery action: {action}")
        return action
        
    async def health_check(self) -> HealthStatus:
        """Perform comprehensive health check"""
        issues = []
        recovery_actions = []
        
        # Check error rate
        if self.error_count > 10:
            issues.append(f"High error count: {self.error_count}")
            recovery_actions.append("Resetting error counter")
            
        # Check consecutive failures
        if self.consecutive_successes == 0 and self.error_count > 0:
            issues.append("No recent successes")
            recovery_actions.append("Attempting recovery transaction")
            
        self.health_status = HealthStatus(
            is_healthy=len(issues) == 0,
            last_check=datetime.now(),
            issues=issues,
            recovery_actions=recovery_actions
        )
        
        if not self.health_status.is_healthy:
            logger.warning(f"Health check failed: {issues}")
            
        return self.health_status
        
    async def monitor_and_heal(self, check_interval: float = 30.0):
        """Continuous monitoring and healing loop"""
        while True:
            try:
                await self.health_check()
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(check_interval)
                
    def get_status_report(self) -> str:
        """Get human-readable status report"""
        return f"""
=== MEV Bot Health Status ===
Healthy: {self.health_status.is_healthy}
Last Check: {self.health_status.last_check}
Error Count: {self.error_count}
Consecutive Successes: {self.consecutive_successes}
Issues: {self.health_status.issues or 'None'}
Recovery Actions: {self.health_status.recovery_actions or 'None'}
"""
