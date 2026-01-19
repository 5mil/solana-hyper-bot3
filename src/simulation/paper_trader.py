"""
PaperTrader: Simulated trade execution without real transactions.

Models realistic fees, slippage, and latency for backtesting and simulation.
"""
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from src.core.types import Action, MarketState, ActionType


@dataclass
class SimTrade:
    """A simulated trade with all execution details."""
    timestamp: datetime
    action_type: ActionType
    entry_price: float
    size: float
    leverage: float
    fees_paid: float
    slippage_pct: float
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    exit_fees: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    is_closed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class PaperTrader:
    """
    Paper trading simulator with realistic fee and slippage models.
    
    Simulates trade execution without broadcasting transactions.
    Tracks positions and calculates P&L with realistic costs.
    """
    
    def __init__(
        self,
        initial_balance: float = 100.0,
        fee_pct: float = 0.05,
        base_slippage_pct: float = 0.02,
        latency_ms: float = 100.0
    ):
        """
        Initialize paper trader.
        
        Args:
            initial_balance: Starting balance
            fee_pct: Trading fee percentage
            base_slippage_pct: Base slippage percentage
            latency_ms: Simulated execution latency
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.fee_pct = fee_pct
        self.base_slippage_pct = base_slippage_pct
        self.latency_ms = latency_ms
        
        self.trades: List[SimTrade] = []
        self.open_positions: List[SimTrade] = []
        self.closed_trades: List[SimTrade] = []
    
    def simulate_execution(
        self,
        action: Action,
        market_state: MarketState
    ) -> SimTrade:
        """
        Simulate executing an action.
        
        Args:
            action: Action to execute
            market_state: Current market state
            
        Returns:
            SimTrade with execution details
        """
        # Calculate slippage (higher for larger sizes and lower liquidity)
        size_factor = min(action.size / 1000.0, 1.0)
        liquidity_factor = 1.0 / market_state.liquidity_score
        slippage_pct = self.base_slippage_pct * size_factor * liquidity_factor
        
        # Add some randomness
        slippage_pct *= random.uniform(0.8, 1.2)
        
        # Apply slippage to price
        if action.action_type in [ActionType.BUY]:
            entry_price = market_state.price * (1 + slippage_pct / 100)
        else:
            entry_price = market_state.price * (1 - slippage_pct / 100)
        
        # Calculate fees
        position_value = action.size * entry_price
        fees = position_value * (self.fee_pct / 100)
        
        # Deduct fees from balance
        self.balance -= fees
        
        # Create trade
        trade = SimTrade(
            timestamp=market_state.timestamp,
            action_type=action.action_type,
            entry_price=entry_price,
            size=action.size,
            leverage=action.leverage,
            fees_paid=fees,
            slippage_pct=slippage_pct,
            metadata={
                "confidence": action.confidence,
                "liquidity_score": market_state.liquidity_score
            }
        )
        
        self.trades.append(trade)
        
        # For buy actions, add to open positions
        if action.action_type in [ActionType.BUY]:
            self.open_positions.append(trade)
        
        return trade
    
    def record_exit(
        self,
        trade: SimTrade,
        exit_price: float,
        exit_timestamp: datetime
    ) -> SimTrade:
        """
        Record exit for an open position.
        
        Args:
            trade: Open trade to close
            exit_price: Exit price
            exit_timestamp: Exit timestamp
            
        Returns:
            Updated trade with P&L
        """
        # Calculate exit fees
        exit_value = trade.size * exit_price
        exit_fees = exit_value * (self.fee_pct / 100)
        
        # Calculate P&L
        entry_value = trade.size * trade.entry_price
        pnl = (exit_value - entry_value) * trade.leverage - exit_fees
        pnl_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0.0
        
        # Update trade
        trade.exit_price = exit_price
        trade.exit_timestamp = exit_timestamp
        trade.exit_fees = exit_fees
        trade.pnl = pnl
        trade.pnl_pct = pnl_pct
        trade.is_closed = True
        
        # Update balance
        self.balance += pnl
        
        # Move to closed trades
        if trade in self.open_positions:
            self.open_positions.remove(trade)
        self.closed_trades.append(trade)
        
        return trade
    
    def close_all_positions(
        self,
        market_state: MarketState
    ) -> List[SimTrade]:
        """
        Close all open positions at current market price.
        
        Args:
            market_state: Current market state
            
        Returns:
            List of closed trades
        """
        closed = []
        for trade in list(self.open_positions):
            self.record_exit(
                trade,
                market_state.price,
                market_state.timestamp
            )
            closed.append(trade)
        return closed
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get trading summary statistics.
        
        Returns:
            Summary dictionary with performance metrics
        """
        if not self.closed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "avg_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "total_fees": sum(t.fees_paid for t in self.trades),
                "current_balance": self.balance,
                "return_pct": 0.0
            }
        
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]
        
        total_pnl = sum(t.pnl for t in self.closed_trades)
        total_fees = sum(t.fees_paid + t.exit_fees for t in self.closed_trades)
        
        return {
            "total_trades": len(self.closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(self.closed_trades) * 100,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl / self.initial_balance * 100,
            "avg_pnl": total_pnl / len(self.closed_trades),
            "avg_win": sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0,
            "avg_loss": sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0,
            "total_fees": total_fees,
            "current_balance": self.balance,
            "return_pct": (self.balance - self.initial_balance) / self.initial_balance * 100,
            "open_positions": len(self.open_positions)
        }
