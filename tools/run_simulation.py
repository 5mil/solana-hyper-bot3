#!/usr/bin/env python3
"""Run simulation locally for testing.

CLI tool to run MarketSimulator with MockQuoteClient for local testing.
"""

import sys
import json
import time
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.types import MarketState
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.core.onflow_engine import OnflowEngine
from src.core.mdp_decision import MDPDecision
from src.simulation.market_simulator import MarketSimulator
from src.adapters.mock_quote_client import MockQuoteClient


class SimpleMockFetcher:
    """Simple mock market data fetcher with random walk."""
    
    def __init__(self, base_price: float = 100.0, volatility: float = 0.02):
        """Initialize mock fetcher.
        
        Args:
            base_price: Starting price
            volatility: Price volatility
        """
        self.base_price = base_price
        self.volatility = volatility
        self.current_price = base_price
        self.call_count = 0
    
    def fetch_market_state(self, symbol: str = "SOL/USD") -> MarketState:
        """Fetch mock market state with random walk.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Mock MarketState
        """
        import random
        
        self.call_count += 1
        
        # Random walk
        change = random.gauss(0, self.volatility)
        self.current_price *= (1 + change)
        
        # Prevent negative prices
        self.current_price = max(self.current_price, 1.0)
        
        price = self.current_price
        spread = price * 0.001  # 10 bps spread
        
        return MarketState(
            timestamp=int(time.time() * 1000),
            symbol=symbol,
            price=price,
            bid=price - spread/2,
            ask=price + spread/2,
            volume_24h=random.uniform(100000, 500000),
            ema_short=price * 0.99,  # Slight deviation
            ema_long=price * 0.98,
            volatility=self.volatility,
            spread_bps=10.0,
            latency_ms=random.uniform(50, 200),
            mev_risk_score=random.uniform(0.1, 0.5),
            liquidity_depth=random.uniform(50000, 200000),
        )
    
    async def fetch_market_state_async(self, symbol: str = "SOL/USD") -> MarketState:
        """Fetch market state asynchronously."""
        return self.fetch_market_state(symbol)


def load_config(config_path: str = "config/simulation_config.json") -> dict:
    """Load simulation configuration.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Config file {config_path} not found, using defaults")
        return {
            "execute_trades": False,
            "iterations": 100,
            "delay_sec": 0.1,
            "output_report": "data/simulation_report.json",
        }


def setup_ensemble() -> HyperEnsemble:
    """Set up HyperEnsemble with decision engines.
    
    Returns:
        Configured HyperEnsemble
    """
    # Create engines
    onflow = OnflowEngine()
    mdp = MDPDecision()
    
    # Create ensemble
    ensemble = HyperEnsemble(min_confidence=0.75)
    
    # Add engines
    ensemble.add_engine("onflow", lambda ms: onflow.get_allocation_fraction(0.8))
    ensemble.add_engine("mdp", lambda ms: mdp.select_action(ms, confidence=0.7))
    
    # Note: The lambda wrappers above are simplified
    # In production, these would return proper Action objects
    
    return ensemble


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run local simulation")
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Number of iterations (overrides config)",
    )
    parser.add_argument(
        "--execute-trades",
        action="store_true",
        help="Enable trade execution (overrides config)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output report path (overrides config)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/simulation_config.json",
        help="Config file path",
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Override with CLI args
    iterations = args.iterations or config.get("iterations", 100)
    execute_trades = args.execute_trades or config.get("execute_trades", False)
    output_path = args.output or config.get("output_report", "data/simulation_report.json")
    delay_sec = config.get("delay_sec", 0.1)
    
    print("=" * 60)
    print("Solana Hyper-Accumulation Bot v3.0 - Local Simulation")
    print("=" * 60)
    print(f"Iterations: {iterations}")
    print(f"Execute trades: {execute_trades}")
    print(f"Output: {output_path}")
    print(f"Delay: {delay_sec}s")
    print("=" * 60)
    print()
    
    # Create components
    fetcher = SimpleMockFetcher(base_price=100.0, volatility=0.02)
    logic_gate = LogicGate()
    
    # Create simulator
    simulator = MarketSimulator(
        market_fetcher=fetcher,
        logic_gate=logic_gate,
        initial_capital=100.0,
        execute_trades=execute_trades,
        min_confidence=0.75,
    )
    
    # Run simulation
    print("Running simulation...")
    start_time = time.time()
    
    summary = simulator.run(
        iterations=iterations,
        delay_sec=delay_sec,
        output_path=output_path,
    )
    
    elapsed = time.time() - start_time
    
    # Print summary
    print()
    print("=" * 60)
    print("Simulation Complete")
    print("=" * 60)
    print(f"Total iterations: {summary['total_iterations']}")
    print(f"Decisions made: {summary['decisions_made']}")
    print(f"Trades executed: {summary['trades_executed']}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print()
    
    if execute_trades:
        perf = summary['trading_performance']
        print("Trading Performance:")
        print(f"  Total trades: {perf['total_trades']}")
        print(f"  Winning trades: {perf['winning_trades']}")
        print(f"  Losing trades: {perf['losing_trades']}")
        print(f"  Win rate: {perf['win_rate']:.1%}")
        print(f"  Total PnL: ${perf['total_pnl']:.2f}")
        print(f"  Return: {perf['return_pct']:.1f}%")
        print(f"  Avg PnL/trade: ${perf['avg_pnl']:.2f}")
        print(f"  Final capital: ${perf['current_capital']:.2f}")
    
    print()
    print(f"Report saved to: {output_path}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
