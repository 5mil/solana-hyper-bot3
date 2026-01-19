"""Unit tests for OnflowEngine."""
import pytest
from src.core.onflow_engine import OnflowEngine
from src.core.types import MarketState


def test_onflow_engine_returns_allocation_within_bounds():
    """Test that OnflowEngine returns allocation within configured bounds."""
    engine = OnflowEngine(
        max_allocation=0.5,
        min_allocation=0.01
    )
    
    market_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        volatility=0.02
    )
    
    allocation = engine.suggest_allocation(market_state)
    
    assert 0.01 <= allocation <= 0.5
    assert isinstance(allocation, float)


def test_onflow_engine_updates_with_wins():
    """Test that OnflowEngine updates EWMA estimates with winning trades."""
    engine = OnflowEngine()
    
    # Record winning trades
    engine.update(won=True, return_pct=5.0, volatility=0.02)
    engine.update(won=True, return_pct=3.0, volatility=0.02)
    
    assert engine.ewma_win_rate is not None
    assert engine.ewma_win_rate > 0.5
    assert engine.ewma_avg_return > 0
    assert engine.trade_count == 2


def test_onflow_engine_reduces_allocation_with_losses():
    """Test that OnflowEngine reduces allocation after losses."""
    engine = OnflowEngine(max_allocation=0.5)
    
    market_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        volatility=0.02
    )
    
    # Get initial allocation
    initial_alloc = engine.suggest_allocation(market_state)
    
    # Record losses
    engine.update(won=False, return_pct=-2.0, volatility=0.02)
    engine.update(won=False, return_pct=-3.0, volatility=0.02)
    
    # Get new allocation
    new_alloc = engine.suggest_allocation(market_state)
    
    # Should reduce allocation after losses
    assert new_alloc <= initial_alloc


def test_onflow_engine_initial_state():
    """Test that OnflowEngine starts with sensible defaults."""
    engine = OnflowEngine()
    
    assert engine.ewma_win_rate is None
    assert engine.ewma_avg_return is None
    assert engine.trade_count == 0


def test_onflow_engine_high_volatility_reduces_allocation():
    """Test that high volatility reduces allocation."""
    engine = OnflowEngine(max_allocation=0.5)
    
    # Low volatility
    low_vol_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.9,
        ask=100.1,
        volatility=0.01
    )
    
    # High volatility
    high_vol_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        volatility=0.1
    )
    
    # Update with winning history
    engine.update(won=True, return_pct=5.0, volatility=0.02)
    engine.update(won=True, return_pct=5.0, volatility=0.02)
    
    low_vol_alloc = engine.suggest_allocation(low_vol_state)
    high_vol_alloc = engine.suggest_allocation(high_vol_state)
    
    # High volatility should reduce allocation
    assert high_vol_alloc < low_vol_alloc
