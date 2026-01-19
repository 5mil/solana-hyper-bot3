"""MDP Decision Layer: Q-learning based decision-making.

Implements a simplified Markov Decision Process with discrete states and actions,
using Q-learning to learn optimal policies over time. States are coarsely discretized
market conditions, and actions are trading decisions.
"""

import numpy as np
from typing import Tuple, Dict, Any
from src.core.types import MarketState, ActionType, Action


class MDPDecision:
    """MDP-based decision layer with Q-learning.
    
    Discretizes continuous market state into coarse bins and maintains a Q-table
    for state-action values. Uses epsilon-greedy exploration.
    
    Attributes:
        learning_rate: Q-learning alpha parameter
        discount_factor: Q-learning gamma parameter
        epsilon: Exploration rate for epsilon-greedy
        state_bins: Number of bins for state discretization
        q_table: Q-value table (state -> action -> value)
    """
    
    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.1,
        state_bins: int = 10,
    ):
        """Initialize MDP decision layer.
        
        Args:
            learning_rate: Q-learning alpha (default: 0.1)
            discount_factor: Q-learning gamma (default: 0.95)
            epsilon: Exploration rate (default: 0.1)
            state_bins: Number of state discretization bins (default: 10)
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.state_bins = state_bins
        
        # Q-table: maps (state_hash) -> {action: value}
        self.q_table: Dict[int, Dict[ActionType, float]] = {}
    
    def _discretize_state(self, market_state: MarketState) -> int:
        """Discretize continuous market state into a hash.
        
        Uses price, volatility, and spread to create discrete state buckets.
        
        Args:
            market_state: Current market state
            
        Returns:
            Integer hash representing discretized state
        """
        # Normalize and bin key features
        price_norm = market_state.price % 100 / 100  # Normalize to 0-1
        vol_norm = min(market_state.volatility, 1.0)
        spread_norm = min(market_state.spread_bps / 100, 1.0)
        
        # Create discrete bins
        price_bin = int(price_norm * self.state_bins)
        vol_bin = int(vol_norm * self.state_bins)
        spread_bin = int(spread_norm * self.state_bins)
        
        # Combine into single hash
        state_hash = (
            price_bin * (self.state_bins ** 2) +
            vol_bin * self.state_bins +
            spread_bin
        )
        
        return state_hash
    
    def _get_q_values(self, state_hash: int) -> Dict[ActionType, float]:
        """Get Q-values for a state, initializing if needed.
        
        Args:
            state_hash: Discretized state hash
            
        Returns:
            Dictionary mapping actions to Q-values
        """
        if state_hash not in self.q_table:
            # Initialize with small random values
            self.q_table[state_hash] = {
                action: np.random.uniform(-0.01, 0.01)
                for action in ActionType
            }
        return self.q_table[state_hash]
    
    def select_action(
        self,
        market_state: MarketState,
        confidence: float = 0.5,
    ) -> Action:
        """Select action using epsilon-greedy policy.
        
        Args:
            market_state: Current market state
            confidence: Base confidence for the action
            
        Returns:
            Action with selected type and confidence
        """
        state_hash = self._discretize_state(market_state)
        q_values = self._get_q_values(state_hash)
        
        # Epsilon-greedy selection
        if np.random.random() < self.epsilon:
            # Explore: random action
            action_type = np.random.choice(list(ActionType))
        else:
            # Exploit: best action
            action_type = max(q_values, key=q_values.get)  # type: ignore
        
        # Get Q-value for selected action (normalized confidence boost)
        q_value = q_values[action_type]
        confidence_boost = 1.0 + np.tanh(q_value) * 0.2  # Bounded boost
        
        return Action(
            action_type=action_type,
            confidence=min(confidence * confidence_boost, 1.0),
            size_fraction=0.0,  # Will be set by allocation engine
            metadata={"state_hash": state_hash, "q_value": q_value},
        )
    
    def update(
        self,
        market_state: MarketState,
        action_type: ActionType,
        reward: float,
        next_market_state: MarketState,
    ) -> None:
        """Update Q-values using Q-learning update rule.
        
        Args:
            market_state: Previous market state
            action_type: Action taken
            reward: Reward received
            next_market_state: Resulting market state
        """
        state_hash = self._discretize_state(market_state)
        next_state_hash = self._discretize_state(next_market_state)
        
        q_values = self._get_q_values(state_hash)
        next_q_values = self._get_q_values(next_state_hash)
        
        # Q-learning update: Q(s,a) = Q(s,a) + α[r + γ*max(Q(s',a')) - Q(s,a)]
        current_q = q_values[action_type]
        max_next_q = max(next_q_values.values())
        
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        q_values[action_type] = new_q
    
    def get_state(self) -> Dict[str, Any]:
        """Get current MDP state for logging/monitoring.
        
        Returns:
            Dictionary with Q-table size and parameters
        """
        return {
            "q_table_size": len(self.q_table),
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "epsilon": self.epsilon,
        }
