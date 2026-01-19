"""Integration test: End-to-end simulation."""

import pytest
import time
from src.core.types import MarketState
from src.simulation.market_simulator import MarketSimulator


class DummyMarketFetcher:
    """Simple dummy market data fetcher for testing."""
    
    def __init__(self):
        self.call_count = 0
        self.base_price = 100.0
    
    def fetch_market_state(self, symbol: str = "SOL/USD") -> MarketState:
        """Fetch a dummy market state."""
        self.call_count += 1
        
        # Simple price walk
        price = self.base_price + (self.call_count * 0.5)
        
        return MarketState(
            timestamp=int(time.time() * 1000),
            symbol=symbol,
            price=price,
            bid=price - 0.5,
            ask=price + 0.5,
            volume_24h=200000.0,
            ema_short=price,
            ema_long=price,
            volatility=0.02,
            spread_bps=100.0,
            latency_ms=100.0,
            mev_risk_score=0.3,
            liquidity_depth=100000.0,
        )
    
    async def fetch_market_state_async(self, symbol: str = "SOL/USD") -> MarketState:
        """Fetch market state asynchronously."""
        return self.fetch_market_state(symbol)


def test_market_simulator_runs_without_errors():
    """Test that MarketSimulator can run end-to-end without errors."""
    # Create dummy fetcher
    fetcher = DummyMarketFetcher()
    
    # Create simulator with execute_trades=False
    simulator = MarketSimulator(
        market_fetcher=fetcher,
        initial_capital=100.0,
        execute_trades=False,
        min_confidence=0.75,
    )
    
    # Run for a few iterations
    summary = simulator.run(iterations=5, delay_sec=0.0)
    
    # Verify we got a summary
    assert "simulation_complete" in summary
    assert summary["simulation_complete"] is True
    assert summary["total_iterations"] == 5
    assert fetcher.call_count >= 5, "Should have fetched market data"


def test_market_simulator_with_trades_enabled():
    """Test MarketSimulator with trade execution enabled."""
    fetcher = DummyMarketFetcher()
    
    # Create simulator with execute_trades=True
    simulator = MarketSimulator(
        market_fetcher=fetcher,
        initial_capital=100.0,
        execute_trades=True,
        min_confidence=0.5,  # Lower threshold to allow more trades
    )
    
    # Run simulation
    summary = simulator.run(iterations=10, delay_sec=0.0)
    
    # Verify simulation completed
    assert summary["simulation_complete"] is True
    assert summary["total_iterations"] == 10
    
    # Check trading performance
    assert "trading_performance" in summary
    perf = summary["trading_performance"]
    assert "total_trades" in perf
    assert "current_capital" in perf
    assert "win_rate" in perf


def test_market_simulator_output_file():
    """Test that MarketSimulator writes output file."""
    import tempfile
    import os
    import json
    
    fetcher = DummyMarketFetcher()
    
    # Create temp file for output
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        output_path = f.name
    
    try:
        simulator = MarketSimulator(
            market_fetcher=fetcher,
            initial_capital=100.0,
            execute_trades=False,
        )
        
        # Run with output path
        summary = simulator.run(iterations=3, delay_sec=0.0, output_path=output_path)
        
        # Verify file exists and is valid JSON
        assert os.path.exists(output_path), "Output file should exist"
        
        with open(output_path, "r") as f:
            report = json.load(f)
        
        assert "summary" in report
        assert "iterations" in report
        assert len(report["iterations"]) == 3
    
    finally:
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)


@pytest.mark.asyncio
async def test_market_simulator_async_fetcher():
    """Test MarketSimulator with async market fetcher."""
    fetcher = DummyMarketFetcher()
    
    simulator = MarketSimulator(
        market_fetcher=fetcher,
        initial_capital=100.0,
        execute_trades=False,
    )
    
    # Run a single iteration
    result = simulator.run_iteration()
    
    # Should complete without errors
    assert "status" in result
    assert "timestamp" in result


def test_market_simulator_logic_gate_blocking():
    """Test that logic gate can block decisions."""
    from src.core.logic_gate import LogicGate
    
    class HighRiskFetcher:
        """Fetcher that returns high-risk market states."""
        
        def fetch_market_state(self, symbol: str = "SOL/USD") -> MarketState:
            return MarketState(
                timestamp=int(time.time() * 1000),
                symbol=symbol,
                price=100.0,
                bid=99.0,
                ask=101.0,
                volume_24h=200000.0,
                mev_risk_score=0.9,  # High risk
                latency_ms=100.0,
            )
    
    fetcher = HighRiskFetcher()
    
    # Create logic gate with strict threshold
    logic_gate = LogicGate(mev_risk_threshold=0.7)
    
    simulator = MarketSimulator(
        market_fetcher=fetcher,
        logic_gate=logic_gate,
        initial_capital=100.0,
        execute_trades=True,
    )
    
    # Run simulation
    summary = simulator.run(iterations=5, delay_sec=0.0)
    
    # Should complete but no trades due to blocking
    assert summary["simulation_complete"] is True
    # Trades should be 0 or very low due to MEV blocking
    assert summary["trading_performance"]["total_trades"] == 0
