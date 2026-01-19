"""Execution interfaces: Protocol definitions for external integrations.

Defines Protocol interfaces for market data fetching and execution providers,
allowing easy mocking and testing without requiring live connections.
"""

from typing import Protocol, Optional
from src.core.types import MarketState, ExecutionReport, Action


class MarketDataFetcher(Protocol):
    """Protocol for fetching market data.
    
    Implementations should fetch current market state from various sources
    (Solana RPC, DEX APIs, etc.) and return standardized MarketState objects.
    """
    
    def fetch_market_state(self, symbol: str = "SOL/USD") -> MarketState:
        """Fetch current market state for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Current MarketState snapshot
        """
        ...
    
    async def fetch_market_state_async(self, symbol: str = "SOL/USD") -> MarketState:
        """Fetch market state asynchronously.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Current MarketState snapshot
        """
        ...


class ExecutionProvider(Protocol):
    """Protocol for executing trades.
    
    Implementations handle actual trade execution through various venues
    (Jito bundles, Jupiter swaps, Drift perps, etc.).
    """
    
    def execute(self, action: Action, market_state: MarketState) -> ExecutionReport:
        """Execute a trading action.
        
        Args:
            action: Action to execute
            market_state: Current market state
            
        Returns:
            ExecutionReport with results
        """
        ...
    
    async def execute_async(
        self,
        action: Action,
        market_state: MarketState,
    ) -> ExecutionReport:
        """Execute a trading action asynchronously.
        
        Args:
            action: Action to execute
            market_state: Current market state
            
        Returns:
            ExecutionReport with results
        """
        ...


class QuoteProvider(Protocol):
    """Protocol for getting trade quotes.
    
    Implementations fetch quotes from DEX aggregators like Jupiter,
    providing expected prices and slippage for given sizes.
    """
    
    def get_quote(
        self,
        symbol: str,
        size_notional: float,
        side: str = "buy",
    ) -> dict:
        """Get a quote for a trade.
        
        Args:
            symbol: Trading pair symbol
            size_notional: Notional size of trade
            side: "buy" or "sell"
            
        Returns:
            Quote dictionary with price, slippage estimates, etc.
        """
        ...
    
    async def get_quote_async(
        self,
        symbol: str,
        size_notional: float,
        side: str = "buy",
    ) -> dict:
        """Get a quote asynchronously.
        
        Args:
            symbol: Trading pair symbol
            size_notional: Notional size of trade
            side: "buy" or "sell"
            
        Returns:
            Quote dictionary with price, slippage estimates, etc.
        """
        ...


class MarginProvider(Protocol):
    """Protocol for margin/leverage operations.
    
    Implementations interact with lending protocols (Drift, Marginfi, etc.)
    to request margin and manage leveraged positions.
    """
    
    def request_margin(
        self,
        collateral_amount: float,
        leverage: float,
    ) -> bool:
        """Request margin for a leveraged position.
        
        Args:
            collateral_amount: Amount of collateral to post
            leverage: Desired leverage multiplier
            
        Returns:
            True if margin request successful
        """
        ...
    
    async def request_margin_async(
        self,
        collateral_amount: float,
        leverage: float,
    ) -> bool:
        """Request margin asynchronously.
        
        Args:
            collateral_amount: Amount of collateral to post
            leverage: Desired leverage multiplier
            
        Returns:
            True if margin request successful
        """
        ...
