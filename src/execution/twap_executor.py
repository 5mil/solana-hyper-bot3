"""TWAP Executor: Time-weighted average price execution with slicing.

Splits large orders into smaller slices over time to reduce market impact.
Uses quote API to get current prices and checks slippage tolerance.
"""

import time
import asyncio
from typing import List, Optional
from src.core.types import Action, MarketState, ExecutionReport
from src.execution.interfaces import QuoteProvider


class TWAPExecutor:
    """TWAP (Time-Weighted Average Price) executor.
    
    Splits orders into slices and executes them over time to minimize
    market impact. Checks slippage tolerance before each slice.
    
    Attributes:
        quote_provider: Provider for getting trade quotes
        num_slices: Number of slices to split order into
        slice_delay_sec: Delay between slices in seconds
        max_slippage_bps: Maximum acceptable slippage in basis points
    """
    
    def __init__(
        self,
        quote_provider: QuoteProvider,
        num_slices: int = 5,
        slice_delay_sec: float = 2.0,
        max_slippage_bps: float = 50.0,
    ):
        """Initialize TWAPExecutor.
        
        Args:
            quote_provider: Quote provider implementation
            num_slices: Number of order slices (default: 5)
            slice_delay_sec: Delay between slices (default: 2.0)
            max_slippage_bps: Max slippage tolerance in bps (default: 50)
        """
        self.quote_provider = quote_provider
        self.num_slices = num_slices
        self.slice_delay_sec = slice_delay_sec
        self.max_slippage_bps = max_slippage_bps
    
    def execute(
        self,
        action: Action,
        market_state: MarketState,
        size_usd: float,
    ) -> List[ExecutionReport]:
        """Execute order using TWAP strategy.
        
        Args:
            action: Action to execute
            market_state: Current market state
            size_usd: Total position size in USD
            
        Returns:
            List of ExecutionReport for each slice
        """
        slice_size = size_usd / self.num_slices
        reports: List[ExecutionReport] = []
        
        side = "buy" if action.action_type.value in ["long", "buy"] else "sell"
        
        for i in range(self.num_slices):
            # Get quote for this slice
            try:
                quote = self.quote_provider.get_quote(
                    symbol=market_state.symbol,
                    size_notional=slice_size,
                    side=side,
                )
            except Exception as e:
                # Quote failed
                reports.append(ExecutionReport(
                    success=False,
                    transaction_id=None,
                    execution_price=None,
                    slippage_bps=0.0,
                    fees=0.0,
                    latency_ms=0.0,
                    timestamp=int(time.time() * 1000),
                    error_message=f"Quote failed: {str(e)}",
                ))
                continue
            
            # Check slippage tolerance
            quoted_slippage_bps = quote.get("slippage_bps", 0.0)
            if quoted_slippage_bps > self.max_slippage_bps:
                # Slippage too high, skip this slice
                reports.append(ExecutionReport(
                    success=False,
                    transaction_id=None,
                    execution_price=quote.get("price"),
                    slippage_bps=quoted_slippage_bps,
                    fees=0.0,
                    latency_ms=0.0,
                    timestamp=int(time.time() * 1000),
                    error_message=f"Slippage {quoted_slippage_bps}bps exceeds max {self.max_slippage_bps}bps",
                ))
                continue
            
            # Execute slice
            execution_start = time.time()
            time.sleep(0.05)  # Simulate execution delay
            execution_latency = (time.time() - execution_start) * 1000
            
            # Generate transaction ID
            tx_id = f"twap_slice_{i}_{int(time.time() * 1000)}"
            
            reports.append(ExecutionReport(
                success=True,
                transaction_id=tx_id,
                execution_price=quote["price"],
                slippage_bps=quoted_slippage_bps,
                fees=quote.get("fees", 0.0),
                latency_ms=execution_latency,
                timestamp=int(time.time() * 1000),
                error_message=None,
            ))
            
            # Wait before next slice (except on last slice)
            if i < self.num_slices - 1:
                time.sleep(self.slice_delay_sec)
        
        return reports
    
    async def execute_async(
        self,
        action: Action,
        market_state: MarketState,
        size_usd: float,
    ) -> List[ExecutionReport]:
        """Execute order using TWAP strategy asynchronously.
        
        Args:
            action: Action to execute
            market_state: Current market state
            size_usd: Total position size in USD
            
        Returns:
            List of ExecutionReport for each slice
        """
        slice_size = size_usd / self.num_slices
        reports: List[ExecutionReport] = []
        
        side = "buy" if action.action_type.value in ["long", "buy"] else "sell"
        
        for i in range(self.num_slices):
            # Get quote for this slice
            try:
                quote = await self.quote_provider.get_quote_async(
                    symbol=market_state.symbol,
                    size_notional=slice_size,
                    side=side,
                )
            except Exception as e:
                reports.append(ExecutionReport(
                    success=False,
                    transaction_id=None,
                    execution_price=None,
                    slippage_bps=0.0,
                    fees=0.0,
                    latency_ms=0.0,
                    timestamp=int(time.time() * 1000),
                    error_message=f"Quote failed: {str(e)}",
                ))
                continue
            
            # Check slippage tolerance
            quoted_slippage_bps = quote.get("slippage_bps", 0.0)
            if quoted_slippage_bps > self.max_slippage_bps:
                reports.append(ExecutionReport(
                    success=False,
                    transaction_id=None,
                    execution_price=quote.get("price"),
                    slippage_bps=quoted_slippage_bps,
                    fees=0.0,
                    latency_ms=0.0,
                    timestamp=int(time.time() * 1000),
                    error_message=f"Slippage {quoted_slippage_bps}bps exceeds max {self.max_slippage_bps}bps",
                ))
                continue
            
            # Execute slice
            execution_start = time.time()
            await asyncio.sleep(0.05)  # Simulate execution delay
            execution_latency = (time.time() - execution_start) * 1000
            
            tx_id = f"twap_slice_{i}_{int(time.time() * 1000)}"
            
            reports.append(ExecutionReport(
                success=True,
                transaction_id=tx_id,
                execution_price=quote["price"],
                slippage_bps=quoted_slippage_bps,
                fees=quote.get("fees", 0.0),
                latency_ms=execution_latency,
                timestamp=int(time.time() * 1000),
                error_message=None,
            ))
            
            # Wait before next slice
            if i < self.num_slices - 1:
                await asyncio.sleep(self.slice_delay_sec)
        
        return reports
