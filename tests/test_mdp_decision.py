"""Unit tests for MDPDecision."""

import pytest
from src.core.mdp_decision import MDPDecision
from src.core.types import MarketState, ActionType


def test_mdp_decision_initialization():
    """Test MDPDecision initializes correctly."""
    mdp = MDPDecision(learning_rate=0.1, discount_factor=0.95, epsilon=0.1)
    
    assert mdp.learning_rate == 0.1
    assert mdp.discount_factor == 0.95
    assert mdp.epsilon == 0.1
    assert len(mdp.q_table) == 0


def test_mdp_select_action_returns_valid_action():
    """Test that select_action returns a valid action."""
    mdp = MDPDecision()
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        volatility=0.02,
        spread_bps=100.0,
    )
    
    action = mdp.select_action(market_state, confidence=0.7)
    
    assert isinstance(action.action_type, ActionType), "Should return valid ActionType"
    assert 0 <= action.confidence <= 1, "Confidence should be in [0, 1]"
    assert "state_hash" in action.metadata, "Should include state hash in metadata"
    assert "q_value" in action.metadata, "Should include Q-value in metadata"


def test_mdp_action_type_is_valid():
    """Test that returned action type is one of the valid enum values."""
    mdp = MDPDecision(epsilon=0.0)  # No exploration for deterministic test
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        volatility=0.01,
        spread_bps=50.0,
    )
    
    # Run multiple times to ensure consistency
    for _ in range(5):
        action = mdp.select_action(market_state)
        assert action.action_type in list(ActionType), "Action type must be valid"


def test_mdp_update_increases_q_table_size():
    """Test that update method adds entries to Q-table."""
    mdp = MDPDecision()
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        volatility=0.02,
        spread_bps=100.0,
    )
    
    next_market_state = MarketState(
        timestamp=1001000,
        price=101.0,
        bid=100.0,
        ask=102.0,
        volatility=0.02,
        spread_bps=100.0,
    )
    
    initial_size = len(mdp.q_table)
    
    mdp.update(market_state, ActionType.LONG, reward=0.1, next_market_state=next_market_state)
    
    # Q-table should have entries now
    assert len(mdp.q_table) > initial_size, "Q-table should grow after update"


def test_mdp_q_learning_updates_values():
    """Test that Q-learning updates Q-values correctly."""
    mdp = MDPDecision(learning_rate=0.5, epsilon=0.0)
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        volatility=0.02,
        spread_bps=100.0,
    )
    
    # Get initial action
    action = mdp.select_action(market_state)
    state_hash = action.metadata["state_hash"]
    initial_q = mdp.q_table[state_hash][action.action_type]
    
    # Update with positive reward
    next_market_state = MarketState(
        timestamp=1001000,
        price=102.0,
        bid=101.0,
        ask=103.0,
        volatility=0.02,
        spread_bps=100.0,
    )
    
    mdp.update(market_state, action.action_type, reward=1.0, next_market_state=next_market_state)
    
    # Q-value should have changed
    updated_q = mdp.q_table[state_hash][action.action_type]
    assert updated_q != initial_q, "Q-value should update"
    assert updated_q > initial_q, "Q-value should increase with positive reward"


def test_mdp_state_export():
    """Test that MDP can export its state."""
    mdp = MDPDecision()
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        volatility=0.02,
        spread_bps=100.0,
    )
    
    # Add some experience
    mdp.select_action(market_state)
    
    state = mdp.get_state()
    
    assert "q_table_size" in state
    assert "learning_rate" in state
    assert "discount_factor" in state
    assert "epsilon" in state
    assert state["q_table_size"] > 0


def test_mdp_exploration_with_epsilon():
    """Test that epsilon-greedy exploration works."""
    mdp = MDPDecision(epsilon=1.0)  # Always explore
    
    market_state = MarketState(
        timestamp=1000000,
        price=100.0,
        bid=99.0,
        ask=101.0,
        volatility=0.02,
        spread_bps=100.0,
    )
    
    # With epsilon=1.0, should get random actions
    actions = set()
    for _ in range(20):
        action = mdp.select_action(market_state)
        actions.add(action.action_type)
    
    # Should see variety in actions due to exploration
    assert len(actions) > 1, "Should explore different actions with high epsilon"
