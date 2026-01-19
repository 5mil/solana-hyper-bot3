"""
Protocol interfaces for execution and market data.

Defines abstract interfaces that all adapters must implement.
"""
from typing import Protocol, Optional, Dict, Any
from src.core.types import MarketState, Action


class MarketDataFetcher(Protocol):
    """
    Protocol for fetching market data.
    
    Implementations should fetch current market state from exchanges or data providers.
    """
    
    async def fetch_market_state(self, symbol: str) -> MarketState:
        """
        Fetch current market state for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "SOL/USD")
            
        Returns:
            Current MarketState
        """
        ...


class QuoteClient(Protocol):
    """
    Protocol for getting trade quotes.
    
    Implementations should provide quotes for given trade sizes.
    """
    
    async def get_quote(
        self,
        symbol: str,
        size_notional: float,
        side: str
    ) -> Dict[str, Any]:
        """
        Get a quote for a trade.
        
        Args:
            symbol: Trading pair symbol
            size_notional: Size in notional currency (e.g., USD)
            side: "buy" or "sell"
            
        Returns:
            Quote dictionary with price, slippage, fees
        """
        ...


class ExecutionProvider(Protocol):
    """
    Protocol for executing trades.
    
    Implementations should handle trade execution and return results.
    """
    
    async def execute_action(
        self,
        action: Action,
        market_state: MarketState
    ) -> Dict[str, Any]:
        """
        Execute a trading action.
        
        Args:
            action: Action to execute
            market_state: Current market state
            
        Returns:
            Execution report with status, fill price, fees, etc.
        """
        ...


class MarginProvider(Protocol):
    """
    Protocol for margin/leverage providers.
    
    Implementations should handle margin requests and position management.
    """
    
    async def request_margin(
        self,
        size: float,
        leverage: float,
        collateral: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Request margin for a leveraged position.
        
        Args:
            size: Position size
            leverage: Leverage multiplier
            collateral: Optional collateral amount
            
        Returns:
            Margin response with approval status and terms
        """
        ...
