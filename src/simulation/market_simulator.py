"""
MarketSimulator: High-fidelity simulation using same components as live bot.

Runs the full decision pipeline (LogicGate -> HyperEnsemble -> sizing -> execution)
using paper trading instead of real execution.
"""
import json
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from src.core.types import MarketState, ActionType
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.execution.leverage_engine import LeverageEngine, LeverageConfig
from src.execution.interfaces import MarketDataFetcher
from src.simulation.paper_trader import PaperTrader


class MarketSimulator:
    """
    High-fidelity market simulator.
    
    Uses the same decision components as the live bot but executes
    via PaperTrader instead of real execution. Respects execute_trades
    flag and writes performance reports.
    """
    
    def __init__(
        self,
        market_data_fetcher: MarketDataFetcher,
        logic_gate: Optional[LogicGate] = None,
        ensemble: Optional[HyperEnsemble] = None,
        leverage_engine: Optional[LeverageEngine] = None,
        paper_trader: Optional[PaperTrader] = None,
        min_confidence: float = 0.75,
        execute_trades: bool = False,
        metrics_path: str = "data/performance_stats.json"
    ):
        """
        Initialize market simulator.
        
        Args:
            market_data_fetcher: Fetcher for market data
            logic_gate: Logic gate filter (creates default if None)
            ensemble: Decision ensemble (creates default if None)
            leverage_engine: Position sizing (creates default if None)
            paper_trader: Paper trader (creates default if None)
            min_confidence: Minimum confidence for execution
            execute_trades: Whether to execute trades (if False, only simulate decisions)
            metrics_path: Path to write metrics
        """
        self.market_data_fetcher = market_data_fetcher
        self.logic_gate = logic_gate or LogicGate()
        self.ensemble = ensemble or HyperEnsemble()
        self.leverage_engine = leverage_engine or LeverageEngine()
        self.paper_trader = paper_trader or PaperTrader()
        self.min_confidence = min_confidence
        self.execute_trades = execute_trades
        self.metrics_path = Path(metrics_path)
        
        # Ensure metrics directory exists
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.iteration = 0
        self.decisions_blocked = 0
        self.decisions_approved = 0
    
    async def run_iteration(self, symbol: str = "SOL/USD") -> Dict[str, Any]:
        """
        Run one simulation iteration.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Iteration report
        """
        self.iteration += 1
        
        # Fetch market state
        market_state = await self.market_data_fetcher.fetch_market_state(symbol)
        
        # Create a dummy action for logic gate check
        from src.core.types import Action
        dummy_action = Action(
            action_type=ActionType.BUY,
            size=1.0,
            confidence=0.5
        )
        
        # Step 1: LogicGate filter
        filter_result = self.logic_gate.check(market_state, dummy_action)
        
        if not filter_result.allowed:
            self.decisions_blocked += 1
            return {
                "iteration": self.iteration,
                "status": "blocked_by_logic_gate",
                "reasons": filter_result.reasons,
                "market_state": {
                    "price": market_state.price,
                    "volume_24h": market_state.volume_24h
                }
            }
        
        # Step 2: HyperEnsemble decision
        decision = self.ensemble.run_and_assert(market_state, self.min_confidence)
        
        if decision is None:
            self.decisions_blocked += 1
            return {
                "iteration": self.iteration,
                "status": "blocked_by_low_confidence",
                "market_state": {
                    "price": market_state.price,
                    "volume_24h": market_state.volume_24h
                }
            }
        
        self.decisions_approved += 1
        
        # Step 3: Size position
        sized_action = self.leverage_engine.size_position(
            decision.action,
            market_state,
            self.paper_trader.balance
        )
        
        # Step 4: Execute (or simulate)
        if self.execute_trades and sized_action.action_type != ActionType.HOLD:
            trade = self.paper_trader.simulate_execution(sized_action, market_state)
            
            return {
                "iteration": self.iteration,
                "status": "executed",
                "action": sized_action.action_type.value,
                "size": sized_action.size,
                "leverage": sized_action.leverage,
                "confidence": decision.consensus_confidence,
                "price": market_state.price,
                "trade": {
                    "entry_price": trade.entry_price,
                    "fees_paid": trade.fees_paid,
                    "slippage_pct": trade.slippage_pct
                }
            }
        else:
            return {
                "iteration": self.iteration,
                "status": "simulated_decision",
                "action": sized_action.action_type.value,
                "size": sized_action.size,
                "confidence": decision.consensus_confidence,
                "price": market_state.price
            }
    
    async def run_simulation(
        self,
        iterations: int = 100,
        delay_sec: float = 1.0,
        symbol: str = "SOL/USD"
    ) -> Dict[str, Any]:
        """
        Run simulation for multiple iterations.
        
        Args:
            iterations: Number of iterations
            delay_sec: Delay between iterations
            symbol: Trading symbol
            
        Returns:
            Simulation summary
        """
        iteration_reports = []
        
        for _ in range(iterations):
            report = await self.run_iteration(symbol)
            iteration_reports.append(report)
            await asyncio.sleep(delay_sec)
        
        # Close all open positions
        market_state = await self.market_data_fetcher.fetch_market_state(symbol)
        self.paper_trader.close_all_positions(market_state)
        
        # Get summary
        summary = self.paper_trader.get_summary()
        
        # Write report
        report = {
            "simulation_config": {
                "iterations": iterations,
                "min_confidence": self.min_confidence,
                "execute_trades": self.execute_trades
            },
            "decisions": {
                "total": self.iteration,
                "approved": self.decisions_approved,
                "blocked": self.decisions_blocked,
                "approval_rate": self.decisions_approved / self.iteration * 100 if self.iteration > 0 else 0
            },
            "trading_summary": summary,
            "iteration_reports": iteration_reports
        }
        
        # Write to file
        with open(self.metrics_path, "w") as f:
            json.dump(report, f, indent=2)
        
        return report
