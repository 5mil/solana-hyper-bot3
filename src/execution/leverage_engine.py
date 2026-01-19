"""Leverage Engine: Position sizing and margin management.

The LeverageEngine handles position sizing with leverage constraints,
implements Kelly-like allocation, and provides margin request interfaces.
"""

from dataclasses import dataclass
from typing import Optional
from src.core.types import Action, MarketState


@dataclass
class LeverageConfig:
    """Configuration for leverage engine.
    
    Attributes:
        max_leverage: Maximum leverage allowed (default: 5.0)
        max_position_pct: Maximum position size as % of capital (default: 0.35)
        min_position_pct: Minimum position size as % of capital (default: 0.01)
        use_kelly: Whether to use Kelly criterion for sizing (default: True)
    """
    max_leverage: float = 5.0
    max_position_pct: float = 0.35
    min_position_pct: float = 0.01
    use_kelly: bool = True


class LeverageEngine:
    """Engine for computing position sizes with leverage constraints.
    
    Takes an Action with a suggested size_fraction and confidence, applies
    leverage rules and position limits, and returns adjusted sizing.
    
    Attributes:
        config: LeverageConfig with constraints
        current_capital: Current account capital
    """
    
    def __init__(
        self,
        config: Optional[LeverageConfig] = None,
        current_capital: float = 100.0,
    ):
        """Initialize LeverageEngine.
        
        Args:
            config: LeverageConfig (uses defaults if None)
            current_capital: Current account capital
        """
        self.config = config or LeverageConfig()
        self.current_capital = current_capital
    
    def compute_position_size(
        self,
        action: Action,
        market_state: MarketState,
        allocation_fraction: float,
    ) -> tuple[float, float]:
        """Compute position size and effective leverage.
        
        Args:
            action: Action with confidence and leverage suggestion
            market_state: Current market state
            allocation_fraction: Allocation fraction from OnflowEngine
            
        Returns:
            Tuple of (position_size_usd, effective_leverage)
        """
        # Start with allocation fraction
        base_fraction = allocation_fraction
        
        # Apply confidence scaling
        confidence_scaled = base_fraction * action.confidence
        
        # Apply position limits
        final_fraction = max(
            self.config.min_position_pct,
            min(confidence_scaled, self.config.max_position_pct)
        )
        
        # Compute base position size
        position_size = self.current_capital * final_fraction
        
        # Apply leverage (capped at max_leverage)
        desired_leverage = min(action.leverage, self.config.max_leverage)
        effective_leverage = desired_leverage if self.config.use_kelly else 1.0
        
        # Final position size with leverage
        leveraged_position_size = position_size * effective_leverage
        
        return leveraged_position_size, effective_leverage
    
    def request_margin(
        self,
        collateral_amount: float,
        leverage: float,
    ) -> dict:
        """Request margin for a leveraged position (stub implementation).
        
        In production, this would interact with Drift/Marginfi via MarginProvider.
        For simulation, returns a mock success response.
        
        Args:
            collateral_amount: Amount of collateral to post
            leverage: Desired leverage
            
        Returns:
            Dictionary with margin request result
        """
        # Validate inputs
        if leverage > self.config.max_leverage:
            return {
                "success": False,
                "error": f"Leverage {leverage} exceeds max {self.config.max_leverage}",
            }
        
        if collateral_amount > self.current_capital:
            return {
                "success": False,
                "error": f"Insufficient capital: {collateral_amount} > {self.current_capital}",
            }
        
        # Mock success
        return {
            "success": True,
            "collateral_posted": collateral_amount,
            "leverage_granted": leverage,
            "buying_power": collateral_amount * leverage,
        }
    
    def update_capital(self, new_capital: float) -> None:
        """Update current capital after trades.
        
        Args:
            new_capital: New capital amount
        """
        self.current_capital = new_capital
