"""
Core type definitions and Pydantic models for the Hyper-Accumulation Bot v3.0.

This module defines all shared types, enums, and data models used throughout the system.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone


class ActionType(str, Enum):
    """Enum for action types the bot can take."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class MarketRegime(str, Enum):
    """Market regime classification."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class DecisionStatus(str, Enum):
    """Status of a decision."""
    APPROVED = "approved"
    BLOCKED = "blocked"
    PENDING = "pending"


class MarketState(BaseModel):
    """
    Current market state snapshot.
    
    Contains all relevant market data needed for decision making.
    """
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str = Field(default="SOL/USD")
    price: float = Field(gt=0)
    volume_24h: float = Field(ge=0)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    regime: MarketRegime = MarketRegime.UNKNOWN
    volatility: float = Field(ge=0, default=0.0)
    liquidity_score: float = Field(ge=0, le=1, default=1.0)
    mev_risk_score: float = Field(ge=0, le=1, default=0.0)
    latency_ms: float = Field(ge=0, default=0.0)


class Action(BaseModel):
    """
    An action to be taken by the bot.
    
    Represents a specific trade action with sizing and metadata.
    """
    action_type: ActionType
    size: float = Field(ge=0)
    price: Optional[float] = None
    confidence: float = Field(ge=0, le=1)
    leverage: float = Field(ge=1, le=5, default=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"Action({self.action_type.value}, size={self.size:.4f}, conf={self.confidence:.2f})"


class Decision(BaseModel):
    """
    A decision from the ensemble system.
    
    Contains the recommended action, consensus confidence, and reasoning.
    """
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    action: Action
    consensus_confidence: float = Field(ge=0, le=1)
    status: DecisionStatus = DecisionStatus.PENDING
    reasons: List[str] = Field(default_factory=list)
    engine_votes: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __str__(self) -> str:
        return f"Decision({self.action.action_type.value}, conf={self.consensus_confidence:.2f}, status={self.status.value})"


class FilterResult(BaseModel):
    """
    Result from a logic gate filter.
    
    Indicates whether an action should be allowed or blocked with reasons.
    """
    allowed: bool
    reasons: List[str] = Field(default_factory=list)
    risk_score: float = Field(ge=0, le=1, default=0.0)
    
    def __str__(self) -> str:
        status = "ALLOW" if self.allowed else "BLOCK"
        return f"FilterResult({status}, risk={self.risk_score:.2f})"


class EngineVote(BaseModel):
    """
    A vote from a single decision engine.
    
    Contains the recommended action and confidence from one engine.
    """
    engine_name: str
    action: Action
    confidence: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
