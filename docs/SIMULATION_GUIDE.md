# Simulation Guide

## Overview

The Solana Hyper-Accumulation Bot v3.0 includes a high-fidelity simulation layer that allows testing the full decision pipeline without risking capital or requiring live API connections.

## Simulation Modes

### 1. Local Simulation

Run simulations locally using mock adapters:

```bash
python tools/run_simulation.py
```

This uses:
- `MockQuoteClient` for price quotes
- `DummyMarketFetcher` for market data
- `PaperTrader` for trade execution
- No blockchain interaction
- No secrets required

### 2. CI Simulation

Automated simulations in GitHub Actions:

```bash
# Triggered by workflow_dispatch or PR
.github/workflows/test-simulation.yml
```

Features:
- Configurable duration and iterations
- Performance threshold validation
- Artifact upload for analysis
- PR comment with results

## Simulation Configuration

Edit `config/simulation_config.json`:

```json
{
  "execute_trades": false,     // Set to true to simulate execution
  "iterations": 100,            // Number of cycles to run
  "delay_sec": 0.1,            // Delay between cycles
  "metrics_path": "data/simulation_stats.json",
  "output_report": "data/simulation_report.json"
}
```

## How Simulation Works

### Components Used

The simulator uses the **exact same decision components** as the live bot:

1. **LogicGate**: Same filtering rules
2. **HyperEnsemble**: Same ML engines and consensus
3. **OnflowEngine**: Same Kelly allocation
4. **MDPDecision**: Same Q-learning
5. **LeverageEngine**: Same position sizing

The only difference is execution:
- **Simulation**: PaperTrader (no transactions)
- **Live**: JitoWarpExecutor + TWAPExecutor (real transactions)

### Realistic Modeling

The simulation includes realistic models for:

**Fees**:
- Base trading fee: 5 bps
- Jito tip: ~10,000 lamports
- Network fees: ~5,000 lamports

**Slippage**:
- Base slippage: 3 bps
- Size impact: Scales with order size
- Volatility impact: Scales with market volatility
- Formula: `slippage = base * (1 + size_factor + volatility_factor)`

**Latency**:
- Network latency: 100-200ms
- Bundle building: 50-100ms
- Execution delays modeled

**Market Impact**:
- Larger orders → more slippage
- TWAP reduces impact over time
- Volume affects available liquidity

### Paper Trading

`PaperTrader` maintains:
- Current capital
- Open positions
- Trade history
- Performance metrics

Features:
- Simulates entry/exit prices with slippage
- Deducts fees from capital
- Computes PnL with leverage
- Tracks win rate and returns

### Market Simulation

`MarketSimulator` runs the full pipeline:

```python
from src.simulation.market_simulator import MarketSimulator

simulator = MarketSimulator(
    market_fetcher=mock_fetcher,
    initial_capital=100.0,
    execute_trades=True,  # Enable trade simulation
    min_confidence=0.75,
)

summary = simulator.run(
    iterations=100,
    delay_sec=0.1,
    output_path="data/report.json",
)
```

Output includes:
- Total iterations
- Decisions made
- Trades executed
- Win rate
- Total PnL
- Current capital
- Iteration-by-iteration results

## Running Simulations

### Quick Local Test

```bash
# Install dependencies
pip install -r requirements.txt

# Run simulation
python tools/run_simulation.py

# Check results
cat data/simulation_report.json
```

### Extended Simulation

```bash
# Edit config for longer run
# Set iterations: 1000 in config/simulation_config.json

python tools/run_simulation.py

# Analyze results
python -c "
import json
with open('data/simulation_report.json') as f:
    data = json.load(f)
    perf = data['summary']['trading_performance']
    print(f\"Win Rate: {perf['win_rate']:.1%}\")
    print(f\"Total PnL: ${perf['total_pnl']:.2f}\")
    print(f\"Return: {perf['return_pct']:.1f}%\")
"
```

### Docker Simulation

```bash
# Build image
docker build -t hyper-bot3:latest .

# Run simulation
docker run --rm \
  -v $(pwd)/data:/app/data \
  hyper-bot3:latest \
  python tools/run_simulation.py
```

## Output Files

### Simulation Report (`data/simulation_report.json`)

```json
{
  "summary": {
    "simulation_complete": true,
    "total_iterations": 100,
    "decisions_made": 85,
    "trades_executed": 42,
    "trading_performance": {
      "total_trades": 42,
      "winning_trades": 38,
      "losing_trades": 4,
      "win_rate": 0.905,
      "total_pnl": 45.2,
      "return_pct": 45.2
    }
  },
  "iterations": [...]
}
```

### Performance Stats (`data/performance_stats.json`)

```json
{
  "total_trades": 42,
  "winning_trades": 38,
  "losing_trades": 4,
  "win_rate": 0.905,
  "total_pnl": 45.2,
  "avg_return_pct": 1.08,
  "max_drawdown_pct": 5.2,
  "sharpe_ratio": 2.1
}
```

## Performance Thresholds

CI simulations enforce thresholds (see `.github/workflows/test-simulation.yml`):

- **Win Rate**: ≥ 90%
- **Avg Monthly Return**: ≥ 45%
- **Max Drawdown**: ≤ 10%

Simulations failing these thresholds block promotion to production.

## Customizing Market Data

Create custom `MarketDataFetcher`:

```python
from src.core.types import MarketState

class CustomFetcher:
    def fetch_market_state(self, symbol: str = "SOL/USD") -> MarketState:
        # Your custom logic
        return MarketState(
            timestamp=...,
            price=...,
            bid=...,
            ask=...,
            # ... other fields
        )

# Use in simulator
simulator = MarketSimulator(market_fetcher=CustomFetcher())
```

## Backtesting

Test on historical data:

```python
from src.simulation.backtest import Backtest, HistoricalBar

bars = [
    HistoricalBar(timestamp=..., open=..., high=..., low=..., close=..., volume=...),
    # ... more bars
]

backtest = Backtest(initial_capital=100.0)
summary = backtest.run(bars, output_path="data/backtest_report.json")
```

## Best Practices

1. **Start with short simulations** (10-100 iterations) during development
2. **Run extended simulations** (1000+ iterations) before deployment
3. **Analyze iteration logs** to understand decision patterns
4. **Validate threshold compliance** before going live
5. **Use deterministic seeds** for reproducible tests
6. **Archive simulation reports** for comparison

## Troubleshooting

**Issue**: No trades executed
- Check `min_confidence` threshold (lower to allow more trades)
- Verify LogicGate isn't too restrictive
- Review `execute_trades` flag in config

**Issue**: High loss rate
- Check slippage and fee models
- Review ensemble decision logic
- Adjust position sizing parameters

**Issue**: Simulation too slow
- Reduce `delay_sec` (but keep realistic)
- Decrease `iterations` for quick tests
- Use mock adapters (no network calls)

## Next Steps

After successful simulation:
1. Review `data/simulation_report.json`
2. Validate performance metrics
3. Run extended simulations in CI
4. If thresholds pass, proceed to live-test mode
5. See `docs/DEPLOYMENT_GUIDE.md` for deployment
