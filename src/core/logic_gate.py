"""
LogicGate: Deterministic axiomatic filter for market actions.

Implements rule-based filters to block actions based on MEV risk, latency,
price jumps, EMA deviations, and volume conditions.
"""
from typing import List
from src.core.types import MarketState, Action, FilterResult


class LogicGate:
    """
    Deterministic filter that blocks actions based on risk rules.
    
    The LogicGate implements axiomatic rules to prevent actions in
    high-risk market conditions. All rules are deterministic and
    should be tuned based on market characteristics.
    """
    
    def __init__(
        self,
        max_mev_risk: float = 0.7,
        max_latency_ms: float = 500.0,
        max_price_jump_pct: float = 5.0,
        max_ema_deviation_pct: float = 10.0,
        min_volume_24h: float = 1000.0
    ):
        """
        Initialize LogicGate with risk thresholds.
        
        Args:
            max_mev_risk: Maximum MEV risk score (0-1) to allow
            max_latency_ms: Maximum latency in milliseconds
            max_price_jump_pct: Maximum price jump as percentage
            max_ema_deviation_pct: Maximum deviation from EMA as percentage
            min_volume_24h: Minimum 24h volume required
        """
        self.max_mev_risk = max_mev_risk
        self.max_latency_ms = max_latency_ms
        self.max_price_jump_pct = max_price_jump_pct
        self.max_ema_deviation_pct = max_ema_deviation_pct
        self.min_volume_24h = min_volume_24h
    
    def check(self, market_state: MarketState, action: Action) -> FilterResult:
        """
        Check if an action should be allowed or blocked.
        
        Args:
            market_state: Current market state
            action: Proposed action
            
        Returns:
            FilterResult with allowed status and reasons
        """
        reasons: List[str] = []
        risk_score = 0.0
        
        # MEV risk check
        if market_state.mev_risk_score > self.max_mev_risk:
            reasons.append(
                f"MEV risk too high: {market_state.mev_risk_score:.2f} > {self.max_mev_risk}"
            )
            risk_score += 0.3
        
        # Latency check
        if market_state.latency_ms > self.max_latency_ms:
            reasons.append(
                f"Latency too high: {market_state.latency_ms:.0f}ms > {self.max_latency_ms}ms"
            )
            risk_score += 0.2
        
        # Volume check
        if market_state.volume_24h < self.min_volume_24h:
            reasons.append(
                f"Volume too low: {market_state.volume_24h:.0f} < {self.min_volume_24h}"
            )
            risk_score += 0.2
        
        # EMA deviation check (if EMA data available)
        if market_state.ema_fast is not None and market_state.ema_slow is not None:
            ema_avg = (market_state.ema_fast + market_state.ema_slow) / 2
            deviation_pct = abs(market_state.price - ema_avg) / ema_avg * 100
            
            if deviation_pct > self.max_ema_deviation_pct:
                reasons.append(
                    f"Price deviation from EMA too high: {deviation_pct:.1f}% > {self.max_ema_deviation_pct}%"
                )
                risk_score += 0.2
        
        # Spread/price jump check (simplified using bid-ask spread)
        spread_pct = (market_state.ask - market_state.bid) / market_state.bid * 100
        if spread_pct > self.max_price_jump_pct:
            reasons.append(
                f"Bid-ask spread too wide: {spread_pct:.2f}% > {self.max_price_jump_pct}%"
            )
            risk_score += 0.1
        
        allowed = len(reasons) == 0
        risk_score = min(risk_score, 1.0)
        
        return FilterResult(
            allowed=allowed,
            reasons=reasons,
            risk_score=risk_score
        )
