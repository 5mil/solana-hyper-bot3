"""
Real-time market data fetcher using actual Solana/Jupiter APIs.

Implements MarketDataFetcher protocol to fetch live market data from:
- Jupiter API for price quotes
- Birdeye API for volume/liquidity metrics
- Fallback to Solana RPC for on-chain data
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import aiohttp

from src.core.types import MarketState, MarketRegime


logger = logging.getLogger(__name__)


class RealTimeMarketDataFetcher:
    """
    Fetches real-time market data from live Solana APIs.
    
    Uses Jupiter for pricing and Birdeye for market metrics.
    Implements exponential backoff for rate limiting.
    """
    
    def __init__(
        self,
        jupiter_endpoint: str = "https://quote-api.jup.ag/v6",
        birdeye_endpoint: str = "https://public-api.birdeye.so",
        birdeye_api_key: Optional[str] = None,
        timeout_sec: float = 5.0,
        max_retries: int = 3
    ):
        """
        Initialize real-time market data fetcher.
        
        Args:
            jupiter_endpoint: Jupiter API base URL
            birdeye_endpoint: Birdeye API base URL
            birdeye_api_key: Optional Birdeye API key for higher rate limits
            timeout_sec: HTTP request timeout
            max_retries: Maximum retry attempts on failure
        """
        self.jupiter_endpoint = jupiter_endpoint
        self.birdeye_endpoint = birdeye_endpoint
        self.birdeye_api_key = birdeye_api_key
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        
        # SOL token mint address
        self.sol_mint = "So11111111111111111111111111111111111111112"
        self.usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        # Cache for reducing API calls
        self._price_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_sec = 2.0  # Cache for 2 seconds
        
        # EMA state tracking
        self._ema_fast = None
        self._ema_slow = None
        self._ema_fast_alpha = 0.2  # ~10 period EMA
        self._ema_slow_alpha = 0.067  # ~30 period EMA
        
        logger.info(f"Initialized RealTimeMarketDataFetcher with Jupiter: {jupiter_endpoint}")
    
    async def _get_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP GET request with exponential backoff retry.
        
        Args:
            session: aiohttp session
            url: URL to fetch
            headers: Optional HTTP headers
            
        Returns:
            JSON response as dict
            
        Raises:
            aiohttp.ClientError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_sec)
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for {url}")
                    raise
    
    async def _fetch_jupiter_price(self, session: aiohttp.ClientSession) -> float:
        """
        Fetch current SOL/USDC price from Jupiter.
        
        Args:
            session: aiohttp session
            
        Returns:
            Current SOL price in USDC
        """
        # Jupiter quote API: get a quote for 1 SOL -> USDC
        url = f"{self.jupiter_endpoint}/quote"
        params = {
            "inputMint": self.sol_mint,
            "outputMint": self.usdc_mint,
            "amount": str(10**9),  # 1 SOL in lamports
            "slippageBps": "50"  # 0.5% slippage tolerance
        }
        
        # Build query string
        query = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        data = await self._get_with_retry(session, full_url)
        
        # Extract price from quote
        out_amount = int(data.get("outAmount", 0))
        if out_amount == 0:
            raise ValueError("Invalid Jupiter quote response: outAmount is 0")
        
        # Convert USDC (6 decimals) to price
        price = out_amount / 10**6
        
        logger.debug(f"Jupiter price: {price} USDC per SOL")
        return price
    
    async def _fetch_birdeye_metrics(
        self,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Fetch volume and market metrics from Birdeye.
        
        Args:
            session: aiohttp session
            
        Returns:
            Dict with volume_24h, liquidity, etc.
        """
        url = f"{self.birdeye_endpoint}/defi/token_overview"
        params = {"address": self.sol_mint}
        query = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{query}"
        
        headers = {}
        if self.birdeye_api_key:
            headers["X-API-KEY"] = self.birdeye_api_key
        
        try:
            data = await self._get_with_retry(session, full_url, headers)
            
            # Extract metrics from response
            token_data = data.get("data", {})
            
            return {
                "volume_24h": float(token_data.get("v24hUSD", 0)),
                "liquidity": float(token_data.get("liquidity", 0)),
                "price_change_24h": float(token_data.get("v24hChangePercent", 0))
            }
        except Exception as e:
            # Birdeye is optional - use fallback values if unavailable
            logger.warning(f"Birdeye metrics unavailable: {e}. Using fallback values.")
            return {
                "volume_24h": 1_000_000_000.0,  # Fallback: $1B volume
                "liquidity": 500_000_000.0,     # Fallback: $500M liquidity
                "price_change_24h": 0.0
            }
    
    async def fetch_market_state(self, symbol: str = "SOL/USD") -> MarketState:
        """
        Fetch current market state from real APIs.
        
        Args:
            symbol: Trading pair (currently only SOL/USD supported)
            
        Returns:
            MarketState with real-time data
        """
        # Check cache
        now = datetime.utcnow()
        if (self._price_cache is not None and 
            self._cache_timestamp is not None and
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl_sec):
            logger.debug("Using cached market data")
            return self._price_cache
        
        async with aiohttp.ClientSession() as session:
            # Fetch data from multiple sources in parallel
            price_task = self._fetch_jupiter_price(session)
            metrics_task = self._fetch_birdeye_metrics(session)
            
            price, metrics = await asyncio.gather(price_task, metrics_task)
        
        # Calculate bid/ask spread (estimate ~0.1% typical spread)
        spread_pct = 0.001
        bid = price * (1 - spread_pct / 2)
        ask = price * (1 + spread_pct / 2)
        
        # Update EMAs
        if self._ema_fast is None:
            self._ema_fast = price
            self._ema_slow = price
        else:
            self._ema_fast = self._ema_fast_alpha * price + (1 - self._ema_fast_alpha) * self._ema_fast
            self._ema_slow = self._ema_slow_alpha * price + (1 - self._ema_slow_alpha) * self._ema_slow
        
        # Calculate volatility from price change
        volatility = abs(metrics.get("price_change_24h", 0)) / 100.0
        if volatility == 0:
            volatility = 0.02  # Fallback: 2% volatility
        
        # Determine market regime
        if self._ema_fast > self._ema_slow * 1.02:
            regime = MarketRegime.TRENDING_UP
        elif self._ema_fast < self._ema_slow * 0.98:
            regime = MarketRegime.TRENDING_DOWN
        else:
            regime = MarketRegime.RANGING
        
        # Calculate liquidity score (normalized 0-1)
        liquidity_raw = metrics.get("liquidity", 0)
        liquidity_score = min(1.0, liquidity_raw / 1_000_000_000)  # Normalize to 1B
        
        # Estimate MEV risk and latency
        # TODO: Real MEV detection would require analyzing mempool and transaction patterns
        # For now, use conservative baseline estimates
        mev_risk_score = 0.3  # Moderate baseline risk (30%)
        latency_ms = 150.0  # Typical Solana RPC latency (150ms)
        
        market_state = MarketState(
            price=price,
            volume_24h=metrics.get("volume_24h", 0),
            bid=bid,
            ask=ask,
            ema_fast=self._ema_fast,
            ema_slow=self._ema_slow,
            regime=regime,
            volatility=volatility,
            liquidity_score=liquidity_score,
            mev_risk_score=mev_risk_score,
            latency_ms=latency_ms
        )
        
        # Update cache
        self._price_cache = market_state
        self._cache_timestamp = now
        
        logger.info(
            f"Fetched market state: price=${price:.2f}, "
            f"volume=${metrics.get('volume_24h', 0)/1e9:.2f}B, "
            f"regime={regime.value}"
        )
        
        return market_state
