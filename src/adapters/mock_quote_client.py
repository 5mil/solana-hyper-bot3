"""
MockQuoteClient: Mock Jupiter-like quote client for testing.

Provides simulated quotes without requiring real API access.
"""
import random
from typing import Dict, Any


class MockQuoteClient:
    """
    Mock Jupiter quote client for local testing.
    
    Simulates quote responses with realistic slippage and fees.
    """
    
    def __init__(
        self,
        base_price: float = 100.0,
        base_slippage_pct: float = 0.05,
        base_fee_pct: float = 0.05
    ):
        """
        Initialize mock quote client.
        
        Args:
            base_price: Base price for quotes
            base_slippage_pct: Base slippage percentage
            base_fee_pct: Base fee percentage
        """
        self.base_price = base_price
        self.base_slippage_pct = base_slippage_pct
        self.base_fee_pct = base_fee_pct
    
    async def get_quote(
        self,
        symbol: str,
        size_notional: float,
        side: str
    ) -> Dict[str, Any]:
        """
        Get a simulated quote.
        
        Args:
            symbol: Trading pair symbol
            size_notional: Size in notional currency
            side: "buy" or "sell"
            
        Returns:
            Quote dictionary
        """
        # Add some price variance
        price = self.base_price * random.uniform(0.995, 1.005)
        
        # Slippage increases with size
        size_factor = min(size_notional / 1000.0, 2.0)
        slippage_pct = self.base_slippage_pct * size_factor * random.uniform(0.8, 1.2)
        
        # Apply slippage
        if side.lower() == "buy":
            quoted_price = price * (1 + slippage_pct / 100)
        else:
            quoted_price = price * (1 - slippage_pct / 100)
        
        # Calculate fees
        fees = size_notional * (self.base_fee_pct / 100)
        
        return {
            "symbol": symbol,
            "side": side,
            "size_notional": size_notional,
            "price": quoted_price,
            "slippage_pct": slippage_pct,
            "fees": fees,
            "route": ["mock_route_1", "mock_route_2"],
            "estimated_execution_time_ms": random.uniform(100, 300)
        }


class MockMarketDataFetcher:
    """
    Mock market data fetcher for testing.
    
    Generates synthetic market data for simulation.
    """
    
    def __init__(
        self,
        base_price: float = 100.0,
        price_volatility: float = 0.02
    ):
        """
        Initialize mock market data fetcher.
        
        Args:
            base_price: Base price for market
            price_volatility: Price volatility for simulation
        """
        self.base_price = base_price
        self.price_volatility = price_volatility
        self.current_price = base_price
    
    async def fetch_market_state(self, symbol: str):
        """
        Fetch simulated market state.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            MarketState
        """
        from src.core.types import MarketState, MarketRegime
        
        # Random walk price
        price_change = random.gauss(0, self.price_volatility)
        self.current_price *= (1 + price_change)
        
        # Keep price in reasonable range
        self.current_price = max(self.current_price, self.base_price * 0.5)
        self.current_price = min(self.current_price, self.base_price * 1.5)
        
        # Generate synthetic market data
        volume = random.uniform(5000, 15000)
        spread_pct = random.uniform(0.01, 0.1)
        
        return MarketState(
            symbol=symbol,
            price=self.current_price,
            volume_24h=volume,
            bid=self.current_price * (1 - spread_pct / 100),
            ask=self.current_price * (1 + spread_pct / 100),
            ema_fast=self.current_price * 1.001,
            ema_slow=self.current_price * 0.999,
            regime=random.choice(list(MarketRegime)),
            volatility=abs(price_change) * 10,
            liquidity_score=random.uniform(0.6, 1.0),
            mev_risk_score=random.uniform(0.0, 0.5),
            latency_ms=random.uniform(50, 200)
        )
