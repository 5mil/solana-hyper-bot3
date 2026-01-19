"""
OnflowEngine: Gradient-based allocation engine using Kelly-like criterion.

Implements an exponentially weighted moving average (EWMA) estimate of
returns and suggests allocation fractions for position sizing.
"""
import numpy as np
from typing import Optional
from src.core.types import MarketState, Action, ActionType


class OnflowEngine:
    """
    Gradient-flow allocation engine implementing Kelly-like sizing.
    
    Uses EWMA estimates of win rate and average returns to compute
    optimal allocation fractions. The allocation is capped to prevent
    over-leveraging.
    """
    
    def __init__(
        self,
        ewma_alpha: float = 0.2,
        max_allocation: float = 0.5,
        min_allocation: float = 0.01,
        kelly_fraction: float = 0.25
    ):
        """
        Initialize the OnflowEngine.
        
        Args:
            ewma_alpha: Smoothing factor for EWMA (0-1, higher = more weight on recent)
            max_allocation: Maximum allocation fraction (0-1)
            min_allocation: Minimum allocation fraction when taking action
            kelly_fraction: Fraction of full Kelly to use (for safety)
        """
        self.ewma_alpha = ewma_alpha
        self.max_allocation = max_allocation
        self.min_allocation = min_allocation
        self.kelly_fraction = kelly_fraction
        
        # EWMA state
        self.ewma_win_rate: Optional[float] = None
        self.ewma_avg_return: Optional[float] = None
        self.ewma_volatility: Optional[float] = None
        self.trade_count = 0
    
    def update(self, won: bool, return_pct: float, volatility: float = 0.0):
        """
        Update EWMA estimates with new trade result.
        
        Args:
            won: Whether the trade was profitable
            return_pct: Return percentage (positive or negative)
            volatility: Market volatility at trade time
        """
        self.trade_count += 1
        
        # Update win rate
        win_value = 1.0 if won else 0.0
        if self.ewma_win_rate is None:
            self.ewma_win_rate = win_value
        else:
            self.ewma_win_rate = (
                self.ewma_alpha * win_value +
                (1 - self.ewma_alpha) * self.ewma_win_rate
            )
        
        # Update average return
        if self.ewma_avg_return is None:
            self.ewma_avg_return = return_pct
        else:
            self.ewma_avg_return = (
                self.ewma_alpha * return_pct +
                (1 - self.ewma_alpha) * self.ewma_avg_return
            )
        
        # Update volatility estimate
        if self.ewma_volatility is None:
            self.ewma_volatility = volatility
        else:
            self.ewma_volatility = (
                self.ewma_alpha * volatility +
                (1 - self.ewma_alpha) * self.ewma_volatility
            )
    
    def suggest_allocation(self, market_state: MarketState) -> float:
        """
        Suggest allocation fraction based on Kelly-like criterion.
        
        Args:
            market_state: Current market state
            
        Returns:
            Allocation fraction (0-1)
        """
        # If no history, use conservative allocation
        if self.ewma_win_rate is None or self.ewma_avg_return is None:
            return self.min_allocation
        
        # Kelly formula: f = (p * b - q) / b
        # where p = win rate, q = 1 - p, b = avg_win / avg_loss ratio
        # Simplified: f ≈ edge / variance
        
        p = self.ewma_win_rate
        q = 1 - p
        
        # Estimate edge
        edge = self.ewma_avg_return / 100.0  # Convert percentage to fraction
        
        # Use volatility as risk measure
        volatility = market_state.volatility if market_state.volatility > 0 else 0.1
        if self.ewma_volatility and self.ewma_volatility > 0:
            volatility = (volatility + self.ewma_volatility) / 2
        
        # Compute Kelly fraction
        # f = edge / (volatility^2)
        if volatility > 0:
            kelly_f = edge / (volatility ** 2)
        else:
            kelly_f = self.min_allocation
        
        # Apply Kelly fraction multiplier for safety
        kelly_f *= self.kelly_fraction
        
        # Adjust for win rate (boost if winning consistently)
        kelly_f *= (0.5 + p * 0.5)
        
        # Clamp to bounds
        allocation = np.clip(kelly_f, self.min_allocation, self.max_allocation)
        
        return float(allocation)
    
    def get_state(self) -> dict:
        """Get current engine state for monitoring."""
        return {
            "trade_count": self.trade_count,
            "ewma_win_rate": self.ewma_win_rate,
            "ewma_avg_return": self.ewma_avg_return,
            "ewma_volatility": self.ewma_volatility
        }
