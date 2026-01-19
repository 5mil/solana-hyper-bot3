"""Paper Trader: Simulated trade execution and tracking.

The PaperTrader simulates trade execution without broadcasting transactions.
Models realistic fees, slippage, and maintains position tracking.
"""

import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from src.core.types import Action, MarketState, ActionType


@dataclass
class SimTrade:
    """Simulated trade record.
    
    Attributes:
        trade_id: Unique trade identifier
        timestamp: Trade timestamp in milliseconds
        action_type: Type of action taken
        entry_price: Entry price
        exit_price: Exit price (None if still open)
        size_usd: Position size in USD
        leverage: Leverage used
        fees: Total fees paid
        slippage_bps: Slippage in basis points
        pnl: Profit/loss (None if still open)
        is_closed: Whether position is closed
    """
    trade_id: str
    timestamp: int
    action_type: ActionType
    entry_price: float
    exit_price: Optional[float]
    size_usd: float
    leverage: float
    fees: float
    slippage_bps: float
    pnl: Optional[float]
    is_closed: bool


class PaperTrader:
    """Paper trading simulator with realistic fee and slippage models.
    
    Simulates trade execution without real transactions, maintaining
    position state and computing realistic costs.
    
    Attributes:
        base_fee_bps: Base trading fee in basis points
        slippage_model: Function to compute slippage based on size and volatility
        initial_capital: Starting capital
        current_capital: Current capital
        trades: List of all simulated trades
        open_positions: Currently open positions
    """
    
    def __init__(
        self,
        initial_capital: float = 100.0,
        base_fee_bps: float = 5.0,
        base_slippage_bps: float = 3.0,
    ):
        """Initialize PaperTrader.
        
        Args:
            initial_capital: Starting capital (default: 100.0)
            base_fee_bps: Base fee in bps (default: 5.0)
            base_slippage_bps: Base slippage in bps (default: 3.0)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.base_fee_bps = base_fee_bps
        self.base_slippage_bps = base_slippage_bps
        
        self.trades: List[SimTrade] = []
        self.open_positions: Dict[str, SimTrade] = {}
        self.trade_counter = 0
    
    def simulate_execution(
        self,
        action: Action,
        market_state: MarketState,
        size_usd: float,
    ) -> SimTrade:
        """Simulate trade execution.
        
        Args:
            action: Action to execute
            market_state: Current market state
            size_usd: Position size in USD
            
        Returns:
            SimTrade record
        """
        self.trade_counter += 1
        trade_id = f"sim_trade_{self.trade_counter}"
        
        # Compute slippage based on size and volatility
        size_factor = min(size_usd / 10000, 1.0)  # Larger orders = more slippage
        volatility_factor = market_state.volatility
        total_slippage_bps = self.base_slippage_bps * (1 + size_factor + volatility_factor)
        
        # Compute entry price with slippage
        if action.action_type in [ActionType.LONG]:
            # Buying - pay ask + slippage
            entry_price = market_state.ask * (1 + total_slippage_bps / 10000)
        else:
            # Selling - receive bid - slippage
            entry_price = market_state.bid * (1 - total_slippage_bps / 10000)
        
        # Compute fees
        fees = size_usd * (self.base_fee_bps / 10000)
        
        trade = SimTrade(
            trade_id=trade_id,
            timestamp=int(time.time() * 1000),
            action_type=action.action_type,
            entry_price=entry_price,
            exit_price=None,
            size_usd=size_usd,
            leverage=action.leverage,
            fees=fees,
            slippage_bps=total_slippage_bps,
            pnl=None,
            is_closed=False,
        )
        
        # Add to open positions
        self.open_positions[trade_id] = trade
        self.trades.append(trade)
        
        # Deduct fees from capital
        self.current_capital -= fees
        
        return trade
    
    def record_exit(
        self,
        trade_id: str,
        market_state: MarketState,
    ) -> Optional[SimTrade]:
        """Record position exit and compute PnL.
        
        Args:
            trade_id: Trade ID to close
            market_state: Current market state
            
        Returns:
            Updated SimTrade with PnL, or None if trade not found
        """
        if trade_id not in self.open_positions:
            return None
        
        trade = self.open_positions[trade_id]
        
        # Compute exit price with slippage
        size_factor = min(trade.size_usd / 10000, 1.0)
        volatility_factor = market_state.volatility
        exit_slippage_bps = self.base_slippage_bps * (1 + size_factor + volatility_factor)
        
        if trade.action_type == ActionType.LONG:
            # Closing long - sell at bid - slippage
            exit_price = market_state.bid * (1 - exit_slippage_bps / 10000)
        else:
            # Closing short - buy at ask + slippage
            exit_price = market_state.ask * (1 + exit_slippage_bps / 10000)
        
        # Compute PnL
        if trade.action_type == ActionType.LONG:
            price_change_pct = (exit_price - trade.entry_price) / trade.entry_price
        else:
            price_change_pct = (trade.entry_price - exit_price) / trade.entry_price
        
        # Apply leverage
        leveraged_return_pct = price_change_pct * trade.leverage
        pnl = trade.size_usd * leveraged_return_pct
        
        # Deduct exit fees
        exit_fees = trade.size_usd * (self.base_fee_bps / 10000)
        pnl -= exit_fees
        
        # Update trade
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.is_closed = True
        trade.fees += exit_fees
        
        # Update capital
        self.current_capital += pnl
        
        # Remove from open positions
        del self.open_positions[trade_id]
        
        return trade
    
    def close_all_positions(self, market_state: MarketState) -> List[SimTrade]:
        """Close all open positions.
        
        Args:
            market_state: Current market state
            
        Returns:
            List of closed trades
        """
        closed_trades = []
        trade_ids = list(self.open_positions.keys())
        
        for trade_id in trade_ids:
            closed_trade = self.record_exit(trade_id, market_state)
            if closed_trade:
                closed_trades.append(closed_trade)
        
        return closed_trades
    
    def summary(self) -> Dict[str, Any]:
        """Generate performance summary.
        
        Returns:
            Dictionary with performance metrics
        """
        closed_trades = [t for t in self.trades if t.is_closed]
        
        if not closed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_fees": 0.0,
                "avg_pnl": 0.0,
                "return_pct": 0.0,
                "current_capital": self.current_capital,
            }
        
        winning_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl and t.pnl <= 0]
        
        total_pnl = sum(t.pnl for t in closed_trades if t.pnl is not None)
        total_fees = sum(t.fees for t in self.trades)
        
        return {
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(closed_trades) if closed_trades else 0.0,
            "total_pnl": total_pnl,
            "total_fees": total_fees,
            "avg_pnl": total_pnl / len(closed_trades) if closed_trades else 0.0,
            "return_pct": (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            "current_capital": self.current_capital,
        }
