"""Core data types and Pydantic models for the Hyper-Accumulation Bot.

This module defines the fundamental data structures used throughout the bot,
including market state, decisions, actions, and various enums.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ActionType(str, Enum):
    """Types of actions the bot can take."""
    LONG = "long"
    SHORT = "short"
    HOLD = "hold"
    EXIT = "exit"
    REDUCE = "reduce"


class DecisionStatus(str, Enum):
    """Status of a decision."""
    APPROVED = "approved"
    BLOCKED = "blocked"
    PENDING = "pending"


class BlockReason(str, Enum):
    """Reasons why a decision might be blocked."""
    HIGH_MEV_RISK = "high_mev_risk"
    HIGH_LATENCY = "high_latency"
    PRICE_JUMP = "price_jump"
    EMA_DEVIATION = "ema_deviation"
    LOW_VOLUME = "low_volume"
    LOW_CONFIDENCE = "low_confidence"
    CIRCUIT_BREAKER = "circuit_breaker"
    MAX_LOSS_EXCEEDED = "max_loss_exceeded"


class MarketState(BaseModel):
    """Current market state snapshot.
    
    Attributes:
        timestamp: Current time in milliseconds
        symbol: Trading pair symbol
        price: Current price
        bid: Best bid price
        ask: Best ask price
        volume_24h: 24-hour volume
        ema_short: Short-term EMA
        ema_long: Long-term EMA
        volatility: Current volatility estimate
        spread_bps: Bid-ask spread in basis points
        latency_ms: Current RPC latency in milliseconds
        mev_risk_score: Estimated MEV risk (0-1)
        liquidity_depth: Liquidity depth estimate
    """
    model_config = ConfigDict(frozen=False)
    
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    symbol: str = Field(default="SOL/USD", description="Trading pair")
    price: float = Field(..., gt=0, description="Current price")
    bid: float = Field(..., gt=0, description="Best bid")
    ask: float = Field(..., gt=0, description="Best ask")
    volume_24h: float = Field(default=0.0, ge=0, description="24h volume")
    ema_short: Optional[float] = Field(default=None, description="Short EMA")
    ema_long: Optional[float] = Field(default=None, description="Long EMA")
    volatility: float = Field(default=0.0, ge=0, description="Volatility")
    spread_bps: float = Field(default=0.0, ge=0, description="Spread in bps")
    latency_ms: float = Field(default=0.0, ge=0, description="Latency in ms")
    mev_risk_score: float = Field(default=0.0, ge=0, le=1, description="MEV risk")
    liquidity_depth: float = Field(default=0.0, ge=0, description="Liquidity depth")


class Action(BaseModel):
    """Trading action recommendation.
    
    Attributes:
        action_type: Type of action to take
        confidence: Confidence in the action (0-1)
        size_fraction: Fraction of capital to use (0-1)
        leverage: Leverage to apply (1-5)
        stop_loss_pct: Stop loss percentage
        take_profit_pct: Take profit percentage
        metadata: Additional action metadata
    """
    model_config = ConfigDict(frozen=False)
    
    action_type: ActionType = Field(..., description="Action type")
    confidence: float = Field(..., ge=0, le=1, description="Action confidence")
    size_fraction: float = Field(default=0.0, ge=0, le=1, description="Size fraction")
    leverage: float = Field(default=1.0, ge=1, le=5, description="Leverage multiplier")
    stop_loss_pct: Optional[float] = Field(default=None, description="Stop loss %")
    take_profit_pct: Optional[float] = Field(default=None, description="Take profit %")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class Decision(BaseModel):
    """Final trading decision with consensus.
    
    Attributes:
        status: Decision status
        action: Recommended action
        consensus_confidence: Ensemble consensus confidence
        block_reasons: Reasons for blocking (if applicable)
        timestamp: Decision timestamp
        engine_votes: Individual engine votes
        market_state: Market state at decision time
    """
    model_config = ConfigDict(frozen=False)
    
    status: DecisionStatus = Field(..., description="Decision status")
    action: Action = Field(..., description="Recommended action")
    consensus_confidence: float = Field(..., ge=0, le=1, description="Consensus confidence")
    block_reasons: List[BlockReason] = Field(default_factory=list, description="Block reasons")
    timestamp: int = Field(..., description="Decision timestamp ms")
    engine_votes: Dict[str, Any] = Field(default_factory=dict, description="Engine votes")
    market_state: Optional[MarketState] = Field(default=None, description="Market snapshot")


class ExecutionReport(BaseModel):
    """Report from execution layer.
    
    Attributes:
        success: Whether execution succeeded
        transaction_id: Transaction ID (if applicable)
        execution_price: Actual execution price
        slippage_bps: Realized slippage in basis points
        fees: Total fees paid
        latency_ms: Execution latency in milliseconds
        timestamp: Execution timestamp
        error_message: Error message (if failed)
    """
    model_config = ConfigDict(frozen=False)
    
    success: bool = Field(..., description="Execution success")
    transaction_id: Optional[str] = Field(default=None, description="Transaction ID")
    execution_price: Optional[float] = Field(default=None, description="Execution price")
    slippage_bps: float = Field(default=0.0, description="Slippage in bps")
    fees: float = Field(default=0.0, ge=0, description="Total fees")
    latency_ms: float = Field(default=0.0, ge=0, description="Latency in ms")
    timestamp: int = Field(..., description="Execution timestamp ms")
    error_message: Optional[str] = Field(default=None, description="Error message")


class PerformanceMetrics(BaseModel):
    """Performance tracking metrics.
    
    Attributes:
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        total_pnl: Total profit/loss
        win_rate: Win rate (0-1)
        avg_return_pct: Average return percentage
        max_drawdown_pct: Maximum drawdown percentage
        sharpe_ratio: Sharpe ratio
        consecutive_losses: Current consecutive losses
        daily_loss_pct: Current daily loss percentage
    """
    model_config = ConfigDict(frozen=False)
    
    total_trades: int = Field(default=0, ge=0, description="Total trades")
    winning_trades: int = Field(default=0, ge=0, description="Winning trades")
    losing_trades: int = Field(default=0, ge=0, description="Losing trades")
    total_pnl: float = Field(default=0.0, description="Total PnL")
    win_rate: float = Field(default=0.0, ge=0, le=1, description="Win rate")
    avg_return_pct: float = Field(default=0.0, description="Avg return %")
    max_drawdown_pct: float = Field(default=0.0, description="Max drawdown %")
    sharpe_ratio: float = Field(default=0.0, description="Sharpe ratio")
    consecutive_losses: int = Field(default=0, ge=0, description="Consecutive losses")
    daily_loss_pct: float = Field(default=0.0, description="Daily loss %")
