"""
HyperEnsemble: Ensemble coordinator for multiple decision engines.

Aggregates votes from multiple engines by confidence weighting and
computes consensus confidence. Provides run_and_assert for minimum
confidence enforcement.
"""
import asyncio
from typing import List, Optional, Callable
from src.core.types import (
    MarketState, Action, Decision, EngineVote,
    ActionType, DecisionStatus
)


class HyperEnsemble:
    """
    Ensemble coordinator that runs multiple decision engines.
    
    Aggregates votes from multiple engines using confidence-weighted
    voting. Can run engines synchronously or asynchronously.
    """
    
    def __init__(
        self,
        engines: Optional[List[tuple[str, Callable]]] = None,
        vote_aggregation_method: str = "weighted"
    ):
        """
        Initialize HyperEnsemble.
        
        Args:
            engines: List of (name, engine_callable) tuples
            vote_aggregation_method: Method for aggregating votes ("weighted", "majority")
        """
        self.engines = engines or []
        self.vote_aggregation_method = vote_aggregation_method
    
    def add_engine(self, name: str, engine_callable: Callable):
        """
        Add an engine to the ensemble.
        
        Args:
            name: Engine name
            engine_callable: Callable that takes MarketState and returns (ActionType, confidence)
        """
        self.engines.append((name, engine_callable))
    
    def run_sync(self, market_state: MarketState) -> Decision:
        """
        Run all engines synchronously and aggregate votes.
        
        Args:
            market_state: Current market state
            
        Returns:
            Decision with aggregated action and consensus confidence
        """
        votes: List[EngineVote] = []
        
        for engine_name, engine_callable in self.engines:
            try:
                # Engine should return (ActionType, confidence)
                action_type, confidence = engine_callable(market_state)
                
                # Create action with basic sizing
                action = Action(
                    action_type=action_type,
                    size=1.0,  # Size to be adjusted by leverage engine
                    confidence=confidence
                )
                
                vote = EngineVote(
                    engine_name=engine_name,
                    action=action,
                    confidence=confidence
                )
                votes.append(vote)
            except Exception as e:
                # Engine failed, skip it
                print(f"Warning: Engine {engine_name} failed: {e}")
                continue
        
        return self._aggregate_votes(votes, market_state)
    
    async def run_async(self, market_state: MarketState) -> Decision:
        """
        Run all engines asynchronously and aggregate votes.
        
        Args:
            market_state: Current market state
            
        Returns:
            Decision with aggregated action and consensus confidence
        """
        async def run_engine(name: str, engine_callable: Callable) -> Optional[EngineVote]:
            try:
                # If engine is async
                if asyncio.iscoroutinefunction(engine_callable):
                    action_type, confidence = await engine_callable(market_state)
                else:
                    action_type, confidence = engine_callable(market_state)
                
                action = Action(
                    action_type=action_type,
                    size=1.0,
                    confidence=confidence
                )
                
                return EngineVote(
                    engine_name=name,
                    action=action,
                    confidence=confidence
                )
            except Exception as e:
                print(f"Warning: Engine {name} failed: {e}")
                return None
        
        # Run all engines concurrently
        tasks = [run_engine(name, engine) for name, engine in self.engines]
        results = await asyncio.gather(*tasks)
        
        # Filter out failed engines
        votes = [v for v in results if v is not None]
        
        return self._aggregate_votes(votes, market_state)
    
    def _aggregate_votes(
        self,
        votes: List[EngineVote],
        market_state: MarketState
    ) -> Decision:
        """
        Aggregate votes from engines into a single decision.
        
        Args:
            votes: List of engine votes
            market_state: Current market state
            
        Returns:
            Aggregated Decision
        """
        if not votes:
            # No votes, return HOLD with low confidence
            return Decision(
                action=Action(
                    action_type=ActionType.HOLD,
                    size=0.0,
                    confidence=0.0
                ),
                consensus_confidence=0.0,
                status=DecisionStatus.BLOCKED,
                reasons=["No engine votes received"],
                engine_votes={}
            )
        
        # Count votes by action type, weighted by confidence
        vote_weights: dict[ActionType, float] = {}
        vote_counts: dict[ActionType, int] = {}
        
        for vote in votes:
            action_type = vote.action.action_type
            vote_weights[action_type] = vote_weights.get(action_type, 0.0) + vote.confidence
            vote_counts[action_type] = vote_counts.get(action_type, 0) + 1
        
        # Select action with highest weighted vote
        chosen_action_type = max(vote_weights, key=vote_weights.get)
        
        # Compute consensus confidence
        total_confidence = sum(vote_weights.values())
        if total_confidence > 0:
            consensus_confidence = vote_weights[chosen_action_type] / total_confidence
        else:
            consensus_confidence = 0.0
        
        # Adjust consensus by agreement (boost if multiple engines agree)
        agreement_factor = vote_counts[chosen_action_type] / len(votes)
        consensus_confidence = consensus_confidence * (0.7 + 0.3 * agreement_factor)
        consensus_confidence = min(consensus_confidence, 1.0)
        
        # Create final action
        final_action = Action(
            action_type=chosen_action_type,
            size=1.0,  # Will be sized by leverage engine
            confidence=consensus_confidence
        )
        
        # Build engine votes dict for transparency
        engine_votes_dict = {
            vote.engine_name: {
                "action": vote.action.action_type.value,
                "confidence": vote.confidence
            }
            for vote in votes
        }
        
        return Decision(
            action=final_action,
            consensus_confidence=consensus_confidence,
            status=DecisionStatus.APPROVED,
            reasons=[f"{len(votes)} engines voted"],
            engine_votes=engine_votes_dict
        )
    
    def run_and_assert(
        self,
        market_state: MarketState,
        min_confidence: float = 0.75
    ) -> Optional[Decision]:
        """
        Run ensemble and enforce minimum confidence threshold.
        
        Args:
            market_state: Current market state
            min_confidence: Minimum consensus confidence required
            
        Returns:
            Decision if confidence >= min_confidence, None otherwise
        """
        decision = self.run_sync(market_state)
        
        if decision.consensus_confidence < min_confidence:
            decision.status = DecisionStatus.BLOCKED
            decision.reasons.append(
                f"Consensus confidence {decision.consensus_confidence:.2f} < {min_confidence}"
            )
            return None
        
        return decision
