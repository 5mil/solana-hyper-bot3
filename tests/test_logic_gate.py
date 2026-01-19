"""Unit tests for LogicGate."""
import pytest
from src.core.logic_gate import LogicGate
from src.core.types import MarketState, Action, ActionType


def test_logic_gate_blocks_high_mev_risk():
    """Test that LogicGate blocks actions when MEV risk is too high."""
    gate = LogicGate(max_mev_risk=0.5)
    
    # Create market state with high MEV risk
    market_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        mev_risk_score=0.8  # High MEV risk
    )
    
    action = Action(
        action_type=ActionType.BUY,
        size=10.0,
        confidence=0.9
    )
    
    result = gate.check(market_state, action)
    
    assert not result.allowed
    assert len(result.reasons) > 0
    assert any("MEV risk" in reason for reason in result.reasons)
    assert result.risk_score > 0


def test_logic_gate_allows_good_conditions():
    """Test that LogicGate allows actions in good conditions."""
    gate = LogicGate()
    
    # Create market state with good conditions
    market_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.9,
        ask=100.1,
        mev_risk_score=0.2,
        latency_ms=100.0,
        liquidity_score=0.9
    )
    
    action = Action(
        action_type=ActionType.BUY,
        size=10.0,
        confidence=0.9
    )
    
    result = gate.check(market_state, action)
    
    assert result.allowed
    assert len(result.reasons) == 0


def test_logic_gate_blocks_high_latency():
    """Test that LogicGate blocks actions when latency is too high."""
    gate = LogicGate(max_latency_ms=200.0)
    
    market_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        latency_ms=600.0  # High latency
    )
    
    action = Action(
        action_type=ActionType.BUY,
        size=10.0,
        confidence=0.9
    )
    
    result = gate.check(market_state, action)
    
    assert not result.allowed
    assert any("Latency" in reason for reason in result.reasons)


def test_logic_gate_blocks_low_volume():
    """Test that LogicGate blocks actions when volume is too low."""
    gate = LogicGate(min_volume_24h=5000.0)
    
    market_state = MarketState(
        price=100.0,
        volume_24h=1000.0,  # Low volume
        bid=99.5,
        ask=100.5
    )
    
    action = Action(
        action_type=ActionType.BUY,
        size=10.0,
        confidence=0.9
    )
    
    result = gate.check(market_state, action)
    
    assert not result.allowed
    assert any("Volume" in reason for reason in result.reasons)
