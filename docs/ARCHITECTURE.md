# Architecture Overview

## Solana Hyper-Accumulation Bot v3.0

### System Architecture

The Hyper-Accumulation Bot v3.0 is a modular trading system designed for Solana that combines multiple decision-making engines with risk management and execution layers.

## Core Components

### 1. Decision Pipeline

The bot uses a multi-stage decision pipeline:

```
MarketData → LogicGate → HyperEnsemble → LeverageEngine → Execution
```

#### LogicGate (Axiomatic Filter)

The first line of defense implements deterministic rule-based filters:

- **MEV Risk Check**: Blocks trades when MEV risk score exceeds threshold
- **Latency Filter**: Ensures network latency is acceptable
- **Volume Gate**: Requires minimum 24h volume for liquidity
- **Price Jump Detection**: Blocks on abnormal bid-ask spreads
- **EMA Deviation**: Checks price deviation from moving averages

If any filter fails, the action is blocked immediately with detailed reasons.

#### HyperEnsemble (Multi-Engine Aggregation)

Runs multiple decision engines in parallel and aggregates their votes:

**Engines:**
- **OnflowEngine**: Kelly-criterion-inspired gradient allocation using EWMA estimates
- **MDPDecision**: Q-learning based MDP with discretized state space

**Voting Process:**
1. Each engine returns `(ActionType, confidence)`
2. Votes are weighted by confidence
3. Consensus confidence computed from agreement
4. Minimum confidence threshold enforced (default 0.75)

#### LeverageEngine (Position Sizing)

Determines position size and leverage:
- Base allocation on confidence level
- Adjust for market liquidity and volatility
- Cap at max_position_pct (default 35%)
- Max leverage 5x, reduced in volatile markets

### 2. Execution Layer

Two execution strategies:

#### JitoWarpExecutor
- MEV-protected bundle submission via Jito
- Models network latency (150ms ± 50ms)
- Includes Jito tip fees
- Simulates realistic slippage

#### TWAPExecutor
- Slices large orders into smaller chunks
- Time-weighted execution to minimize impact
- Per-slice slippage tolerance checks
- Uses QuoteClient for real-time pricing

### 3. Simulation Layer

#### PaperTrader
- Simulates trade execution without transactions
- Realistic fee model (0.05% default)
- Size-dependent slippage calculation
- Tracks open positions and P&L

#### MarketSimulator
- **Reuses same decision components as live bot**
- Runs full pipeline: LogicGate → Ensemble → Sizing → PaperTrader
- Respects `execute_trades` flag
- Writes performance metrics to JSON

#### Backtest
- Replays historical bars through decision pipeline
- Same logic as live trading
- Generates performance reports

## Data Flow

### Market State
```python
MarketState(
    price, volume_24h, bid, ask,
    ema_fast, ema_slow, regime,
    volatility, liquidity_score,
    mev_risk_score, latency_ms
)
```

### Decision
```python
Decision(
    action: Action(action_type, size, confidence, leverage),
    consensus_confidence,
    status,
    reasons,
    engine_votes
)
```

## Modes of Operation

### Simulation Mode
- Uses PaperTrader for execution
- No real transactions
- Safe for testing strategies
- Writes to data/performance_stats.json

### Live Mode
- Uses JitoWarpExecutor + TWAPExecutor
- **Requires wallet keypair in environment**
- Real transaction signing and submission
- Requires external integrations (Solana RPC, Jupiter, Drift/Marginfi)

## Safety Features

1. **Logic Gate**: Multi-condition risk filter blocks high-risk trades
2. **Consensus Confidence**: Minimum threshold prevents low-confidence actions
3. **Circuit Breakers**: Max drawdown, consecutive loss limits (config)
4. **Position Limits**: Max 35% of balance, max 5x leverage
5. **Slippage Caps**: Per-trade slippage tolerance checks

## Integration Points

All external services abstracted behind Protocol interfaces:

- `MarketDataFetcher`: Fetch market state (Solana RPC, price feeds)
- `QuoteClient`: Get trade quotes (Jupiter aggregator)
- `ExecutionProvider`: Execute trades (Jito bundles, DEX)
- `MarginProvider`: Request leverage (Drift, Marginfi)

Mock implementations provided for testing without secrets.

## Monitoring

Performance metrics tracked in real-time:
- Total trades, win rate, P&L
- Average win/loss, fees paid
- Current balance, return %
- Open positions count

Metrics persisted to JSON for health checks and alerting.
