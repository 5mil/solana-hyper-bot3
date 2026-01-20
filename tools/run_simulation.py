#!/usr/bin/env python3
"""
Enhanced Run simulation CLI tool with production-ready features.

Runs MarketSimulator with real-time or mock data, with optional GUI.
Features:
- Real-time market data from Jupiter/Birdeye APIs
- Mock data simulation for testing
- Interactive GUI dashboard (toggleable)
- Input validation and error handling
- Structured logging
- Progress tracking
- Metrics persistence
"""
import asyncio
import argparse
import json
import logging
import sys
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# Third-party imports
try:
    import tqdm
except ImportError:
    print("Warning: tqdm not found. Install with: pip install tqdm")
    tqdm = None

from src.simulation.market_simulator import MarketSimulator
from src.adapters.mock_quote_client import MockMarketDataFetcher, MockQuoteClient
from src.adapters.realtime_market_data import RealTimeMarketDataFetcher
from src.adapters.jupiter_quote_client import JupiterQuoteClient
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.core.onflow_engine import OnflowEngine
from src.core.mdp_decision import MDPDecision
from src.execution.leverage_engine import LeverageEngine, LeverageConfig
from src.execution.twap_executor import TWAPExecutor
from src.simulation.paper_trader import PaperTrader

# Optional GUI import
try:
    from src.gui.bot_dashboard import BotGUI
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("Warning: GUI not available (tkinter not installed). Use --gui flag only if tkinter is available.")


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure structured logging."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('simulation.log')
        ]
    )
    
    return logging.getLogger(__name__)


# ============================================================================
# MAIN SIMULATION RUNNER
# ============================================================================

async def run_simulation(
    iterations: int,
    delay_sec: float,
    execute_trades: bool,
    min_confidence: float,
    output_path: str,
    use_real_time: bool,
    show_gui: bool,
    verbose: bool
):
    """
    Run trading simulation.
    
    Args:
        iterations: Number of simulation cycles
        delay_sec: Delay between cycles
        execute_trades: Whether to execute trades (vs. just decisions)
        min_confidence: Minimum confidence threshold
        output_path: Path to write metrics
        use_real_time: Use real-time APIs instead of mock data
        show_gui: Show GUI dashboard
        verbose: Verbose logging
    """
    logger = setup_logging(verbose)
    
    # Initialize GUI if requested
    gui = None
    if show_gui:
        if not GUI_AVAILABLE:
            logger.error("GUI requested but tkinter is not available. Install tkinter to use --gui flag.")
            print("ERROR: GUI not available. Run without --gui flag or install tkinter.")
            return
        
        logger.info("Initializing GUI dashboard...")
        gui = BotGUI()
        gui.start_in_thread()
        logger.info("GUI started in background thread")
    
    # Initialize market data fetcher
    if use_real_time:
        logger.info("Using REAL-TIME market data from Jupiter/Birdeye APIs")
        if gui:
            gui.update("log", {"message": "[INFO] Using real-time API data\n"})
        
        fetcher = RealTimeMarketDataFetcher(
            jupiter_endpoint=os.getenv("JUPITER_ENDPOINT", "https://quote-api.jup.ag/v6"),
            birdeye_api_key=os.getenv("BIRDEYE_API_KEY")
        )
    else:
        logger.info("Using MOCK market data (synthetic random walk)")
        if gui:
            gui.update("log", {"message": "[INFO] Using mock simulated data\n"})
        
        fetcher = MockMarketDataFetcher()
    
    # Create config
    config = {
        "min_confidence": min_confidence,
        "max_position_pct": 0.35,
        "initial_balance": 100.0
    }
    
    # Initialize simulator
    simulator = MarketSimulator(
        market_data_fetcher=fetcher,
        config=config
    )
    
    logger.info(
        f"Starting simulation: {iterations} iterations, "
        f"delay={delay_sec}s, execute_trades={execute_trades}, "
        f"min_confidence={min_confidence}"
    )
    
    # Run simulation
    try:
        if tqdm:
            iterator = tqdm.tqdm(range(iterations), desc="Simulation Progress")
        else:
            iterator = range(iterations)
        
        for i in iterator:
            cycle_num = i + 1
            
            # Update GUI status
            if gui:
                gui.update("status", {
                    "status": "RUNNING",
                    "cycle": cycle_num
                })
            
            # Run one cycle
            report = await simulator.run_cycle(
                symbol="SOL/USD",
                execute_trades=execute_trades
            )
            
            # Update GUI with market data
            if gui and "market_state" in report:
                ms = report["market_state"]
                gui.update("status", {
                    "price": ms.price,
                    "regime": ms.regime.value
                })
            
            # Update GUI with trade data
            if gui and report.get("status") == "paper_trade":
                # Calculate P&L for this trade (simplified)
                pnl = report.get("pnl", 0)
                
                gui.update("trade", {
                    "action": report.get("action", "HOLD"),
                    "size": report.get("size", 0),
                    "price": report.get("price", 0),
                    "pnl": pnl,
                    "balance": simulator.paper_trader.balance if hasattr(simulator, 'paper_trader') else 100.0
                })
            
            # Update GUI metrics
            if gui:
                summary = simulator.get_summary()
                gui.update("metrics", {
                    "balance": summary.get("final_balance", 100.0),
                    "pnl": summary.get("total_pnl", 0),
                    "trades": summary.get("total_trades", 0),
                    "winning_trades": summary.get("winning_trades", 0),
                    "blocked": summary.get("blocked_count", 0),
                    "cycles": cycle_num
                })
            
            # Log progress
            if cycle_num % 10 == 0:
                summary = simulator.get_summary()
                logger.info(
                    f"Cycle {cycle_num}/{iterations}: "
                    f"Balance=${summary.get('final_balance', 0):.2f}, "
                    f"Trades={summary.get('total_trades', 0)}, "
                    f"Win Rate={summary.get('win_rate_pct', 0):.1f}%"
                )
            
            # Delay
            await asyncio.sleep(delay_sec)
        
        # Final summary
        summary = simulator.get_summary()
        logger.info("\n" + "="*60)
        logger.info("SIMULATION COMPLETE")
        logger.info("="*60)
        logger.info(f"Total Cycles: {iterations}")
        logger.info(f"Total Trades: {summary.get('total_trades', 0)}")
        logger.info(f"Winning Trades: {summary.get('winning_trades', 0)}")
        logger.info(f"Win Rate: {summary.get('win_rate_pct', 0):.2f}%")
        logger.info(f"Final Balance: ${summary.get('final_balance', 0):.2f}")
        logger.info(f"Total P&L: ${summary.get('total_pnl', 0):+.2f}")
        logger.info(f"Return: {summary.get('return_pct', 0):+.2f}%")
        logger.info(f"Max Drawdown: {summary.get('max_drawdown_pct', 0):.2f}%")
        logger.info(f"Blocked/Skipped: {summary.get('blocked_count', 0)}")
        logger.info("="*60)
        
        # Write output
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Results written to: {output_path}")
        
        if gui:
            gui.update("log", {"message": f"\n[COMPLETE] Results saved to {output_path}\n"})
            logger.info("GUI will remain open. Close window to exit.")
            # Keep GUI running
            while True:
                await asyncio.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("\nSimulation interrupted by user")
        if gui:
            gui.close()
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        if gui:
            gui.update("log", {"message": f"\n[ERROR] {e}\n"})
            gui.close()
        raise


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run Solana Hyper-Bot simulation with real-time or mock data"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of simulation cycles (default: 100)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between cycles in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--execute-trades",
        action="store_true",
        help="Execute trades (paper trading). If not set, only makes decisions."
    )
    
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.75,
        help="Minimum confidence threshold (default: 0.75)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="data/performance_stats.json",
        help="Output path for metrics (default: data/performance_stats.json)"
    )
    
    parser.add_argument(
        "--real-time",
        action="store_true",
        help="Use REAL-TIME market data from Jupiter/Birdeye APIs (default: mock data)"
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Show GUI dashboard for real-time monitoring"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    # Run simulation
    asyncio.run(run_simulation(
        iterations=args.iterations,
        delay_sec=args.delay,
        execute_trades=args.execute_trades,
        min_confidence=args.min_confidence,
        output_path=args.output,
        use_real_time=args.real_time,
        show_gui=args.gui,
        verbose=args.verbose
    ))


if __name__ == "__main__":
    main() 
