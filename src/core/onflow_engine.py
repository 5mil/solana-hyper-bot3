"""Onflow Engine: Gradient-based allocation with Kelly-like criterion.

The OnflowEngine maintains EWMA (Exponentially Weighted Moving Average) estimates
of win rate and returns to compute optimal allocation fractions using a Kelly-like
criterion. This provides dynamic position sizing based on recent performance.
"""

import numpy as np
from typing import Optional


class OnflowEngine:
    """Gradient-flow allocation engine with Kelly-like criterion.
    
    Maintains exponentially weighted moving averages of:
    - Win rate
    - Average return per trade
    
    Uses these to compute Kelly-like allocation fraction:
    f = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    
    Attributes:
        alpha: EWMA decay factor (higher = more weight on recent data)
        min_allocation: Minimum allocation fraction
        max_allocation: Maximum allocation fraction
        ewma_win_rate: Current EWMA win rate estimate
        ewma_avg_return: Current EWMA average return estimate
        trade_count: Number of trades processed
    """
    
    def __init__(
        self,
        alpha: float = 0.3,
        min_allocation: float = 0.05,
        max_allocation: float = 0.35,
    ):
        """Initialize OnflowEngine.
        
        Args:
            alpha: EWMA decay factor (default: 0.3)
            min_allocation: Minimum allocation fraction (default: 0.05)
            max_allocation: Maximum allocation fraction (default: 0.35)
        """
        self.alpha = alpha
        self.min_allocation = min_allocation
        self.max_allocation = max_allocation
        
        # Initialize EWMA estimates
        self.ewma_win_rate: float = 0.5  # Start neutral
        self.ewma_avg_return: float = 0.0
        self.trade_count: int = 0
    
    def update(self, trade_return: float) -> None:
        """Update EWMA estimates with a new trade result.
        
        Args:
            trade_return: Return from the trade (positive for profit, negative for loss)
        """
        self.trade_count += 1
        
        # Update win rate (1 if profitable, 0 if loss)
        is_win = 1.0 if trade_return > 0 else 0.0
        self.ewma_win_rate = (
            self.alpha * is_win + (1 - self.alpha) * self.ewma_win_rate
        )
        
        # Update average return
        self.ewma_avg_return = (
            self.alpha * trade_return + (1 - self.alpha) * self.ewma_avg_return
        )
    
    def get_allocation_fraction(self, confidence: float = 1.0) -> float:
        """Compute optimal allocation fraction using Kelly-like criterion.
        
        Args:
            confidence: Confidence multiplier (0-1) to scale allocation
            
        Returns:
            Allocation fraction between min_allocation and max_allocation
        """
        # If not enough data, return minimum allocation
        if self.trade_count < 2:
            return self.min_allocation
        
        # Simple Kelly-like formula
        # For positive expected value: f = edge / odds
        # We use a simplified version based on win rate and avg return
        win_rate = self.ewma_win_rate
        avg_return = abs(self.ewma_avg_return)
        
        # Compute base allocation
        if avg_return > 0:
            # Kelly fraction approximation
            edge = win_rate - (1 - win_rate)
            base_allocation = max(0, edge) * avg_return * 0.5  # Half-Kelly for safety
        else:
            base_allocation = self.min_allocation
        
        # Scale by confidence
        allocation = base_allocation * confidence
        
        # Clamp to bounds
        allocation = np.clip(allocation, self.min_allocation, self.max_allocation)
        
        return float(allocation)
    
    def get_state(self) -> dict:
        """Get current engine state for logging/monitoring.
        
        Returns:
            Dictionary with current EWMA estimates and trade count
        """
        return {
            "ewma_win_rate": self.ewma_win_rate,
            "ewma_avg_return": self.ewma_avg_return,
            "trade_count": self.trade_count,
            "alpha": self.alpha,
        }
