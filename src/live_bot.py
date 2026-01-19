"""
LiveBot: Main bot loop for simulation and live trading.

Implements the main decision loop used for both simulation and live modes.
Each cycle: fetch market state, run LogicGate, run HyperEnsemble, size position,
execute via appropriate executor.
"""
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from src.core.types import MarketState, ActionType
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.core.onflow_engine import OnflowEngine
from src.core.mdp_decision import MDPDecision
from src.execution.leverage_engine import LeverageEngine, LeverageConfig
from src.execution.jito_warp import JitoWarpExecutor
from src.execution.twap_executor import TWAPExecutor
from src.execution.interfaces import MarketDataFetcher
from src.simulation.paper_trader import PaperTrader


class LiveBot:
    """
    Main bot implementing the decision loop.
    
    Can run in simulation or live mode. In simulation mode, uses PaperTrader.
    In live mode, uses real executors (Jito + TWAP).
    """
    
    def __init__(
        self,
        market_data_fetcher: MarketDataFetcher,
        mode: str = "simulation",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize LiveBot.
        
        Args:
            market_data_fetcher: Fetcher for market data
            mode: "simulation" or "live"
            config: Bot configuration dictionary
        """
        self.market_data_fetcher = market_data_fetcher
        self.mode = mode
        self.config = config or {}
        
        # Initialize components
        self.logic_gate = LogicGate()
        self.onflow_engine = OnflowEngine()
        self.mdp_engine = MDPDecision()
        
        # Setup ensemble with engines
        self.ensemble = HyperEnsemble()
        self.ensemble.add_engine(
            "onflow",
            lambda ms: (ActionType.BUY, self.onflow_engine.suggest_allocation(ms))
        )
        self.ensemble.add_engine(
            "mdp",
            lambda ms: self.mdp_engine.select_action(ms, explore=True)
        )
        
        # Leverage and execution
        leverage_config = LeverageConfig(
            max_position_pct=self.config.get("max_position_pct", 0.35),
            account_balance=self.config.get("account_balance", 100.0)
        )
        self.leverage_engine = LeverageEngine(leverage_config)
        
        # Mode-specific setup
        if mode == "simulation":
            self.paper_trader = PaperTrader(
                initial_balance=self.config.get("initial_balance", 100.0)
            )
            self.executor = None
        else:
            self.paper_trader = None
            # In live mode, would initialize real executors
            self.jito_executor = JitoWarpExecutor()
            self.twap_executor = None  # Would need real quote client
        
        # Metrics
        self.min_confidence = self.config.get("min_confidence", 0.75)
        self.metrics_path = Path(self.config.get("metrics_path", "data/performance_stats.json"))
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.cycle_count = 0
        self.total_trades = 0
        self.blocked_count = 0
        self.running = False
    
    async def run_cycle(self, symbol: str = "SOL/USD") -> Dict[str, Any]:
        """
        Run one decision cycle.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Cycle report
        """
        self.cycle_count += 1
        
        # Step 1: Fetch market state
        market_state = await self.market_data_fetcher.fetch_market_state(symbol)
        
        # Step 2: LogicGate filter
        from src.core.types import Action
        dummy_action = Action(
            action_type=ActionType.BUY,
            size=1.0,
            confidence=0.5
        )
        
        filter_result = self.logic_gate.check(market_state, dummy_action)
        if not filter_result.allowed:
            self.blocked_count += 1
            return {
                "cycle": self.cycle_count,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "blocked_by_logic_gate",
                "reasons": filter_result.reasons
            }
        
        # Step 3: HyperEnsemble decision
        decision = self.ensemble.run_and_assert(market_state, self.min_confidence)
        if decision is None:
            self.blocked_count += 1
            return {
                "cycle": self.cycle_count,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "blocked_by_confidence"
            }
        
        # Step 4: Size position
        if self.mode == "simulation":
            balance = self.paper_trader.balance
        else:
            balance = self.config.get("account_balance", 100.0)
        
        sized_action = self.leverage_engine.size_position(
            decision.action,
            market_state,
            balance
        )
        
        # Step 5: Execute
        if sized_action.action_type == ActionType.HOLD:
            return {
                "cycle": self.cycle_count,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "hold",
                "confidence": decision.consensus_confidence
            }
        
        if self.mode == "simulation":
            # Paper trade
            trade = self.paper_trader.simulate_execution(sized_action, market_state)
            self.total_trades += 1
            
            return {
                "cycle": self.cycle_count,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "paper_trade",
                "action": sized_action.action_type.value,
                "size": sized_action.size,
                "leverage": sized_action.leverage,
                "confidence": decision.consensus_confidence,
                "price": trade.entry_price
            }
        else:
            # Live execution (Jito + TWAP)
            # NOTE: This is a stub - would require real wallet signing
            result = await self.jito_executor.execute_action(sized_action, market_state)
            self.total_trades += 1
            
            return {
                "cycle": self.cycle_count,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "live_execution",
                "action": sized_action.action_type.value,
                "result": result
            }
    
    async def run_loop(
        self,
        max_cycles: Optional[int] = None,
        cycle_delay_sec: float = 5.0,
        symbol: str = "SOL/USD"
    ):
        """
        Run main bot loop.
        
        Args:
            max_cycles: Maximum cycles (None for infinite)
            cycle_delay_sec: Delay between cycles
            symbol: Trading symbol
        """
        self.running = True
        cycles_run = 0
        
        try:
            while self.running:
                if max_cycles and cycles_run >= max_cycles:
                    break
                
                report = await self.run_cycle(symbol)
                cycles_run += 1
                
                # Persist metrics
                await self.persist_metrics()
                
                await asyncio.sleep(cycle_delay_sec)
                
        except KeyboardInterrupt:
            print("Bot stopped by user")
        finally:
            self.running = False
            await self.persist_metrics()
    
    async def persist_metrics(self):
        """Persist performance metrics to JSON."""
        if self.mode == "simulation" and self.paper_trader:
            summary = self.paper_trader.get_summary()
        else:
            summary = {
                "mode": self.mode,
                "note": "Live mode metrics not implemented"
            }
        
        metrics = {
            "mode": self.mode,
            "cycle_count": self.cycle_count,
            "total_trades": self.total_trades,
            "blocked_count": self.blocked_count,
            "last_updated": datetime.utcnow().isoformat(),
            "trading_summary": summary
        }
        
        with open(self.metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
    
    def stop(self):
        """Stop the bot loop."""
        self.running = False


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Solana Hyper-Accumulation Bot v3.0")
    parser.add_argument("--mode", choices=["simulation", "live"], default="simulation")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--cycles", type=int, help="Max cycles to run")
    parser.add_argument("--delay", type=float, default=5.0, help="Delay between cycles")
    
    args = parser.parse_args()
    
    # Load config
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    else:
        config = {}
    
    # Setup mock fetcher for testing
    from src.adapters.mock_quote_client import MockMarketDataFetcher
    fetcher = MockMarketDataFetcher()
    
    # Create and run bot
    bot = LiveBot(fetcher, mode=args.mode, config=config)
    
    print(f"Starting bot in {args.mode} mode...")
    await bot.run_loop(max_cycles=args.cycles, cycle_delay_sec=args.delay)
    
    print("Bot finished.")
    if bot.mode == "simulation":
        summary = bot.paper_trader.get_summary()
        print(f"\nSimulation Summary:")
        print(f"  Total trades: {summary['total_trades']}")
        print(f"  Win rate: {summary['win_rate']:.1f}%")
        print(f"  Return: {summary['return_pct']:.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
