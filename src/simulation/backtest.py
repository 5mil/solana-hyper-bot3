"""
Backtest: Historical replay using the same decision pipeline.

Replays historical price bars through the decision pipeline to evaluate
strategy performance on past data.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.core.types import MarketState, MarketRegime
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.execution.leverage_engine import LeverageEngine
from src.simulation.paper_trader import PaperTrader


class Backtest:
    """
    Backtest runner for historical data replay.
    
    Replays historical bars through the same decision pipeline used
    in live trading to evaluate strategy performance.
    """
    
    def __init__(
        self,
        logic_gate: Optional[LogicGate] = None,
        ensemble: Optional[HyperEnsemble] = None,
        leverage_engine: Optional[LeverageEngine] = None,
        paper_trader: Optional[PaperTrader] = None,
        min_confidence: float = 0.75
    ):
        """
        Initialize backtest runner.
        
        Args:
            logic_gate: Logic gate filter
            ensemble: Decision ensemble
            leverage_engine: Position sizing
            paper_trader: Paper trader
            min_confidence: Minimum confidence for execution
        """
        self.logic_gate = logic_gate or LogicGate()
        self.ensemble = ensemble or HyperEnsemble()
        self.leverage_engine = leverage_engine or LeverageEngine()
        self.paper_trader = paper_trader or PaperTrader()
        self.min_confidence = min_confidence
    
    def create_market_state_from_bar(self, bar: Dict[str, Any]) -> MarketState:
        """
        Create MarketState from a historical bar.
        
        Args:
            bar: Dictionary with OHLCV data
            
        Returns:
            MarketState
        """
        # Extract basic fields
        timestamp = bar.get("timestamp", datetime.utcnow())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        price = bar.get("close", bar.get("price", 100.0))
        volume = bar.get("volume", 1000.0)
        
        # Calculate bid/ask from high/low or use spread
        high = bar.get("high", price * 1.001)
        low = bar.get("low", price * 0.999)
        
        return MarketState(
            timestamp=timestamp,
            symbol=bar.get("symbol", "SOL/USD"),
            price=price,
            volume_24h=volume,
            bid=low,
            ask=high,
            ema_fast=bar.get("ema_fast"),
            ema_slow=bar.get("ema_slow"),
            regime=MarketRegime(bar.get("regime", "unknown")),
            volatility=bar.get("volatility", 0.02),
            liquidity_score=bar.get("liquidity_score", 0.8),
            mev_risk_score=bar.get("mev_risk_score", 0.1),
            latency_ms=bar.get("latency_ms", 100.0)
        )
    
    async def run_backtest(
        self,
        historical_bars: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run backtest on historical bars.
        
        Args:
            historical_bars: List of historical bar dictionaries
            
        Returns:
            Backtest summary with performance metrics
        """
        results = []
        
        for i, bar in enumerate(historical_bars):
            market_state = self.create_market_state_from_bar(bar)
            
            # Create dummy action for logic gate
            from src.core.types import Action, ActionType
            dummy_action = Action(
                action_type=ActionType.BUY,
                size=1.0,
                confidence=0.5
            )
            
            # Logic gate filter
            filter_result = self.logic_gate.check(market_state, dummy_action)
            
            if not filter_result.allowed:
                results.append({
                    "bar": i,
                    "timestamp": market_state.timestamp.isoformat(),
                    "status": "blocked",
                    "price": market_state.price
                })
                continue
            
            # Ensemble decision
            decision = self.ensemble.run_and_assert(market_state, self.min_confidence)
            
            if decision is None:
                results.append({
                    "bar": i,
                    "timestamp": market_state.timestamp.isoformat(),
                    "status": "low_confidence",
                    "price": market_state.price
                })
                continue
            
            # Size and execute
            sized_action = self.leverage_engine.size_position(
                decision.action,
                market_state,
                self.paper_trader.balance
            )
            
            if sized_action.action_type != ActionType.HOLD:
                trade = self.paper_trader.simulate_execution(sized_action, market_state)
                
                # For backtest, close position at next bar or end
                if i + 1 < len(historical_bars):
                    next_bar = historical_bars[i + 1]
                    next_state = self.create_market_state_from_bar(next_bar)
                    self.paper_trader.record_exit(
                        trade,
                        next_state.price,
                        next_state.timestamp
                    )
                
                results.append({
                    "bar": i,
                    "timestamp": market_state.timestamp.isoformat(),
                    "status": "executed",
                    "action": sized_action.action_type.value,
                    "price": market_state.price,
                    "size": sized_action.size
                })
        
        # Close any remaining positions
        if historical_bars:
            final_bar = historical_bars[-1]
            final_state = self.create_market_state_from_bar(final_bar)
            self.paper_trader.close_all_positions(final_state)
        
        summary = self.paper_trader.get_summary()
        
        return {
            "backtest_config": {
                "num_bars": len(historical_bars),
                "min_confidence": self.min_confidence
            },
            "results": results,
            "summary": summary
        }
