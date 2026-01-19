"""Mock Quote Client: Jupiter-like quote provider for testing.

Provides realistic quote responses without requiring live Jupiter API access.
"""

import random
import time
from typing import Optional


class MockQuoteClient:
    """Mock Jupiter-like quote client for local testing.
    
    Generates realistic quotes with simulated slippage and fees based on
    order size and market conditions.
    
    Attributes:
        base_price: Base price for quotes
        base_slippage_bps: Base slippage in basis points
        base_fee_bps: Base fee in basis points
    """
    
    def __init__(
        self,
        base_price: float = 100.0,
        base_slippage_bps: float = 3.0,
        base_fee_bps: float = 5.0,
    ):
        """Initialize MockQuoteClient.
        
        Args:
            base_price: Base price for quotes (default: 100.0)
            base_slippage_bps: Base slippage in bps (default: 3.0)
            base_fee_bps: Base fee in bps (default: 5.0)
        """
        self.base_price = base_price
        self.base_slippage_bps = base_slippage_bps
        self.base_fee_bps = base_fee_bps
    
    def get_quote(
        self,
        symbol: str,
        size_notional: float,
        side: str = "buy",
    ) -> dict:
        """Get a mock quote for a trade.
        
        Args:
            symbol: Trading pair symbol
            size_notional: Notional size of trade
            side: "buy" or "sell"
            
        Returns:
            Quote dictionary with price, slippage, fees
        """
        # Add random price movement
        price_variation = random.uniform(-2, 2)
        current_price = self.base_price * (1 + price_variation / 100)
        
        # Compute slippage based on size
        size_impact_factor = min(size_notional / 1000, 1.0)
        slippage_bps = self.base_slippage_bps * (1 + size_impact_factor * 2)
        
        # Apply slippage to price
        if side == "buy":
            quoted_price = current_price * (1 + slippage_bps / 10000)
        else:
            quoted_price = current_price * (1 - slippage_bps / 10000)
        
        # Compute fees
        fees = size_notional * (self.base_fee_bps / 10000)
        
        return {
            "symbol": symbol,
            "side": side,
            "size_notional": size_notional,
            "price": quoted_price,
            "slippage_bps": slippage_bps,
            "fees": fees,
            "timestamp": int(time.time() * 1000),
        }
    
    async def get_quote_async(
        self,
        symbol: str,
        size_notional: float,
        side: str = "buy",
    ) -> dict:
        """Get a mock quote asynchronously.
        
        Args:
            symbol: Trading pair symbol
            size_notional: Notional size of trade
            side: "buy" or "sell"
            
        Returns:
            Quote dictionary with price, slippage, fees
        """
        import asyncio
        # Simulate async delay
        await asyncio.sleep(0.01)
        return self.get_quote(symbol, size_notional, side)
    
    def update_base_price(self, new_price: float) -> None:
        """Update the base price for quotes.
        
        Args:
            new_price: New base price
        """
        self.base_price = new_price
