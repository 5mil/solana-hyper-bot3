"""Live Bot: Main trading loop for simulation and live modes.

The LiveBot implements the main trading loop used for both simulation and
live trading. Each cycle: fetch market data, run LogicGate, run HyperEnsemble,
size position, and execute trades. Persists metrics and provides health checks.
"""

import json
import time
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from enum import Enum

from src.core.types import MarketState, ActionType, DecisionStatus, PerformanceMetrics
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.core.onflow_engine import OnflowEngine
from src.execution.interfaces import MarketDataFetcher
from src.execution.leverage_engine import LeverageEngine, LeverageConfig
from src.execution.jito_warp import JitoWarpExecutor
from src.execution.twap_executor import TWAPExecutor
from src.simulation.paper_trader import PaperTrader


class BotMode(str, Enum):
    """Bot operating mode."""
    SIMULATION = "simulation"
    LIVE = "live"


class LiveBot:
    """Main trading bot for simulation and live modes.
    
    Implements the core trading loop:
    1. Fetch MarketState via MarketDataFetcher
    2. Run LogicGate (return early if blocked)
    3. Run HyperEnsemble (return early if consensus < min_confidence)
    4. Size position via LeverageEngine (Kelly-like but capped)
    5. Execute via JitoWarpExecutor + TWAPExecutor (live) or PaperTrader (sim)
    
    Persists metrics to JSON and provides health check interface.
    
    Attributes:
        mode: Operating mode (simulation or live)
        market_fetcher: MarketDataFetcher implementation
        logic_gate: LogicGate for filtering
        ensemble: HyperEnsemble for decisions
        onflow_engine: OnflowEngine for allocation
        leverage_engine: LeverageEngine for sizing
        paper_trader: PaperTrader (simulation mode)
        jito_executor: JitoWarpExecutor (live mode)
        twap_executor: TWAPExecutor (live mode)
        metrics: Current performance metrics
        config: Bot configuration
    """
    
    def __init__(
        self,
        mode: BotMode,
        market_fetcher: MarketDataFetcher,
        config: Dict[str, Any],
        logic_gate: Optional[LogicGate] = None,
        ensemble: Optional[HyperEnsemble] = None,
        onflow_engine: Optional[OnflowEngine] = None,
        leverage_config: Optional[LeverageConfig] = None,
        jito_executor: Optional[JitoWarpExecutor] = None,
        twap_executor: Optional[TWAPExecutor] = None,
    ):
        """Initialize LiveBot.
        
        Args:
            mode: Operating mode
            market_fetcher: Market data fetcher
            config: Bot configuration dictionary
            logic_gate: LogicGate instance
            ensemble: HyperEnsemble instance
            onflow_engine: OnflowEngine instance
            leverage_config: Leverage configuration
            jito_executor: Jito executor (live mode)
            twap_executor: TWAP executor (live mode)
        """
        self.mode = mode
        self.market_fetcher = market_fetcher
        self.config = config
        
        # Core components
        self.logic_gate = logic_gate or LogicGate()
        self.ensemble = ensemble or HyperEnsemble(
            min_confidence=config.get("min_confidence", 0.75)
        )
        self.onflow_engine = onflow_engine or OnflowEngine()
        
        # Execution components
        initial_capital = config.get("initial_balance", 100.0)
        self.leverage_engine = LeverageEngine(
            config=leverage_config or LeverageConfig(
                max_position_pct=config.get("max_position_pct", 0.35)
            ),
            current_capital=initial_capital,
        )
        
        # Mode-specific executors
        if mode == BotMode.SIMULATION:
            self.paper_trader = PaperTrader(initial_capital=initial_capital)
        else:
            self.paper_trader = None
            self.jito_executor = jito_executor or JitoWarpExecutor()
            self.twap_executor = twap_executor
        
        # Metrics
        self.metrics = PerformanceMetrics()
        self.metrics_path = config.get("metrics_path", "data/performance_stats.json")
        
        # Circuit breaker
        self.circuit_breaker_triggered = False
        self.consecutive_losses = 0
        self.daily_loss_pct = 0.0
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should trigger.
        
        Returns:
            True if circuit breaker triggered
        """
        max_drawdown = self.config.get("circuit_breaker_drawdown", 0.25)
        max_daily_loss = self.config.get("max_daily_loss_pct", 0.15)
        max_consecutive_losses = self.config.get("consecutive_losses_limit", 5)
        
        if self.metrics.max_drawdown_pct / 100 >= max_drawdown:
            print(f"Circuit breaker: Max drawdown {self.metrics.max_drawdown_pct}% exceeded")
            return True
        
        if self.daily_loss_pct >= max_daily_loss:
            print(f"Circuit breaker: Daily loss {self.daily_loss_pct}% exceeded")
            return True
        
        if self.consecutive_losses >= max_consecutive_losses:
            print(f"Circuit breaker: {self.consecutive_losses} consecutive losses")
            return True
        
        return False
    
    def run_cycle(self, symbol: str = "SOL/USD") -> Dict[str, Any]:
        """Run a single trading cycle.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dictionary with cycle results
        """
        # Check circuit breaker
        if self._check_circuit_breaker():
            self.circuit_breaker_triggered = True
            return {
                "status": "circuit_breaker_triggered",
                "timestamp": int(time.time() * 1000),
            }
        
        # 1. Fetch market state
        try:
            market_state = self.market_fetcher.fetch_market_state(symbol)
        except Exception as e:
            return {
                "status": "market_fetch_failed",
                "error": str(e),
                "timestamp": int(time.time() * 1000),
            }
        
        # 2. Run logic gate
        allowed, block_reasons = self.logic_gate.check(market_state)
        if not allowed:
            return {
                "status": "blocked_by_logic_gate",
                "block_reasons": [r.value for r in block_reasons],
                "timestamp": int(time.time() * 1000),
            }
        
        # 3. Run ensemble
        min_confidence = self.config.get("min_confidence", 0.75)
        decision = self.ensemble.run_and_assert(market_state, min_confidence)
        
        if decision.status != DecisionStatus.APPROVED:
            return {
                "status": "blocked_by_ensemble",
                "confidence": decision.consensus_confidence,
                "block_reasons": [r.value for r in decision.block_reasons],
                "timestamp": int(time.time() * 1000),
            }
        
        # Skip HOLD actions
        if decision.action.action_type == ActionType.HOLD:
            return {
                "status": "hold_decision",
                "timestamp": int(time.time() * 1000),
            }
        
        # 4. Size position
        allocation_fraction = self.onflow_engine.get_allocation_fraction(
            decision.consensus_confidence
        )
        
        position_size, leverage = self.leverage_engine.compute_position_size(
            decision.action,
            market_state,
            allocation_fraction,
        )
        
        if position_size <= 0:
            return {
                "status": "position_size_too_small",
                "timestamp": int(time.time() * 1000),
            }
        
        # 5. Execute
        decision.action.leverage = leverage
        
        if self.mode == BotMode.SIMULATION:
            # Simulation mode - use paper trader
            trade = self.paper_trader.simulate_execution(
                decision.action,
                market_state,
                position_size,
            )
            
            self.metrics.total_trades += 1
            self.leverage_engine.update_capital(self.paper_trader.current_capital)
            
            return {
                "status": "executed_simulation",
                "trade_id": trade.trade_id,
                "size": trade.size_usd,
                "price": trade.entry_price,
                "timestamp": int(time.time() * 1000),
            }
        else:
            # Live mode - use Jito + TWAP
            # In production, this would execute real transactions
            # For now, just log the intent
            return {
                "status": "would_execute_live",
                "action": decision.action.action_type.value,
                "size": position_size,
                "leverage": leverage,
                "timestamp": int(time.time() * 1000),
                "note": "Live execution requires production adapters and secrets",
            }
    
    def run_loop(
        self,
        iterations: Optional[int] = None,
        delay_sec: float = 5.0,
    ) -> None:
        """Run the main trading loop.
        
        Args:
            iterations: Number of iterations (None = infinite)
            delay_sec: Delay between cycles
        """
        iteration = 0
        
        while iterations is None or iteration < iterations:
            if self.circuit_breaker_triggered:
                print("Circuit breaker triggered, stopping bot")
                break
            
            result = self.run_cycle()
            print(f"Cycle {iteration}: {result['status']}")
            
            # Persist metrics
            self._save_metrics()
            
            iteration += 1
            time.sleep(delay_sec)
    
    def _save_metrics(self) -> None:
        """Save current metrics to JSON file."""
        # Update metrics from paper trader if in simulation mode
        if self.mode == BotMode.SIMULATION and self.paper_trader:
            summary = self.paper_trader.summary()
            self.metrics.total_trades = summary["total_trades"]
            self.metrics.winning_trades = summary["winning_trades"]
            self.metrics.losing_trades = summary["losing_trades"]
            self.metrics.win_rate = summary["win_rate"]
            self.metrics.total_pnl = summary["total_pnl"]
        
        # Save to file
        Path(self.metrics_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_path, "w") as f:
            json.dump(self.metrics.model_dump(), f, indent=2)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check.
        
        Returns:
            Dictionary with health status
        """
        return {
            "healthy": not self.circuit_breaker_triggered,
            "mode": self.mode.value,
            "metrics_exist": Path(self.metrics_path).exists(),
            "total_trades": self.metrics.total_trades,
            "circuit_breaker": self.circuit_breaker_triggered,
        }


if __name__ == "__main__":
    import sys
    
    # This would normally load config from file and initialize with real/mock adapters
    print("LiveBot - use tools/run_simulation.py or configure with real adapters")
    sys.exit(0)
