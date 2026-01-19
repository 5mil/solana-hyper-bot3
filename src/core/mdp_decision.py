"""
MDPDecision: Markov Decision Process with Q-learning.

Implements a simplified MDP with discrete state/action space and
Q-learning for action selection.
"""
import numpy as np
from typing import Tuple, Optional
from src.core.types import MarketState, Action, ActionType, MarketRegime


class MDPDecision:
    """
    MDP decision layer with Q-learning.
    
    Uses coarse discretization of market state and maintains a Q-table
    for action-value estimates. Implements epsilon-greedy exploration.
    """
    
    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01
    ):
        """
        Initialize MDP decision layer.
        
        Args:
            learning_rate: Q-learning learning rate (alpha)
            discount_factor: Q-learning discount factor (gamma)
            epsilon: Exploration rate for epsilon-greedy
            epsilon_decay: Decay rate for epsilon
            min_epsilon: Minimum epsilon value
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        
        # Q-table: state_idx -> action -> value
        self.q_table: dict[int, dict[ActionType, float]] = {}
        
        # Episode counter
        self.episode_count = 0
    
    def _discretize_state(self, market_state: MarketState) -> int:
        """
        Discretize continuous market state to integer state index.
        
        Uses coarse binning of key features: regime, volatility, liquidity.
        
        Args:
            market_state: Current market state
            
        Returns:
            Integer state index
        """
        # Regime: 5 states
        regime_idx = list(MarketRegime).index(market_state.regime)
        
        # Volatility: 3 bins (low, medium, high)
        if market_state.volatility < 0.02:
            vol_idx = 0
        elif market_state.volatility < 0.05:
            vol_idx = 1
        else:
            vol_idx = 2
        
        # Liquidity: 3 bins (low, medium, high)
        if market_state.liquidity_score < 0.4:
            liq_idx = 0
        elif market_state.liquidity_score < 0.7:
            liq_idx = 1
        else:
            liq_idx = 2
        
        # Combine into single state index
        # 5 regimes * 3 volatility * 3 liquidity = 45 states
        state_idx = regime_idx * 9 + vol_idx * 3 + liq_idx
        
        return state_idx
    
    def _init_state(self, state_idx: int):
        """Initialize Q-values for a new state."""
        if state_idx not in self.q_table:
            self.q_table[state_idx] = {
                ActionType.BUY: 0.0,
                ActionType.SELL: 0.0,
                ActionType.HOLD: 0.0,
                ActionType.CLOSE: 0.0
            }
    
    def select_action(
        self,
        market_state: MarketState,
        explore: bool = True
    ) -> Tuple[ActionType, float]:
        """
        Select action using epsilon-greedy Q-learning.
        
        Args:
            market_state: Current market state
            explore: Whether to use epsilon-greedy exploration
            
        Returns:
            Tuple of (action_type, confidence)
        """
        state_idx = self._discretize_state(market_state)
        self._init_state(state_idx)
        
        # Epsilon-greedy exploration
        if explore and np.random.random() < self.epsilon:
            # Random action
            import random
            action_type = random.choice(list(ActionType))
            confidence = 0.3  # Low confidence for random actions
        else:
            # Greedy action (highest Q-value)
            q_values = self.q_table[state_idx]
            action_type = max(q_values, key=q_values.get)
            
            # Confidence based on Q-value and spread
            max_q = q_values[action_type]
            avg_q = np.mean(list(q_values.values()))
            
            # Confidence higher when Q-value is clearly better
            if max_q > avg_q:
                confidence = min(0.9, 0.5 + (max_q - avg_q) * 2)
            else:
                confidence = 0.5
        
        return action_type, confidence
    
    def update(
        self,
        state: MarketState,
        action: ActionType,
        reward: float,
        next_state: MarketState,
        done: bool = False
    ):
        """
        Update Q-values using Q-learning update rule.
        
        Args:
            state: Previous state
            action: Action taken
            reward: Reward received
            next_state: New state after action
            done: Whether episode ended
        """
        state_idx = self._discretize_state(state)
        next_state_idx = self._discretize_state(next_state)
        
        self._init_state(state_idx)
        self._init_state(next_state_idx)
        
        # Q-learning update: Q(s,a) += α * (r + γ * max_a' Q(s',a') - Q(s,a))
        current_q = self.q_table[state_idx][action]
        
        if done:
            target = reward
        else:
            max_next_q = max(self.q_table[next_state_idx].values())
            target = reward + self.discount_factor * max_next_q
        
        self.q_table[state_idx][action] += self.learning_rate * (target - current_q)
        
        # Decay epsilon
        if done:
            self.episode_count += 1
            self.epsilon = max(
                self.min_epsilon,
                self.epsilon * self.epsilon_decay
            )
    
    def get_state(self) -> dict:
        """Get current engine state for monitoring."""
        return {
            "episode_count": self.episode_count,
            "epsilon": self.epsilon,
            "q_table_size": len(self.q_table)
        }
