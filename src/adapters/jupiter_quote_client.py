"""
Jupiter Quote Client for real-time trade quotes.

Implements QuoteClient protocol to fetch actual quotes from Jupiter aggregator.
"""
import logging
from typing import Dict, Any, Optional
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class JupiterQuoteClient:
    """
    Real-time quote client using Jupiter aggregator API.
    
    Fetches actual quotes with real slippage and fee data.
    """
    
    def __init__(
        self,
        jupiter_endpoint: str = "https://quote-api.jup.ag/v6",
        timeout_sec: float = 5.0,
        max_retries: int = 3
    ):
        """
        Initialize Jupiter quote client.
        
        Args:
            jupiter_endpoint: Jupiter API base URL
            timeout_sec: HTTP request timeout
            max_retries: Maximum retry attempts
        """
        self.jupiter_endpoint = jupiter_endpoint
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        
        # Token addresses
        self.sol_mint = "So11111111111111111111111111111111111111112"
        self.usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        logger.info(f"Initialized JupiterQuoteClient: {jupiter_endpoint}")
    
    async def get_quote(
        self,
        symbol: str,
        size_notional: float,
        side: str
    ) -> Dict[str, Any]:
        """
        Get a real-time quote from Jupiter.
        
        Args:
            symbol: Trading pair (e.g., "SOL/USD")
            size_notional: Size in USD
            side: "buy" or "sell"
            
        Returns:
            Quote dictionary with price, slippage, fees
        """
        # Convert USD size to token amount
        # For simplicity, we'll get a quote and derive the price
        
        # Determine input/output mints based on side
        if side.lower() == "buy":
            input_mint = self.usdc_mint
            output_mint = self.sol_mint
            # Convert USD to USDC (6 decimals)
            amount = int(size_notional * 10**6)
        else:  # sell
            input_mint = self.sol_mint
            output_mint = self.usdc_mint
            # TODO: Fetch current price for more accurate quote amount
            # For now, use rough estimate of $100/SOL
            amount = int((size_notional / 100) * 10**9)  # Assume ~$100/SOL
        
        url = f"{self.jupiter_endpoint}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": "50"  # 0.5% slippage tolerance
        }
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    query = "&".join(f"{k}={v}" for k, v in params.items())
                    full_url = f"{url}?{query}"
                    
                    async with session.get(
                        full_url,
                        timeout=aiohttp.ClientTimeout(total=self.timeout_sec)
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        # Extract quote data
                        in_amount = int(data.get("inAmount", 0))
                        out_amount = int(data.get("outAmount", 0))
                        
                        # Calculate price and slippage
                        if side.lower() == "buy":
                            # Buying SOL with USDC
                            price = (in_amount / 10**6) / (out_amount / 10**9)
                            sol_received = out_amount / 10**9
                        else:
                            # Selling SOL for USDC
                            price = (out_amount / 10**6) / (in_amount / 10**9)
                            sol_received = 0
                        
                        # Extract price impact (slippage)
                        price_impact = float(data.get("priceImpactPct", 0))
                        slippage_pct = abs(price_impact)
                        
                        # Estimate fees (Jupiter typically 0-0.05%)
                        fees_usd = size_notional * 0.0005  # 0.05% estimate
                        
                        logger.debug(
                            f"Jupiter quote: {side} ${size_notional:.2f} at ${price:.2f}, "
                            f"slippage={slippage_pct:.4f}%, fees=${fees_usd:.4f}"
                        )
                        
                        return {
                            "price": price,
                            "slippage_pct": slippage_pct,
                            "fees_usd": fees_usd,
                            "estimated_fill": sol_received if side.lower() == "buy" else size_notional / price,
                            "route_plan": data.get("routePlan", []),
                            "raw_quote": data
                        }
                        
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Quote request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("All quote attempts failed, using fallback")
                        # Return fallback quote
                        return {
                            "price": 100.0,  # Fallback price
                            "slippage_pct": 0.1,
                            "fees_usd": size_notional * 0.001,
                            "estimated_fill": size_notional / 100.0,
                            "route_plan": [],
                            "raw_quote": {},
                            "is_fallback": True
                        }
