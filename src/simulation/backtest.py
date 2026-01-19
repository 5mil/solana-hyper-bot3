"""Backtest: Historical data replay through decision pipeline.

The Backtest runner accepts historical market data bars and replays them
through the same decision pipeline used by live bot and simulator.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from src.core.types import MarketState
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.execution.leverage_engine import LeverageEngine, LeverageConfig
from src.simulation.paper_trader import PaperTrader


@dataclass
class HistoricalBar:
    """Historical OHLCV bar.
    
    Attributes:
        timestamp: Bar timestamp in milliseconds
        open: Opening price
        high: High price
        low: Low price
        close: Closing price
        volume: Volume
    """
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class Backtest:
    """Historical data backtest runner.
    
    Replays historical bars through the decision pipeline, using the same
    components as live trading and simulation.
    
    Attributes:
        logic_gate: LogicGate for filtering
        ensemble: HyperEnsemble for decisions
        leverage_engine: LeverageEngine for sizing
        paper_trader: PaperTrader for execution
        min_confidence: Minimum confidence threshold
    """
    
    def __init__(
        self,
        logic_gate: Optional[LogicGate] = None,
        ensemble: Optional[HyperEnsemble] = None,
        leverage_config: Optional[LeverageConfig] = None,
        initial_capital: float = 100.0,
        min_confidence: float = 0.75,
    ):
        """Initialize Backtest.
        
        Args:
            logic_gate: LogicGate instance
            ensemble: HyperEnsemble instance
            leverage_config: Leverage configuration
            initial_capital: Starting capital
            min_confidence: Minimum confidence threshold
        """
        self.logic_gate = logic_gate or LogicGate()
        self.ensemble = ensemble or HyperEnsemble(min_confidence=min_confidence)
        self.paper_trader = PaperTrader(initial_capital=initial_capital)
        self.leverage_engine = LeverageEngine(
            config=leverage_config or LeverageConfig(),
            current_capital=initial_capital,
        )
        self.min_confidence = min_confidence
    
    def _bar_to_market_state(self, bar: HistoricalBar, symbol: str = "SOL/USD") -> MarketState:
        """Convert historical bar to MarketState.
        
        Args:
            bar: Historical bar data
            symbol: Trading pair symbol
            
        Returns:
            MarketState representation
        """
        # Use close as current price
        price = bar.close
        
        # Estimate bid/ask from high/low
        spread = (bar.high - bar.low) / 2
        bid = price - spread / 2
        ask = price + spread / 2
        
        # Simple volatility estimate from range
        volatility = (bar.high - bar.low) / bar.close if bar.close > 0 else 0.0
        
        return MarketState(
            timestamp=bar.timestamp,
            symbol=symbol,
            price=price,
            bid=max(bid, 0.01),
            ask=ask,
            volume_24h=bar.volume,
            ema_short=price,  # Simplified - could compute actual EMA
            ema_long=price,
            volatility=volatility,
            spread_bps=(ask - bid) / price * 10000 if price > 0 else 0,
            latency_ms=0.0,  # Historical data has no latency
            mev_risk_score=0.0,  # Historical data has no MEV risk
            liquidity_depth=bar.volume,
        )
    
    def run(
        self,
        bars: List[HistoricalBar],
        symbol: str = "SOL/USD",
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run backtest on historical bars.
        
        Args:
            bars: List of historical bars to replay
            symbol: Trading pair symbol
            output_path: Optional path to write results
            
        Returns:
            Summary dictionary with backtest results
        """
        results = []
        
        for i, bar in enumerate(bars):
            # Convert bar to market state
            market_state = self._bar_to_market_state(bar, symbol)
            
            # Run logic gate
            allowed, block_reasons = self.logic_gate.check(market_state)
            if not allowed:
                results.append({
                    "bar_index": i,
                    "timestamp": bar.timestamp,
                    "status": "blocked",
                    "block_reasons": [r.value for r in block_reasons],
                })
                continue
            
            # Run ensemble
            decision = self.ensemble.run_and_assert(market_state, self.min_confidence)
            
            if decision.status.value != "approved":
                results.append({
                    "bar_index": i,
                    "timestamp": bar.timestamp,
                    "status": "low_confidence",
                    "confidence": decision.consensus_confidence,
                })
                continue
            
            # Compute position size
            allocation_fraction = decision.consensus_confidence * 0.35
            position_size, leverage = self.leverage_engine.compute_position_size(
                decision.action,
                market_state,
                allocation_fraction,
            )
            
            if position_size > 0:
                # Execute trade
                decision.action.leverage = leverage
                trade = self.paper_trader.simulate_execution(
                    decision.action,
                    market_state,
                    position_size,
                )
                
                # Update capital
                self.leverage_engine.update_capital(self.paper_trader.current_capital)
                
                results.append({
                    "bar_index": i,
                    "timestamp": bar.timestamp,
                    "status": "executed",
                    "trade_id": trade.trade_id,
                    "action": trade.action_type.value,
                    "size": trade.size_usd,
                    "price": trade.entry_price,
                })
        
        # Close all positions at end
        if bars:
            final_market_state = self._bar_to_market_state(bars[-1], symbol)
            self.paper_trader.close_all_positions(final_market_state)
        
        # Generate summary
        trading_summary = self.paper_trader.summary()
        
        summary = {
            "backtest_complete": True,
            "bars_processed": len(bars),
            "trades_executed": trading_summary["total_trades"],
            "trading_performance": trading_summary,
        }
        
        # Write output if path provided
        if output_path:
            report = {
                "summary": summary,
                "results": results,
            }
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
        
        return summary
