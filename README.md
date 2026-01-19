# Solana Hyper-Accumulation Bot v3.0

A production-grade, modular trading bot for Solana featuring multi-engine decision making, high-fidelity simulation, and comprehensive risk management.

## 🚀 Features

- **Multi-Engine Decision System**: Combines gradient-flow allocation (Kelly-like) and Q-learning MDP
- **Axiomatic Risk Filters**: LogicGate implements MEV protection, latency checks, and market condition filters
- **High-Fidelity Simulation**: Uses same decision logic as live trading with realistic fee/slippage models
- **Modular Architecture**: All integrations abstracted behind Protocol interfaces
- **CI/CD Ready**: GitHub Actions workflows for testing, simulation, and deployment
- **Safety First**: Circuit breakers, position limits, confidence thresholds

## 📋 Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional, for containerized deployment)

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/5mil/solana-hyper-bot3.git
cd solana-hyper-bot3
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run a simulation**
```bash
python tools/run_simulation.py --iterations 100 --execute-trades
```

Or run the bot directly:
```bash
python src/live_bot.py --mode simulation --cycles 50 --delay 2.0
```

### Docker

Build and run:
```bash
docker build -t solana-hyper-bot3:latest .
docker run --rm -v $(pwd)/data:/app/data solana-hyper-bot3:latest --mode simulation --cycles 20
```

## 🏗️ Architecture

### Decision Pipeline

```
MarketData → LogicGate → HyperEnsemble → LeverageEngine → Execution
              (filter)     (consensus)     (sizing)        (Jito/TWAP)
```

### Core Components

- **LogicGate**: Axiomatic filter (MEV, latency, volume, price jump checks)
- **OnflowEngine**: Kelly-criterion gradient allocation with EWMA estimates
- **MDPDecision**: Q-learning with discretized state space
- **HyperEnsemble**: Aggregates engine votes with confidence weighting
- **LeverageEngine**: Position sizing with max 5x leverage, 35% position cap
- **JitoWarpExecutor**: MEV-protected bundle execution (simulation)
- **TWAPExecutor**: Time-weighted order slicing for large trades
- **PaperTrader**: High-fidelity simulation with realistic costs

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## 🧪 Testing

Run all tests:
```bash
pytest
```

Run specific test suites:
```bash
pytest tests/test_logic_gate.py -v
pytest tests/test_onflow_engine.py -v
pytest tests/test_mdp_decision.py -v
pytest tests/test_integration_end_to_end.py -v
```

## 📊 Simulation

The bot includes comprehensive simulation capabilities that use the **same decision logic** as live trading.

### Run Simulation

```bash
# Quick simulation (100 iterations)
python tools/run_simulation.py --iterations 100 --execute-trades --min-confidence 0.75

# Extended simulation
python tools/run_simulation.py --iterations 1000 --delay 0.5 --execute-trades
```

### Simulation Output

Results written to `data/performance_stats.json`:
- Trading summary (win rate, return %, P&L)
- Decision breakdown (approved/blocked counts)
- Iteration-by-iteration reports

See [docs/SIMULATION_GUIDE.md](docs/SIMULATION_GUIDE.md) for comprehensive simulation documentation.

## ⚙️ Configuration

### Bot Configuration (`config/bot_config.json`)

```json
{
  "min_confidence": 0.75,
  "max_position_pct": 0.35,
  "max_daily_loss_pct": 5.0,
  "consecutive_losses_limit": 5,
  "slippage_cap_pct": 1.0,
  "circuit_breaker_drawdown": 0.25,
  "initial_balance": 100
}
```

### Simulation Configuration (`config/simulation_config.json`)

```json
{
  "execute_trades": false,
  "iterations": 100,
  "delay_sec": 1.0,
  "metrics_path": "data/simulation_stats.json"
}
```

## 🚢 Deployment

### GitHub Actions Workflows

1. **deploy-bot.yml**: Build, test, and deploy
   - Runs on push to main
   - Manual dispatch with mode selection (simulation/live-test/production)
   - Pushes Docker image to GHCR

2. **test-simulation.yml**: High-fidelity simulation gate
   - Scheduled daily
   - Enforces thresholds (90% win rate, 45% monthly return, 10% max drawdown)
   - Must pass before production promotion

3. **emergency-stop.yml**: Emergency shutdown
   - Manual trigger only
   - Stops container and optionally sweeps funds

See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for detailed deployment documentation.

## 🔒 Security

- **No Secrets in Code**: All secrets via environment variables
- **Mock Adapters**: Test without real API keys or wallet
- **Simulation First**: Validate strategies before risking capital
- **Circuit Breakers**: Automatic shutdown on drawdown/loss limits
- **Emergency Procedures**: Quick-stop workflows with fund recovery

### Required Secrets (Live Mode Only)

- `WALLET_KEYPAIR`: Base58 encoded Solana keypair
- `EMERGENCY_SWEEP_ADDRESS`: Emergency fund recovery address
- `GITHUB_CONTAINER_REGISTRY_PAT`: For Docker image pushes

See `config/secrets.template.json` for full list.

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md): System design and components
- [Simulation Guide](docs/SIMULATION_GUIDE.md): How to run and analyze simulations
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md): Docker, CI/CD, and production deployment

## 🛠️ Development

### Project Structure

```
solana-hyper-bot3/
├── src/
│   ├── core/              # Decision engines and logic
│   ├── execution/         # Execution layer (leverage, Jito, TWAP)
│   ├── simulation/        # Simulation and backtesting
│   ├── adapters/          # Mock implementations for testing
│   └── live_bot.py        # Main bot entry point
├── tests/                 # Unit and integration tests
├── config/                # Configuration files
├── docs/                  # Documentation
├── tools/                 # Utility scripts
├── .github/workflows/     # CI/CD workflows
└── data/                  # Output directory for metrics
```

### Adding New Engines

1. Implement engine following the callable pattern: `(MarketState) -> (ActionType, confidence)`
2. Add to HyperEnsemble in `src/live_bot.py`
3. Write unit tests
4. Run simulation to validate

### Adding New Executors

1. Implement `ExecutionProvider` protocol from `src/execution/interfaces.py`
2. Add realistic latency and fee models
3. Integrate with LiveBot or MarketSimulator
4. Test in simulation mode first

## 📈 Performance Thresholds

Production promotion requires:
- ✅ Win Rate ≥ 90%
- ✅ Avg Monthly Return ≥ 45%
- ✅ Max Drawdown ≤ 10%

Enforced by `test-simulation.yml` workflow.

## ⚠️ Disclaimer

This software is for educational and research purposes. Trading cryptocurrencies involves substantial risk of loss. The authors are not responsible for any financial losses incurred through use of this software. Always test thoroughly in simulation before risking real capital.

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📞 Support

- Issues: [GitHub Issues](https://github.com/5mil/solana-hyper-bot3/issues)
- Documentation: See `docs/` directory

---

Built with ❤️ for the Solana ecosystem