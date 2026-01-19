# Architecture Overview

## Solana Hyper-Accumulation Bot v3.0

The Hyper-Accumulation Bot v3.0 is a production-grade algorithmic trading system designed for Solana markets. It implements a sophisticated multi-layer decision-making pipeline with risk management, position sizing, and high-performance execution.

## System Architecture

### Decision Pipeline

The bot processes each market cycle through the following stages:

```
Market Data → Logic Gate → Hyper Ensemble → Position Sizing → Execution
     ↓            ↓              ↓                ↓               ↓
  Fetchers    Hard Rules    ML Consensus      Kelly-like      Jito/TWAP
```

### Component Layers

#### 1. Core Decision Layer (`src/core/`)

**LogicGate** - Deterministic axiomatic filter
- Implements hard constraints that must be satisfied before trading
- Filters based on MEV risk, latency, price jumps, EMA deviation, and volume
- Returns `allow/block` with specific reasons
- First line of defense against adverse conditions

**OnflowEngine** - Gradient allocation with Kelly criterion
- Maintains EWMA (Exponentially Weighted Moving Average) estimates
- Tracks win rate and average returns
- Computes optimal allocation fraction using Kelly-like formula
- Dynamically adjusts position sizes based on recent performance

**MDPDecision** - Markov Decision Process with Q-learning
- Discretizes continuous market state into coarse bins
- Maintains Q-table for state-action values
- Uses epsilon-greedy exploration strategy
- Learns optimal policies over time through reinforcement learning

**HyperEnsemble** - Multi-engine coordination and consensus
- Aggregates votes from multiple decision engines
- Weighs votes by confidence
- Computes consensus confidence and action
- Enforces minimum confidence thresholds (default: 0.75)
- Can run engines synchronously or asynchronously

#### 2. Execution Layer (`src/execution/`)

**LeverageEngine** - Position sizing and margin management
- Enforces max leverage constraint (default: 5x)
- Caps position size (default: 35% of capital)
- Implements Kelly-like allocation with safety bounds
- Provides margin request interface for leveraged positions

**JitoWarpExecutor** - MEV-protected bundle submission
- Simulates Jito bundle submission with realistic latency
- Models tip calculation and inclusion probability
- Estimates slippage based on timing and market conditions
- In production, would submit actual Jito bundles

**TWAPExecutor** - Time-weighted average price execution
- Slices large orders into smaller pieces
- Executes over time to reduce market impact
- Checks slippage tolerance before each slice
- Uses QuoteProvider for real-time price quotes

#### 3. Simulation Layer (`src/simulation/`)

**PaperTrader** - Simulated trade execution
- Executes trades without blockchain transactions
- Models realistic fees, slippage, and latency
- Tracks position state and computes PnL
- Provides performance summary

**MarketSimulator** - High-fidelity simulation
- Uses the same decision components as live bot
- Runs LogicGate → Ensemble → Sizing → PaperTrader
- Never signs or broadcasts transactions
- Writes JSON reports with metrics

**Backtest** - Historical data replay
- Accepts historical OHLCV bars
- Replays through decision pipeline
- Uses same components as live trading
- Generates backtest performance reports

#### 4. Live Bot (`src/live_bot.py`)

**LiveBot** - Main trading loop
- Supports both simulation and live modes
- Each cycle:
  1. Fetch market state
  2. Run LogicGate (return early if blocked)
  3. Run HyperEnsemble (return early if low confidence)
  4. Size position via LeverageEngine
  5. Execute via appropriate executor
- Persists metrics to JSON
- Implements circuit breaker logic
- Provides health check interface

### Data Flow

1. **Market Data Ingestion**: MarketDataFetcher pulls data from Solana RPC, Jupiter, etc.
2. **Risk Filtering**: LogicGate applies hard constraints
3. **Decision Making**: HyperEnsemble aggregates ML engine votes
4. **Position Sizing**: OnflowEngine and LeverageEngine compute optimal size
5. **Execution**: JitoWarp or TWAP executes with MEV protection
6. **Metrics**: Performance tracked and persisted to JSON

### Protocol Interfaces

All external integrations are abstracted behind Protocol interfaces:

- `MarketDataFetcher`: Fetch market state from various sources
- `ExecutionProvider`: Execute trades through different venues
- `QuoteProvider`: Get trade quotes from DEX aggregators
- `MarginProvider`: Request margin from lending protocols

This allows:
- Easy mocking for tests
- Swapping implementations without code changes
- Safe simulation without secrets

### Risk Management

**Circuit Breaker** triggers on:
- Max drawdown threshold (default: 25%)
- Daily loss limit (default: 15%)
- Consecutive losses (default: 5)

**Position Limits**:
- Max leverage: 5x
- Max position: 35% of capital
- Min confidence: 75% consensus

**Slippage Protection**:
- Slippage cap (default: 50 bps)
- Per-slice checks in TWAP
- MEV risk filtering

## Configuration

- `config/bot_config.json`: Core bot parameters
- `config/live_runtime.json`: Runtime endpoints and settings
- `config/simulation_config.json`: Simulation-specific settings
- `config/secrets.template.json`: Required environment variables (no actual secrets)

## Testing Strategy

- Unit tests for each core component
- Integration tests with mock adapters
- Simulation runs with paper trading
- Backtest validation with historical data
- All tests use deterministic mocks

## Deployment

See `docs/DEPLOYMENT_GUIDE.md` for Docker build and deployment instructions.

## Extensibility

To add new decision engines:
1. Implement callable that takes `MarketState` and returns `Action`
2. Register with `HyperEnsemble.add_engine()`
3. Engine votes will be included in consensus

To add new execution venues:
1. Implement `ExecutionProvider` protocol
2. Pass to LiveBot constructor
3. Use in live mode execution

## Security

- No secrets in code or configs
- All external integrations behind interfaces
- Simulation never signs transactions
- Circuit breaker prevents runaway losses
- MEV risk filtering
