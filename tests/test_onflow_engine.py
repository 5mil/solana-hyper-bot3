"""Unit tests for OnflowEngine."""

import pytest
from src.core.onflow_engine import OnflowEngine


def test_onflow_engine_initialization():
    """Test OnflowEngine initializes with correct defaults."""
    engine = OnflowEngine()
    
    assert engine.alpha == 0.3
    assert engine.min_allocation == 0.05
    assert engine.max_allocation == 0.35
    assert engine.ewma_win_rate == 0.5  # Neutral start
    assert engine.trade_count == 0


def test_onflow_engine_update_winning_trade():
    """Test that OnflowEngine updates correctly on winning trade."""
    engine = OnflowEngine(alpha=0.5)
    
    # Record a winning trade
    engine.update(trade_return=0.1)  # 10% profit
    
    assert engine.trade_count == 1
    assert engine.ewma_win_rate > 0.5, "Win rate should increase"
    assert engine.ewma_avg_return > 0, "Average return should be positive"


def test_onflow_engine_update_losing_trade():
    """Test that OnflowEngine updates correctly on losing trade."""
    engine = OnflowEngine(alpha=0.5)
    
    # Record a losing trade
    engine.update(trade_return=-0.05)  # -5% loss
    
    assert engine.trade_count == 1
    assert engine.ewma_win_rate < 0.5, "Win rate should decrease"
    assert engine.ewma_avg_return < 0, "Average return should be negative"


def test_onflow_engine_allocation_within_bounds():
    """Test that allocation fraction stays within min/max bounds."""
    engine = OnflowEngine(min_allocation=0.05, max_allocation=0.35)
    
    # Update with several winning trades
    for _ in range(10):
        engine.update(trade_return=0.1)
    
    # Get allocation with high confidence
    allocation = engine.get_allocation_fraction(confidence=1.0)
    
    assert allocation >= engine.min_allocation, "Should respect minimum"
    assert allocation <= engine.max_allocation, "Should respect maximum"


def test_onflow_engine_min_allocation_on_insufficient_data():
    """Test that engine returns min allocation when insufficient data."""
    engine = OnflowEngine(min_allocation=0.05)
    
    # No trades yet
    allocation = engine.get_allocation_fraction(confidence=1.0)
    
    assert allocation == engine.min_allocation, "Should return min with no data"


def test_onflow_engine_confidence_scaling():
    """Test that confidence scales allocation appropriately."""
    engine = OnflowEngine()
    
    # Add some trade history
    for _ in range(5):
        engine.update(trade_return=0.1)
    
    # Get allocations with different confidence levels
    alloc_high = engine.get_allocation_fraction(confidence=1.0)
    alloc_low = engine.get_allocation_fraction(confidence=0.5)
    
    assert alloc_low < alloc_high, "Lower confidence should yield lower allocation"


def test_onflow_engine_state_export():
    """Test that engine can export its state."""
    engine = OnflowEngine(alpha=0.3)
    
    engine.update(trade_return=0.05)
    engine.update(trade_return=-0.02)
    
    state = engine.get_state()
    
    assert "ewma_win_rate" in state
    assert "ewma_avg_return" in state
    assert "trade_count" in state
    assert state["trade_count"] == 2
    assert state["alpha"] == 0.3


def test_onflow_engine_multiple_trades():
    """Test engine behavior over multiple trades."""
    engine = OnflowEngine(alpha=0.3)
    
    # Simulate mixed performance
    trades = [0.1, -0.05, 0.08, -0.03, 0.12, 0.05, -0.02]
    
    for ret in trades:
        engine.update(trade_return=ret)
    
    assert engine.trade_count == len(trades)
    
    # With mostly winning trades, allocation should be reasonable
    allocation = engine.get_allocation_fraction(confidence=0.8)
    assert engine.min_allocation <= allocation <= engine.max_allocation
