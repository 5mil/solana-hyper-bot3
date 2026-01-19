"""Unit tests for LogicGate."""

import pytest
from src.core.logic_gate import LogicGate
from src.core.types import MarketState, BlockReason


def test_logic_gate_blocks_high_mev_risk():
    """Test that LogicGate blocks trades with high MEV risk."""
    gate = LogicGate(mev_risk_threshold=0.7)
    
    # Create market state with high MEV risk
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        mev_risk_score=0.8,  # Above threshold
        volume_24h=200000.0,
        latency_ms=100.0,
    )
    
    allowed, block_reasons = gate.check(market_state)
    
    assert not allowed, "Should block high MEV risk"
    assert BlockReason.HIGH_MEV_RISK in block_reasons, "Should report MEV risk"


def test_logic_gate_allows_low_mev_risk():
    """Test that LogicGate allows trades with low MEV risk."""
    gate = LogicGate(mev_risk_threshold=0.7)
    
    # Create market state with acceptable conditions
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        mev_risk_score=0.5,  # Below threshold
        volume_24h=200000.0,
        latency_ms=100.0,
        ema_short=100.0,
        ema_long=100.0,
    )
    
    allowed, block_reasons = gate.check(market_state)
    
    assert allowed, "Should allow low MEV risk"
    assert len(block_reasons) == 0, "Should have no block reasons"


def test_logic_gate_blocks_high_latency():
    """Test that LogicGate blocks trades with high latency."""
    gate = LogicGate(max_latency_ms=500.0)
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        mev_risk_score=0.3,
        volume_24h=200000.0,
        latency_ms=600.0,  # Above threshold
    )
    
    allowed, block_reasons = gate.check(market_state)
    
    assert not allowed, "Should block high latency"
    assert BlockReason.HIGH_LATENCY in block_reasons, "Should report latency"


def test_logic_gate_blocks_low_volume():
    """Test that LogicGate blocks trades with insufficient volume."""
    gate = LogicGate(min_volume_24h=100000.0)
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        mev_risk_score=0.3,
        volume_24h=50000.0,  # Below threshold
        latency_ms=100.0,
    )
    
    allowed, block_reasons = gate.check(market_state)
    
    assert not allowed, "Should block low volume"
    assert BlockReason.LOW_VOLUME in block_reasons, "Should report volume"


def test_logic_gate_blocks_price_jump():
    """Test that LogicGate blocks trades with large price jumps."""
    gate = LogicGate(max_price_jump_pct=5.0)
    
    market_state = MarketState(
        timestamp=1000000,
        price=110.0,  # 10% above EMA
        bid=109.0,
        ask=111.0,
        mev_risk_score=0.3,
        volume_24h=200000.0,
        latency_ms=100.0,
        ema_short=100.0,  # Base price
        ema_long=100.0,
    )
    
    allowed, block_reasons = gate.check(market_state)
    
    assert not allowed, "Should block price jump"
    assert BlockReason.PRICE_JUMP in block_reasons, "Should report price jump"


def test_logic_gate_multiple_violations():
    """Test that LogicGate reports multiple violations."""
    gate = LogicGate(
        mev_risk_threshold=0.5,
        max_latency_ms=300.0,
        min_volume_24h=100000.0,
    )
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        mev_risk_score=0.8,  # Violation
        volume_24h=50000.0,  # Violation
        latency_ms=500.0,  # Violation
    )
    
    allowed, block_reasons = gate.check(market_state)
    
    assert not allowed, "Should block multiple violations"
    assert len(block_reasons) >= 3, "Should report all violations"
    assert BlockReason.HIGH_MEV_RISK in block_reasons
    assert BlockReason.LOW_VOLUME in block_reasons
    assert BlockReason.HIGH_LATENCY in block_reasons
