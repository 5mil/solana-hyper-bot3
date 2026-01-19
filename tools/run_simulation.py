#!/usr/bin/env python3
"""
Run simulation CLI tool.

Runs MarketSimulator with MockQuoteClient for local testing.
"""
import asyncio
import argparse
import json
from pathlib import Path

from src.simulation.market_simulator import MarketSimulator
from src.adapters.mock_quote_client import MockMarketDataFetcher, MockQuoteClient
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.core.onflow_engine import OnflowEngine
from src.core.mdp_decision import MDPDecision
from src.execution.leverage_engine import LeverageEngine, LeverageConfig
from src.execution.twap_executor import TWAPExecutor
from src.simulation.paper_trader import PaperTrader


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run market simulation")
    parser.add_argument("--iterations", type=int, default=100, help="Number of iterations")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between iterations (seconds)")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--output", type=str, default="data/simulation_stats.json", help="Output path")
    parser.add_argument("--execute-trades", action="store_true", help="Execute trades (paper trading)")
    parser.add_argument("--min-confidence", type=float, default=0.75, help="Minimum confidence threshold")
    
    args = parser.parse_args()
    
    # Load config if provided
    config = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    
    # Setup components
    print("Setting up simulation components...")
    
    # Market data fetcher
    fetcher = MockMarketDataFetcher(
        base_price=config.get("market_simulation", {}).get("base_price", 100.0),
        price_volatility=config.get("market_simulation", {}).get("price_volatility", 0.02)
    )
    
    # Logic gate
    logic_gate = LogicGate()
    
    # Ensemble with engines
    ensemble = HyperEnsemble()
    onflow_engine = OnflowEngine()
    mdp_engine = MDPDecision()
    
    from src.core.types import ActionType
    
    ensemble.add_engine(
        "onflow",
        lambda ms: (ActionType.BUY, onflow_engine.suggest_allocation(ms))
    )
    ensemble.add_engine(
        "mdp",
        lambda ms: mdp_engine.select_action(ms, explore=True)
    )
    
    # Leverage engine
    leverage_config = LeverageConfig(
        max_position_pct=config.get("max_position_pct", 0.35),
        account_balance=config.get("initial_balance", 100.0)
    )
    leverage_engine = LeverageEngine(leverage_config)
    
    # Paper trader
    paper_trader = PaperTrader(
        initial_balance=config.get("initial_balance", 100.0)
    )
    
    # Create simulator
    simulator = MarketSimulator(
        market_data_fetcher=fetcher,
        logic_gate=logic_gate,
        ensemble=ensemble,
        leverage_engine=leverage_engine,
        paper_trader=paper_trader,
        min_confidence=args.min_confidence,
        execute_trades=args.execute_trades,
        metrics_path=args.output
    )
    
    print(f"Running simulation: {args.iterations} iterations, execute_trades={args.execute_trades}")
    print(f"Min confidence: {args.min_confidence}")
    print("-" * 60)
    
    # Run simulation
    report = await simulator.run_simulation(
        iterations=args.iterations,
        delay_sec=args.delay
    )
    
    # Display summary
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    
    decisions = report["decisions"]
    summary = report["trading_summary"]
    
    print(f"\nDecisions:")
    print(f"  Total: {decisions['total']}")
    print(f"  Approved: {decisions['approved']}")
    print(f"  Blocked: {decisions['blocked']}")
    print(f"  Approval Rate: {decisions['approval_rate']:.1f}%")
    
    print(f"\nTrading Summary:")
    print(f"  Total Trades: {summary['total_trades']}")
    print(f"  Win Rate: {summary['win_rate']:.1f}%")
    print(f"  Total P&L: ${summary['total_pnl']:.2f}")
    print(f"  Return: {summary['return_pct']:.2f}%")
    print(f"  Final Balance: ${summary['current_balance']:.2f}")
    print(f"  Total Fees: ${summary['total_fees']:.2f}")
    
    if summary['winning_trades'] > 0:
        print(f"  Avg Win: ${summary['avg_win']:.2f}")
    if summary['losing_trades'] > 0:
        print(f"  Avg Loss: ${summary['avg_loss']:.2f}")
    
    print(f"\nResults written to: {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
