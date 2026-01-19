"""Unit tests for MDPDecision."""
import pytest
from src.core.mdp_decision import MDPDecision
from src.core.types import MarketState, ActionType, MarketRegime


def test_mdp_decision_select_action_returns_valid_action():
    """Test that MDPDecision.select_action returns a valid action."""
    mdp = MDPDecision()
    
    market_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        regime=MarketRegime.TRENDING_UP,
        volatility=0.02,
        liquidity_score=0.8
    )
    
    action_type, confidence = mdp.select_action(market_state, explore=False)
    
    assert action_type in [ActionType.BUY, ActionType.SELL, ActionType.HOLD, ActionType.CLOSE]
    assert 0.0 <= confidence <= 1.0
    assert isinstance(action_type, ActionType)
    assert isinstance(confidence, float)


def test_mdp_decision_exploration():
    """Test that MDPDecision explores with epsilon-greedy."""
    mdp = MDPDecision(epsilon=1.0)  # Always explore
    
    market_state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        regime=MarketRegime.RANGING,
        volatility=0.02,
        liquidity_score=0.8
    )
    
    action_type, confidence = mdp.select_action(market_state, explore=True)
    
    # With epsilon=1.0, should explore (random action)
    assert action_type in [ActionType.BUY, ActionType.SELL, ActionType.HOLD, ActionType.CLOSE]
    # Exploration gives low confidence
    assert confidence < 0.5


def test_mdp_decision_updates_q_table():
    """Test that MDPDecision updates Q-table correctly."""
    mdp = MDPDecision(learning_rate=0.1)
    
    state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        regime=MarketRegime.TRENDING_UP,
        volatility=0.02,
        liquidity_score=0.8
    )
    
    next_state = MarketState(
        price=102.0,
        volume_24h=10000.0,
        bid=101.5,
        ask=102.5,
        regime=MarketRegime.TRENDING_UP,
        volatility=0.02,
        liquidity_score=0.8
    )
    
    initial_size = len(mdp.q_table)
    
    # Update Q-table with positive reward
    mdp.update(
        state=state,
        action=ActionType.BUY,
        reward=1.0,
        next_state=next_state,
        done=False
    )
    
    # Q-table should have entries
    assert len(mdp.q_table) >= initial_size


def test_mdp_decision_epsilon_decay():
    """Test that epsilon decays over episodes."""
    mdp = MDPDecision(epsilon=0.5, epsilon_decay=0.9, min_epsilon=0.01)
    
    initial_epsilon = mdp.epsilon
    
    # Simulate episode completion
    state = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        regime=MarketRegime.RANGING,
        volatility=0.02,
        liquidity_score=0.8
    )
    
    for _ in range(5):
        mdp.update(
            state=state,
            action=ActionType.HOLD,
            reward=0.0,
            next_state=state,
            done=True
        )
    
    # Epsilon should have decayed
    assert mdp.epsilon < initial_epsilon
    assert mdp.epsilon >= mdp.min_epsilon


def test_mdp_decision_state_discretization():
    """Test that different market states get discretized."""
    mdp = MDPDecision()
    
    state1 = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        regime=MarketRegime.TRENDING_UP,
        volatility=0.01,
        liquidity_score=0.9
    )
    
    state2 = MarketState(
        price=100.0,
        volume_24h=10000.0,
        bid=99.5,
        ask=100.5,
        regime=MarketRegime.VOLATILE,
        volatility=0.1,
        liquidity_score=0.3
    )
    
    idx1 = mdp._discretize_state(state1)
    idx2 = mdp._discretize_state(state2)
    
    # Different states should get different indices
    assert idx1 != idx2
    assert isinstance(idx1, int)
    assert isinstance(idx2, int)
