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
        min_confidence: Optional[float] = None,
        execute_trades: bool = False,
        metrics_path: str = "data/performance_stats.json",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize market simulator.
        
        Args:
            market_data_fetcher: Fetcher for market data
            logic_gate: Logic gate filter (creates default if None)
            ensemble: Decision ensemble (creates default if None)
            leverage_engine: Position sizing (creates default if None)
            paper_trader: Paper trader (creates default if None)
            min_confidence: Minimum confidence for execution (overridden by config if present)
            execute_trades: Whether to execute trades (if False, only simulate decisions)
            metrics_path: Path to write metrics
            config: Optional configuration dictionary
        """
        self.market_data_fetcher = market_data_fetcher
        
        # Handle config
        config = config or {}
        self.min_confidence = config.get("min_confidence", min_confidence or 0.75)
        initial_balance = config.get("initial_balance", 100.0)
        max_position_pct = config.get("max_position_pct", 0.35)
        
        self.logic_gate = logic_gate or LogicGate()
        
        # Initialize ensemble with default engines if not provided
        if ensemble is None:
            from src.core.onflow_engine import OnflowEngine
            from src.core.mdp_decision import MDPDecision
            
            self.ensemble = HyperEnsemble()
            self.onflow_engine = OnflowEngine()
            self.mdp_engine = MDPDecision()
            
            # Add engines to ensemble
            self.ensemble.add_engine(
                "onflow",
                lambda ms: (ActionType.BUY, self.onflow_engine.suggest_allocation(ms))
            )
            self.ensemble.add_engine(
                "mdp",
                lambda ms: self.mdp_engine.select_action(ms, explore=True)
            )
        else:
            self.ensemble = ensemble
            self.onflow_engine = None
            self.mdp_engine = None
        
        self.leverage_engine = leverage_engine or LeverageEngine(
            LeverageConfig(
                max_position_pct=max_position_pct,
                account_balance=initial_balance
            )
        )
        self.paper_trader = paper_trader or PaperTrader(initial_balance=initial_balance)
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
                "status": "paper_trade",
                "action": sized_action.action_type.value,
                "size": sized_action.size,
                "leverage": sized_action.leverage,
                "confidence": decision.consensus_confidence,
                "price": market_state.price,
                "pnl": 0,  # Will be calculated on position close
                "trade": {
                    "entry_price": trade.entry_price,
                    "fees_paid": trade.fees_paid,
                    "slippage_pct": trade.slippage_pct
                },
                "market_state": {
                    "price": market_state.price,
                    "regime": market_state.regime.value
                }
            }
        else:
            return {
                "iteration": self.iteration,
                "status": "simulated_decision",
                "action": sized_action.action_type.value,
                "size": sized_action.size,
                "confidence": decision.consensus_confidence,
                "price": market_state.price,
                "market_state": {
                    "price": market_state.price,
                    "regime": market_state.regime.value
                }
            }
    
    async def run_cycle(self, symbol: str = "SOL/USD", execute_trades: bool = None) -> Dict[str, Any]:
        """
        Run one simulation cycle (alias for run_iteration with optional execute_trades override).
        
        Args:
            symbol: Trading symbol
            execute_trades: Override execute_trades setting for this cycle
            
        Returns:
            Cycle report
        """
        if execute_trades is not None:
            old_execute = self.execute_trades
            self.execute_trades = execute_trades
            result = await self.run_iteration(symbol)
            self.execute_trades = old_execute
            return result
        else:
            return await self.run_iteration(symbol)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get current simulation summary.
        
        Returns:
            Summary dictionary with balance, trades, P&L, etc.
        """
        paper_summary = self.paper_trader.get_summary()
        
        # Normalize keys for consistency
        final_balance = paper_summary.get("current_balance", paper_summary.get("final_balance", 0))
        total_pnl = paper_summary.get("total_pnl", 0)
        total_trades = paper_summary.get("total_trades", 0)
        winning_trades = paper_summary.get("winning_trades", 0)
        
        return {
            "final_balance": final_balance,
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate_pct": paper_summary.get("win_rate", 0.0),
            "return_pct": paper_summary.get("return_pct", 0.0),
            "max_drawdown_pct": 0.0,  # Would need historical tracking
            "blocked_count": self.decisions_blocked,
            "approved_count": self.decisions_approved,
            "total_cycles": self.iteration,
            "approval_rate": (self.decisions_approved / self.iteration * 100) if self.iteration > 0 else 0
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
