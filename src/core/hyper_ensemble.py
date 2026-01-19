"""Hyper Ensemble: Multi-engine coordination and consensus decision-making.

The HyperEnsemble runs multiple decision engines (synchronously or asynchronously),
aggregates their votes by confidence weighting, and computes a consensus decision.
Implements run_and_assert to enforce minimum confidence thresholds.
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from src.core.types import MarketState, Action, Decision, DecisionStatus, ActionType, BlockReason
import time


class HyperEnsemble:
    """Ensemble coordinator that aggregates multiple decision engines.
    
    Runs multiple engines (can be sync or async), collects their Action votes,
    aggregates by confidence weighting, and produces a consensus Decision.
    
    Attributes:
        engines: Dictionary of engine name to engine callable
        min_confidence: Minimum consensus confidence required (default: 0.75)
        async_mode: Whether to run engines asynchronously
    """
    
    def __init__(
        self,
        engines: Optional[Dict[str, Callable[[MarketState], Action]]] = None,
        min_confidence: float = 0.75,
        async_mode: bool = False,
    ):
        """Initialize HyperEnsemble.
        
        Args:
            engines: Dictionary mapping engine names to callables
            min_confidence: Minimum consensus confidence (default: 0.75)
            async_mode: Run engines asynchronously (default: False)
        """
        self.engines = engines or {}
        self.min_confidence = min_confidence
        self.async_mode = async_mode
    
    def add_engine(self, name: str, engine: Callable[[MarketState], Action]) -> None:
        """Add an engine to the ensemble.
        
        Args:
            name: Engine identifier
            engine: Callable that takes MarketState and returns Action
        """
        self.engines[name] = engine
    
    def run(self, market_state: MarketState) -> Decision:
        """Run all engines and aggregate their votes into a consensus decision.
        
        Args:
            market_state: Current market state
            
        Returns:
            Decision with consensus action and confidence
        """
        if not self.engines:
            # No engines, return HOLD with low confidence
            return Decision(
                status=DecisionStatus.BLOCKED,
                action=Action(action_type=ActionType.HOLD, confidence=0.0),
                consensus_confidence=0.0,
                block_reasons=[BlockReason.LOW_CONFIDENCE],
                timestamp=int(time.time() * 1000),
                engine_votes={},
                market_state=market_state,
            )
        
        # Collect votes from all engines
        votes: Dict[str, Action] = {}
        for engine_name, engine in self.engines.items():
            try:
                action = engine(market_state)
                votes[engine_name] = action
            except Exception as e:
                # Engine failed, skip its vote
                print(f"Engine {engine_name} failed: {e}")
                continue
        
        if not votes:
            # All engines failed
            return Decision(
                status=DecisionStatus.BLOCKED,
                action=Action(action_type=ActionType.HOLD, confidence=0.0),
                consensus_confidence=0.0,
                block_reasons=[BlockReason.LOW_CONFIDENCE],
                timestamp=int(time.time() * 1000),
                engine_votes={},
                market_state=market_state,
            )
        
        # Aggregate votes by confidence weighting
        consensus_action, consensus_confidence = self._aggregate_votes(votes)
        
        # Determine status
        status = (
            DecisionStatus.APPROVED
            if consensus_confidence >= self.min_confidence
            else DecisionStatus.BLOCKED
        )
        
        block_reasons = (
            [] if status == DecisionStatus.APPROVED
            else [BlockReason.LOW_CONFIDENCE]
        )
        
        return Decision(
            status=status,
            action=consensus_action,
            consensus_confidence=consensus_confidence,
            block_reasons=block_reasons,
            timestamp=int(time.time() * 1000),
            engine_votes={name: action.model_dump() for name, action in votes.items()},
            market_state=market_state,
        )
    
    async def run_async(self, market_state: MarketState) -> Decision:
        """Run all engines asynchronously and aggregate votes.
        
        Args:
            market_state: Current market state
            
        Returns:
            Decision with consensus action and confidence
        """
        if not self.engines:
            return Decision(
                status=DecisionStatus.BLOCKED,
                action=Action(action_type=ActionType.HOLD, confidence=0.0),
                consensus_confidence=0.0,
                block_reasons=[BlockReason.LOW_CONFIDENCE],
                timestamp=int(time.time() * 1000),
                engine_votes={},
                market_state=market_state,
            )
        
        # Run engines concurrently
        async def run_engine(name: str, engine: Callable) -> tuple[str, Optional[Action]]:
            try:
                # If engine is async, await it; otherwise run in executor
                if asyncio.iscoroutinefunction(engine):
                    action = await engine(market_state)
                else:
                    loop = asyncio.get_event_loop()
                    action = await loop.run_in_executor(None, engine, market_state)
                return name, action
            except Exception as e:
                print(f"Engine {name} failed: {e}")
                return name, None
        
        results = await asyncio.gather(
            *[run_engine(name, engine) for name, engine in self.engines.items()]
        )
        
        votes = {name: action for name, action in results if action is not None}
        
        if not votes:
            return Decision(
                status=DecisionStatus.BLOCKED,
                action=Action(action_type=ActionType.HOLD, confidence=0.0),
                consensus_confidence=0.0,
                block_reasons=[BlockReason.LOW_CONFIDENCE],
                timestamp=int(time.time() * 1000),
                engine_votes={},
                market_state=market_state,
            )
        
        consensus_action, consensus_confidence = self._aggregate_votes(votes)
        
        status = (
            DecisionStatus.APPROVED
            if consensus_confidence >= self.min_confidence
            else DecisionStatus.BLOCKED
        )
        
        block_reasons = [] if status == DecisionStatus.APPROVED else [BlockReason.LOW_CONFIDENCE]
        
        return Decision(
            status=status,
            action=consensus_action,
            consensus_confidence=consensus_confidence,
            block_reasons=block_reasons,
            timestamp=int(time.time() * 1000),
            engine_votes={name: action.model_dump() for name, action in votes.items()},
            market_state=market_state,
        )
    
    def _aggregate_votes(self, votes: Dict[str, Action]) -> tuple[Action, float]:
        """Aggregate engine votes by confidence weighting.
        
        Args:
            votes: Dictionary of engine name to Action vote
            
        Returns:
            Tuple of (consensus_action, consensus_confidence)
        """
        # Weight votes by confidence
        action_scores: Dict[ActionType, float] = {}
        total_confidence = 0.0
        
        for action in votes.values():
            action_scores[action.action_type] = (
                action_scores.get(action.action_type, 0.0) + action.confidence
            )
            total_confidence += action.confidence
        
        if total_confidence == 0:
            # No confidence, return HOLD
            return Action(action_type=ActionType.HOLD, confidence=0.0), 0.0
        
        # Find action with highest weighted score
        best_action_type = max(action_scores, key=action_scores.get)  # type: ignore
        consensus_confidence = action_scores[best_action_type] / total_confidence
        
        # Aggregate other parameters (average from votes for this action)
        matching_votes = [v for v in votes.values() if v.action_type == best_action_type]
        avg_size = sum(v.size_fraction for v in matching_votes) / len(matching_votes)
        avg_leverage = sum(v.leverage for v in matching_votes) / len(matching_votes)
        
        consensus_action = Action(
            action_type=best_action_type,
            confidence=consensus_confidence,
            size_fraction=avg_size,
            leverage=avg_leverage,
        )
        
        return consensus_action, consensus_confidence
    
    def run_and_assert(
        self,
        market_state: MarketState,
        min_confidence: Optional[float] = None,
    ) -> Decision:
        """Run ensemble and enforce minimum confidence threshold.
        
        Args:
            market_state: Current market state
            min_confidence: Override minimum confidence (uses self.min_confidence if None)
            
        Returns:
            Decision with status APPROVED only if confidence >= threshold
        """
        threshold = min_confidence if min_confidence is not None else self.min_confidence
        decision = self.run(market_state)
        
        if decision.consensus_confidence < threshold:
            decision.status = DecisionStatus.BLOCKED
            if BlockReason.LOW_CONFIDENCE not in decision.block_reasons:
                decision.block_reasons.append(BlockReason.LOW_CONFIDENCE)
        
        return decision
