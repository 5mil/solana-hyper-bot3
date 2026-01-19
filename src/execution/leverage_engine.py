"""
LeverageEngine: Position sizing and leverage management.

Implements Kelly-like sizing with maximum leverage and position limits.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from src.core.types import Action, MarketState


@dataclass
class LeverageConfig:
    """Configuration for leverage engine."""
    max_leverage: float = 5.0
    max_position_pct: float = 0.35
    min_position_pct: float = 0.01
    risk_per_trade_pct: float = 0.02
    account_balance: float = 100.0


class LeverageEngine:
    """
    Position sizing and leverage management.
    
    Determines optimal position size and leverage based on confidence,
    account balance, and risk limits.
    """
    
    def __init__(self, config: Optional[LeverageConfig] = None):
        """
        Initialize leverage engine.
        
        Args:
            config: Leverage configuration
        """
        self.config = config or LeverageConfig()
    
    def size_position(
        self,
        action: Action,
        market_state: MarketState,
        account_balance: Optional[float] = None
    ) -> Action:
        """
        Size a position based on Kelly-like allocation.
        
        Args:
            action: Base action with confidence
            market_state: Current market state
            account_balance: Current account balance (overrides config)
            
        Returns:
            Action with updated size and leverage
        """
        balance = account_balance or self.config.account_balance
        
        # Base allocation on confidence
        # Higher confidence -> larger position
        allocation_pct = action.confidence * self.config.max_position_pct
        allocation_pct = max(self.config.min_position_pct, allocation_pct)
        
        # Adjust for market liquidity
        allocation_pct *= market_state.liquidity_score
        
        # Reduce for high volatility
        if market_state.volatility > 0.05:
            allocation_pct *= 0.7
        
        # Clamp to limits
        allocation_pct = min(allocation_pct, self.config.max_position_pct)
        
        # Calculate position size
        position_size = balance * allocation_pct
        
        # Determine leverage
        # Higher confidence allows more leverage
        base_leverage = 1.0 + (action.confidence * (self.config.max_leverage - 1.0))
        leverage = min(base_leverage, self.config.max_leverage)
        
        # Reduce leverage in volatile markets
        if market_state.volatility > 0.05:
            leverage = max(1.0, leverage * 0.6)
        
        # Update action
        action.size = position_size
        action.leverage = leverage
        action.price = market_state.price
        action.metadata["allocation_pct"] = allocation_pct
        action.metadata["account_balance"] = balance
        
        return action
    
    async def request_margin(
        self,
        size: float,
        leverage: float,
        collateral: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Stub method for requesting margin from providers.
        
        In production, this would interface with Drift/Marginfi.
        
        Args:
            size: Position size
            leverage: Leverage multiplier
            collateral: Optional collateral amount
            
        Returns:
            Margin response
        """
        # Calculate required collateral
        if collateral is None:
            collateral = size / leverage
        
        # Simple approval for simulation
        return {
            "approved": True,
            "size": size,
            "leverage": leverage,
            "collateral_required": collateral,
            "interest_rate": 0.0001,  # 0.01% per trade
            "provider": "stub"
        }
