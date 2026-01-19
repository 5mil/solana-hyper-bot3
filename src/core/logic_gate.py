"""Logic Gate: Deterministic axiomatic filter for market conditions.

The LogicGate implements hard rule-based filters that can block trades based on
MEV risk, latency, price jumps, EMA deviation, and volume thresholds. This is
the first line of defense before ensemble decision-making.
"""

from typing import Tuple, List
from src.core.types import MarketState, BlockReason


class LogicGate:
    """Deterministic rule-based filter for market conditions.
    
    Implements hard constraints that must be satisfied before allowing trades:
    - MEV risk threshold
    - Maximum latency tolerance
    - Price jump detection
    - EMA deviation limits
    - Minimum volume requirements
    
    Attributes:
        mev_risk_threshold: Maximum acceptable MEV risk score (0-1)
        max_latency_ms: Maximum acceptable latency in milliseconds
        max_price_jump_pct: Maximum acceptable price jump percentage
        max_ema_deviation_pct: Maximum deviation from EMA percentage
        min_volume_24h: Minimum 24h volume required
    """
    
    def __init__(
        self,
        mev_risk_threshold: float = 0.7,
        max_latency_ms: float = 500.0,
        max_price_jump_pct: float = 5.0,
        max_ema_deviation_pct: float = 10.0,
        min_volume_24h: float = 100000.0,
    ):
        """Initialize LogicGate with threshold parameters.
        
        Args:
            mev_risk_threshold: Max MEV risk (default: 0.7)
            max_latency_ms: Max latency in ms (default: 500)
            max_price_jump_pct: Max price jump % (default: 5.0)
            max_ema_deviation_pct: Max EMA deviation % (default: 10.0)
            min_volume_24h: Min 24h volume (default: 100000)
        """
        self.mev_risk_threshold = mev_risk_threshold
        self.max_latency_ms = max_latency_ms
        self.max_price_jump_pct = max_price_jump_pct
        self.max_ema_deviation_pct = max_ema_deviation_pct
        self.min_volume_24h = min_volume_24h
    
    def check(self, market_state: MarketState) -> Tuple[bool, List[BlockReason]]:
        """Check if market state passes all logic gate filters.
        
        Args:
            market_state: Current market state to evaluate
            
        Returns:
            Tuple of (allowed: bool, block_reasons: List[BlockReason])
            If allowed is True, block_reasons will be empty.
            If allowed is False, block_reasons contains why it was blocked.
        """
        block_reasons: List[BlockReason] = []
        
        # Check MEV risk
        if market_state.mev_risk_score > self.mev_risk_threshold:
            block_reasons.append(BlockReason.HIGH_MEV_RISK)
        
        # Check latency
        if market_state.latency_ms > self.max_latency_ms:
            block_reasons.append(BlockReason.HIGH_LATENCY)
        
        # Check volume
        if market_state.volume_24h < self.min_volume_24h:
            block_reasons.append(BlockReason.LOW_VOLUME)
        
        # Check price jump (compare current price to EMA if available)
        if market_state.ema_short is not None:
            price_deviation_pct = abs(
                (market_state.price - market_state.ema_short) / market_state.ema_short * 100
            )
            if price_deviation_pct > self.max_price_jump_pct:
                block_reasons.append(BlockReason.PRICE_JUMP)
        
        # Check EMA deviation (short vs long)
        if market_state.ema_short is not None and market_state.ema_long is not None:
            ema_deviation_pct = abs(
                (market_state.ema_short - market_state.ema_long) / market_state.ema_long * 100
            )
            if ema_deviation_pct > self.max_ema_deviation_pct:
                block_reasons.append(BlockReason.EMA_DEVIATION)
        
        allowed = len(block_reasons) == 0
        return allowed, block_reasons
