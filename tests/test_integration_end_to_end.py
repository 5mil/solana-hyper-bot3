"""Integration tests for end-to-end simulation."""
import pytest
from src.simulation.market_simulator import MarketSimulator
from src.adapters.mock_quote_client import MockMarketDataFetcher


@pytest.mark.asyncio
async def test_integration_market_simulator_basic():
    """Test that MarketSimulator runs end-to-end with mock fetcher."""
    fetcher = MockMarketDataFetcher(base_price=100.0)
    
    simulator = MarketSimulator(
        market_data_fetcher=fetcher,
        min_confidence=0.5,  # Lower threshold for testing
        execute_trades=True,
        metrics_path="data/test_simulation.json"
    )
    
    # Run a few iterations
    report = await simulator.run_simulation(
        iterations=5,
        delay_sec=0.1  # Fast for testing
    )
    
    assert report is not None
    assert "simulation_config" in report
    assert "trading_summary" in report
    assert report["simulation_config"]["iterations"] == 5


@pytest.mark.asyncio
async def test_integration_market_simulator_generates_output():
    """Test that MarketSimulator generates output summary."""
    fetcher = MockMarketDataFetcher(base_price=100.0)
    
    simulator = MarketSimulator(
        market_data_fetcher=fetcher,
        min_confidence=0.6,
        execute_trades=True,
        metrics_path="data/test_output.json"
    )
    
    report = await simulator.run_simulation(
        iterations=10,
        delay_sec=0.05
    )
    
    # Check report structure
    assert "decisions" in report
    assert "trading_summary" in report
    assert "iteration_reports" in report
    
    # Check decisions were made
    assert report["decisions"]["total"] > 0
    
    # Check trading summary exists
    summary = report["trading_summary"]
    assert "total_trades" in summary
    assert "current_balance" in summary


@pytest.mark.asyncio
async def test_integration_market_simulator_respects_execute_flag():
    """Test that execute_trades flag is respected."""
    fetcher = MockMarketDataFetcher(base_price=100.0)
    
    # Without execution
    sim_no_exec = MarketSimulator(
        market_data_fetcher=fetcher,
        execute_trades=False,
        metrics_path="data/test_no_exec.json"
    )
    
    report_no_exec = await sim_no_exec.run_simulation(
        iterations=5,
        delay_sec=0.05
    )
    
    # Should have no trades
    assert report_no_exec["trading_summary"]["total_trades"] == 0
    
    # With execution
    sim_with_exec = MarketSimulator(
        market_data_fetcher=fetcher,
        min_confidence=0.5,  # Lower to increase trades
        execute_trades=True,
        metrics_path="data/test_with_exec.json"
    )
    
    report_with_exec = await sim_with_exec.run_simulation(
        iterations=10,
        delay_sec=0.05
    )
    
    # May have trades (depending on decisions)
    assert "total_trades" in report_with_exec["trading_summary"]


@pytest.mark.asyncio
async def test_integration_iteration_report_structure():
    """Test that iteration reports have correct structure."""
    fetcher = MockMarketDataFetcher(base_price=100.0)
    
    simulator = MarketSimulator(
        market_data_fetcher=fetcher,
        min_confidence=0.5,
        execute_trades=True,
        metrics_path="data/test_iteration.json"
    )
    
    report = await simulator.run_simulation(
        iterations=3,
        delay_sec=0.05
    )
    
    iteration_reports = report["iteration_reports"]
    
    assert len(iteration_reports) == 3
    
    for iter_report in iteration_reports:
        assert "iteration" in iter_report
        assert "status" in iter_report
        # Status should be one of the valid types
        assert iter_report["status"] in [
            "blocked_by_logic_gate",
            "blocked_by_low_confidence",
            "executed",
            "simulated_decision"
        ]
