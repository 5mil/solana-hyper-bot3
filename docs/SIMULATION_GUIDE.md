# Simulation Guide

## Overview

The Hyper-Accumulation Bot v3.0 supports high-fidelity simulation that uses the **exact same decision logic** as live trading, but executes via PaperTrader instead of real transactions.

## Simulation Modes

### 1. Decision-Only Simulation
Set `execute_trades: false` to test decision-making without position tracking:
```json
{
  "execute_trades": false,
  "iterations": 100
}
```
- Runs LogicGate + HyperEnsemble
- Logs decisions but doesn't execute
- Useful for testing filters and confidence thresholds

### 2. Full Paper Trading
Set `execute_trades: true` for complete trading simulation:
```json
{
  "execute_trades": true,
  "iterations": 100,
  "initial_balance": 100.0
}
```
- Executes via PaperTrader
- Tracks positions, P&L, fees
- Generates performance reports

## Running Simulations

### Local Simulation

```bash
python tools/run_simulation.py --iterations 100 --delay 1.0
```

Or using the LiveBot directly:
```bash
python src/live_bot.py --mode simulation --cycles 50 --delay 2.0
```

### Via MarketSimulator

```python
from src.simulation.market_simulator import MarketSimulator
from src.adapters.mock_quote_client import MockMarketDataFetcher

fetcher = MockMarketDataFetcher(base_price=100.0)
simulator = MarketSimulator(
    market_data_fetcher=fetcher,
    min_confidence=0.75,
    execute_trades=True
)

report = await simulator.run_simulation(
    iterations=100,
    delay_sec=1.0
)
```

## Simulation Outputs

### Performance Stats JSON

Written to `data/performance_stats.json` (configurable):

```json
{
  "simulation_config": {
    "iterations": 100,
    "min_confidence": 0.75,
    "execute_trades": true
  },
  "decisions": {
    "total": 100,
    "approved": 45,
    "blocked": 55,
    "approval_rate": 45.0
  },
  "trading_summary": {
    "total_trades": 40,
    "winning_trades": 25,
    "losing_trades": 15,
    "win_rate": 62.5,
    "total_pnl": 12.5,
    "return_pct": 12.5,
    "avg_win": 2.1,
    "avg_loss": -1.3,
    "total_fees": 2.0,
    "current_balance": 112.5
  }
}
```

### Key Metrics

- **Approval Rate**: % of decisions passing LogicGate + confidence threshold
- **Win Rate**: % of closed trades that were profitable
- **Return %**: (final_balance - initial_balance) / initial_balance * 100
- **Avg Win/Loss**: Average P&L for winning/losing trades

## Realistic Models

### Fee Model
- Default: 0.05% per trade
- Applied on entry and exit
- Includes network fees in live mode

### Slippage Model
- Base slippage: 0.02%
- Scales with position size
- Inversely proportional to liquidity score
- Random variance: ±20%

### Latency Model
- Base: 100-150ms for simulation
- Higher for Jito bundles (150ms ± 50ms)
- Affects price by market volatility during execution

## Configuration

### simulation_config.json

```json
{
  "execute_trades": false,
  "iterations": 100,
  "delay_sec": 1.0,
  "metrics_path": "data/simulation_stats.json",
  "market_simulation": {
    "base_price": 100.0,
    "price_volatility": 0.02,
    "volume_range": [5000, 15000]
  }
}
```

### Adjusting Thresholds

Edit `config/bot_config.json` to tune behavior:
- `min_confidence`: 0.75 (higher = more selective)
- `max_position_pct`: 0.35 (max % of balance per trade)
- `max_mev_risk`: 0.7 (MEV risk tolerance)
- `max_latency_ms`: 500 (network latency tolerance)

## Backtesting

For historical data replay:

```python
from src.simulation.backtest import Backtest

backtest = Backtest(min_confidence=0.75)

historical_bars = [
    {"timestamp": "2024-01-01T00:00:00", "close": 100.0, "volume": 10000, ...},
    # ... more bars
]

report = await backtest.run_backtest(historical_bars)
```

## CI Integration

GitHub Actions runs simulation tests automatically:
- Unit tests verify individual components
- Integration test runs 5-10 iteration simulation
- Full simulation runs on workflow_dispatch with configurable duration
- Results uploaded as artifacts

## Best Practices

1. **Start with Decision-Only**: Test filters without P&L noise
2. **Short Iterations First**: Run 10-20 iterations to validate setup
3. **Increase Gradually**: Scale to 100+ iterations for statistics
4. **Compare Configurations**: A/B test different min_confidence values
5. **Check Approval Rate**: Too low (<20%) = filters too strict; too high (>80%) = not selective enough

## Troubleshooting

### No Trades Executed
- Check `approval_rate` in output
- Lower `min_confidence` threshold
- Verify `execute_trades: true`
- Check LogicGate thresholds aren't too strict

### Low Win Rate
- Ensemble engines may need tuning
- Check market volatility settings
- Review decision logic in engines

### High Fees/Slippage
- Reduce `fee_pct` and `base_slippage_pct` in PaperTrader
- Use smaller position sizes
- Increase liquidity_score in mock data
