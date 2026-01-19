"""Market Simulator: High-fidelity simulation using real decision components.

The MarketSimulator uses the same decision pipeline as the live bot (LogicGate,
HyperEnsemble, LeverageEngine) but executes through PaperTrader instead of live.
Never signs or broadcasts transactions.
"""

import json
import time
from typing import Optional, Dict, Any
from pathlib import Path

from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.core.types import ActionType, DecisionStatus
from src.execution.interfaces import MarketDataFetcher
from src.execution.leverage_engine import LeverageEngine, LeverageConfig
from src.simulation.paper_trader import PaperTrader


class MarketSimulator:
    """High-fidelity market simulator using real decision components.
    
    Uses the same decision pipeline as live bot:
    1. Fetch market state via MarketDataFetcher
    2. Run LogicGate filter
    3. Run HyperEnsemble decision
    4. Size position via LeverageEngine
    5. Execute via PaperTrader
    
    Never signs or broadcasts transactions. Respects execute_trades flag
    and writes JSON reports.
    
    Attributes:
        market_fetcher: MarketDataFetcher for getting market data
        logic_gate: LogicGate for filtering
        ensemble: HyperEnsemble for decisions
        leverage_engine: LeverageEngine for sizing
        paper_trader: PaperTrader for simulated execution
        execute_trades: Whether to execute trades or just log decisions
        min_confidence: Minimum confidence threshold
    """
    
    def __init__(
        self,
        market_fetcher: MarketDataFetcher,
        logic_gate: Optional[LogicGate] = None,
        ensemble: Optional[HyperEnsemble] = None,
        leverage_config: Optional[LeverageConfig] = None,
        initial_capital: float = 100.0,
        execute_trades: bool = False,
        min_confidence: float = 0.75,
    ):
        """Initialize MarketSimulator.
        
        Args:
            market_fetcher: Market data fetcher
            logic_gate: LogicGate instance (creates default if None)
            ensemble: HyperEnsemble instance (creates default if None)
            leverage_config: Leverage configuration
            initial_capital: Starting capital
            execute_trades: Whether to actually execute trades
            min_confidence: Minimum confidence threshold
        """
        self.market_fetcher = market_fetcher
        self.logic_gate = logic_gate or LogicGate()
        self.ensemble = ensemble or HyperEnsemble(min_confidence=min_confidence)
        self.paper_trader = PaperTrader(initial_capital=initial_capital)
        self.leverage_engine = LeverageEngine(
            config=leverage_config or LeverageConfig(),
            current_capital=initial_capital,
        )
        
        self.execute_trades = execute_trades
        self.min_confidence = min_confidence
        
        # Tracking
        self.iteration_count = 0
        self.decisions_made = 0
        self.trades_executed = 0
    
    def run_iteration(self, symbol: str = "SOL/USD") -> Dict[str, Any]:
        """Run a single simulation iteration.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dictionary with iteration results
        """
        self.iteration_count += 1
        
        # 1. Fetch market state
        market_state = self.market_fetcher.fetch_market_state(symbol)
        
        # 2. Run logic gate
        allowed, block_reasons = self.logic_gate.check(market_state)
        if not allowed:
            return {
                "iteration": self.iteration_count,
                "timestamp": int(time.time() * 1000),
                "status": "blocked_by_logic_gate",
                "block_reasons": [r.value for r in block_reasons],
                "market_state": market_state.model_dump(),
            }
        
        # 3. Run ensemble decision
        decision = self.ensemble.run_and_assert(market_state, self.min_confidence)
        self.decisions_made += 1
        
        if decision.status != DecisionStatus.APPROVED:
            return {
                "iteration": self.iteration_count,
                "timestamp": int(time.time() * 1000),
                "status": "blocked_by_ensemble",
                "block_reasons": [r.value for r in decision.block_reasons],
                "consensus_confidence": decision.consensus_confidence,
                "market_state": market_state.model_dump(),
            }
        
        # 4. Skip non-actionable decisions
        if decision.action.action_type in [ActionType.HOLD]:
            return {
                "iteration": self.iteration_count,
                "timestamp": int(time.time() * 1000),
                "status": "hold_decision",
                "action": decision.action.model_dump(),
                "market_state": market_state.model_dump(),
            }
        
        # 5. Compute position size
        # Get allocation fraction (mock onflow engine with simple confidence scaling)
        allocation_fraction = decision.consensus_confidence * 0.35
        
        position_size, leverage = self.leverage_engine.compute_position_size(
            decision.action,
            market_state,
            allocation_fraction,
        )
        
        # 6. Execute trade (if enabled)
        if self.execute_trades and position_size > 0:
            # Update action with computed leverage
            decision.action.leverage = leverage
            
            # Simulate execution
            trade = self.paper_trader.simulate_execution(
                decision.action,
                market_state,
                position_size,
            )
            
            self.trades_executed += 1
            
            # Update leverage engine capital
            self.leverage_engine.update_capital(self.paper_trader.current_capital)
            
            return {
                "iteration": self.iteration_count,
                "timestamp": int(time.time() * 1000),
                "status": "trade_executed",
                "trade": {
                    "trade_id": trade.trade_id,
                    "action_type": trade.action_type.value,
                    "entry_price": trade.entry_price,
                    "size_usd": trade.size_usd,
                    "leverage": trade.leverage,
                    "fees": trade.fees,
                    "slippage_bps": trade.slippage_bps,
                },
                "decision": decision.model_dump(),
                "market_state": market_state.model_dump(),
            }
        
        return {
            "iteration": self.iteration_count,
            "timestamp": int(time.time() * 1000),
            "status": "decision_approved_not_executed",
            "decision": decision.model_dump(),
            "position_size": position_size,
            "market_state": market_state.model_dump(),
        }
    
    def run(
        self,
        iterations: int = 100,
        delay_sec: float = 0.1,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run full simulation for specified iterations.
        
        Args:
            iterations: Number of iterations to run
            delay_sec: Delay between iterations
            output_path: Path to write JSON report (optional)
            
        Returns:
            Summary dictionary with results
        """
        iteration_results = []
        
        for i in range(iterations):
            result = self.run_iteration()
            iteration_results.append(result)
            
            if delay_sec > 0:
                time.sleep(delay_sec)
        
        # Close all open positions
        market_state = self.market_fetcher.fetch_market_state()
        self.paper_trader.close_all_positions(market_state)
        
        # Generate summary
        trading_summary = self.paper_trader.summary()
        
        summary = {
            "simulation_complete": True,
            "total_iterations": self.iteration_count,
            "decisions_made": self.decisions_made,
            "trades_executed": self.trades_executed,
            "trading_performance": trading_summary,
            "execute_trades": self.execute_trades,
            "min_confidence": self.min_confidence,
        }
        
        # Write report if path provided
        if output_path:
            report = {
                "summary": summary,
                "iterations": iteration_results,
            }
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
        
        return summary
