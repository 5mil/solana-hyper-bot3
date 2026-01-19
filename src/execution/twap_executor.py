"""
TWAPExecutor: Time-Weighted Average Price order execution.

Slices large orders into smaller chunks and executes them over time
to minimize market impact and slippage.
"""
import asyncio
from typing import Dict, Any, List
from src.core.types import Action, MarketState
from src.execution.interfaces import QuoteClient


class TWAPExecutor:
    """
    TWAP executor that slices orders over time.
    
    Breaks large orders into smaller slices to reduce market impact
    and checks slippage tolerance for each slice.
    """
    
    def __init__(
        self,
        quote_client: QuoteClient,
        num_slices: int = 5,
        slice_interval_sec: float = 2.0,
        slippage_tolerance_pct: float = 1.0
    ):
        """
        Initialize TWAP executor.
        
        Args:
            quote_client: Client for getting quotes
            num_slices: Number of slices to break order into
            slice_interval_sec: Time between slices
            slippage_tolerance_pct: Maximum acceptable slippage per slice
        """
        self.quote_client = quote_client
        self.num_slices = num_slices
        self.slice_interval_sec = slice_interval_sec
        self.slippage_tolerance_pct = slippage_tolerance_pct
    
    async def execute_twap(
        self,
        action: Action,
        market_state: MarketState
    ) -> Dict[str, Any]:
        """
        Execute action using TWAP strategy.
        
        Args:
            action: Action to execute
            market_state: Current market state
            
        Returns:
            Execution report with per-slice details
        """
        slice_size = action.size / self.num_slices
        slice_reports: List[Dict[str, Any]] = []
        total_filled = 0.0
        total_cost = 0.0
        rejected_slices = 0
        
        for i in range(self.num_slices):
            # Get quote for this slice
            try:
                quote = await self.quote_client.get_quote(
                    symbol=market_state.symbol,
                    size_notional=slice_size,
                    side=action.action_type.value
                )
                
                # Check slippage tolerance
                slippage_pct = quote.get("slippage_pct", 0.0)
                if slippage_pct > self.slippage_tolerance_pct:
                    slice_reports.append({
                        "slice": i + 1,
                        "status": "rejected",
                        "reason": f"Slippage {slippage_pct:.2f}% > {self.slippage_tolerance_pct}%",
                        "size": slice_size,
                        "slippage_pct": slippage_pct
                    })
                    rejected_slices += 1
                    continue
                
                # Execute slice
                fill_price = quote.get("price", market_state.price)
                fees = quote.get("fees", 0.0)
                
                slice_cost = slice_size * fill_price + fees
                total_filled += slice_size
                total_cost += slice_cost
                
                slice_reports.append({
                    "slice": i + 1,
                    "status": "filled",
                    "size": slice_size,
                    "fill_price": fill_price,
                    "slippage_pct": slippage_pct,
                    "fees": fees,
                    "cost": slice_cost
                })
                
            except Exception as e:
                slice_reports.append({
                    "slice": i + 1,
                    "status": "error",
                    "reason": str(e),
                    "size": slice_size
                })
                rejected_slices += 1
            
            # Wait before next slice (except for last slice)
            if i < self.num_slices - 1:
                await asyncio.sleep(self.slice_interval_sec)
        
        # Calculate average fill price
        avg_fill_price = total_cost / total_filled if total_filled > 0 else market_state.price
        
        return {
            "success": rejected_slices < self.num_slices,
            "action": action.action_type.value,
            "requested_size": action.size,
            "filled_size": total_filled,
            "fill_rate": total_filled / action.size if action.size > 0 else 0,
            "avg_fill_price": avg_fill_price,
            "total_cost": total_cost,
            "num_slices": self.num_slices,
            "filled_slices": self.num_slices - rejected_slices,
            "rejected_slices": rejected_slices,
            "slice_reports": slice_reports
        }
    
    async def execute_action(
        self,
        action: Action,
        market_state: MarketState
    ) -> Dict[str, Any]:
        """
        Execute an action via TWAP.
        
        Args:
            action: Action to execute
            market_state: Current market state
            
        Returns:
            Execution report
        """
        return await self.execute_twap(action, market_state)
