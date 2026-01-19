# Solana Hyper-Accumulation Bot v3.0

A production-grade algorithmic trading system for Solana markets implementing sophisticated multi-layer decision-making with risk management, position sizing, and high-performance execution.

## 🚀 Features

- **Multi-Layer Decision Pipeline**: LogicGate → Gradient Flow → MDP → Ensemble
- **Advanced Risk Management**: MEV filtering, circuit breakers, position limits
- **Kelly-Like Position Sizing**: Dynamic allocation based on EWMA performance
- **MEV-Protected Execution**: Jito bundle simulation with realistic latency modeling
- **High-Fidelity Simulation**: Test full pipeline without risking capital
- **Protocol-Based Architecture**: All external integrations behind interfaces for easy mocking
- **Comprehensive Testing**: Unit, integration, and simulation tests
- **CI/CD Workflows**: Automated testing, simulation validation, and deployment
- **Docker Packaging**: Production-ready containerization

## 📁 Project Structure

```
solana-hyper-bot3/
├── src/
│   ├── core/              # Core decision components
│   │   ├── types.py       # Pydantic models and enums
│   │   ├── logic_gate.py  # Deterministic filter
│   │   ├── onflow_engine.py  # Kelly allocation
│   │   ├── mdp_decision.py   # Q-learning MDP
│   │   └── hyper_ensemble.py # Ensemble coordinator
│   ├── execution/         # Execution layer
│   │   ├── interfaces.py     # Protocol definitions
│   │   ├── leverage_engine.py # Position sizing
│   │   ├── jito_warp.py      # Jito simulation
│   │   └── twap_executor.py  # TWAP execution
│   ├── simulation/        # Simulation layer
│   │   ├── paper_trader.py      # Paper trading
│   │   ├── market_simulator.py  # Market simulation
│   │   └── backtest.py          # Historical replay
│   ├── adapters/          # External service adapters
│   │   └── mock_quote_client.py # Mock Jupiter
│   └── live_bot.py        # Main trading loop
├── config/                # Configuration files
│   ├── bot_config.json           # Bot parameters
│   ├── live_runtime.json         # Runtime settings
│   ├── simulation_config.json    # Simulation config
│   └── secrets.template.json     # Secret placeholders
├── tests/                 # Test suite
│   ├── test_logic_gate.py
│   ├── test_onflow_engine.py
│   ├── test_mdp_decision.py
│   └── test_integration_end_to_end.py
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md       # System architecture
│   ├── SIMULATION_GUIDE.md   # Simulation guide
│   └── DEPLOYMENT_GUIDE.md   # Deployment guide
├── tools/                 # Utility scripts
│   ├── health_check.py       # Health check
│   └── run_simulation.py     # Local simulation
├── .github/workflows/     # CI/CD workflows
│   ├── deploy-bot.yml        # Main deployment
│   ├── test-simulation.yml   # Simulation tests
│   └── emergency-stop.yml    # Emergency stop
├── Dockerfile             # Docker image definition
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🏃 Quick Start

### Local Simulation

Run a simulation locally without any secrets or external connections:

```bash
# Install dependencies
pip install -r requirements.txt

# Run simulation
python tools/run_simulation.py --iterations 100 --execute-trades

# Check results
cat data/simulation_report.json
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_logic_gate.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Docker Build and Run

```bash
# Build image
docker build -t hyper-bot3:latest .

# Run simulation in Docker
docker run --rm \
  -v $(pwd)/data:/app/data \
  hyper-bot3:latest \
  python tools/run_simulation.py
```

## 📊 Architecture

The bot processes each trading cycle through a sophisticated pipeline:

1. **Market Data Fetching**: Pull current state from Solana RPC, Jupiter, etc.
2. **Logic Gate**: Apply hard constraints (MEV risk, latency, volume, price jumps)
3. **Hyper Ensemble**: Aggregate multiple ML engine votes with confidence weighting
4. **Position Sizing**: Compute optimal size using Kelly-like allocation (capped at 35%)
5. **Execution**: Execute via Jito bundles or TWAP with slippage protection

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## 🔬 Simulation

The simulation layer uses the **exact same decision components** as live trading but executes through a paper trader instead of blockchain transactions:

- **Same Logic**: Identical decision pipeline
- **Realistic Modeling**: Fee, slippage, and latency models
- **Risk-Free Testing**: No capital at risk, no secrets needed
- **Performance Validation**: Enforces thresholds before production

See [docs/SIMULATION_GUIDE.md](docs/SIMULATION_GUIDE.md) for complete simulation guide.

## 🚀 Deployment

### CI/CD Workflows

**Deploy Bot** (`.github/workflows/deploy-bot.yml`):
- Runs tests and builds Docker image
- Supports simulation, live-test, and production modes
- Posts results to PR comments

**Test Simulation** (`.github/workflows/test-simulation.yml`):
- Nightly extended simulations
- Enforces performance thresholds:
  - Win rate ≥ 90%
  - Avg monthly return ≥ 45%
  - Max drawdown ≤ 10%

**Emergency Stop** (`.github/workflows/emergency-stop.yml`):
- Manual trigger to stop live container
- Optional fund sweep to emergency address
- Creates incident tracking issue

See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for deployment instructions.

## ⚙️ Configuration

### Bot Configuration (`config/bot_config.json`)

```json
{
  "min_confidence": 0.75,
  "max_position_pct": 0.35,
  "max_daily_loss_pct": 0.15,
  "consecutive_losses_limit": 5,
  "circuit_breaker_drawdown": 0.25,
  "initial_balance": 100.0
}
```

### Simulation Configuration (`config/simulation_config.json`)

```json
{
  "execute_trades": false,
  "iterations": 100,
  "delay_sec": 0.1,
  "output_report": "data/simulation_report.json"
}
```

## 🧪 Testing

The test suite includes:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end pipeline testing
- **Simulation Tests**: Extended trading simulations
- **Deterministic Mocks**: No external dependencies

All tests use mock adapters and can run without secrets.

## 🔐 Security

- **No secrets in code**: All secrets via environment variables
- **Protocol interfaces**: Easy mocking without live connections
- **Simulation mode**: Never signs or broadcasts transactions
- **Circuit breakers**: Automatic stop on excessive losses
- **MEV protection**: Risk scoring and Jito bundle support

## 📈 Performance Thresholds

Production deployment requires:

- ✅ Win Rate ≥ 90%
- ✅ Avg Monthly Return ≥ 45%
- ✅ Max Drawdown ≤ 10%
- ✅ All tests passing

## 🛠️ Development

### Adding New Decision Engines

```python
from src.core.hyper_ensemble import HyperEnsemble

# Create your engine
def my_engine(market_state: MarketState) -> Action:
    # Your logic here
    return Action(...)

# Add to ensemble
ensemble = HyperEnsemble()
ensemble.add_engine("my_engine", my_engine)
```

### Adding New Execution Venues

```python
from src.execution.interfaces import ExecutionProvider

class MyExecutor:
    def execute(self, action: Action, market_state: MarketState) -> ExecutionReport:
        # Your execution logic
        return ExecutionReport(...)

# Use in LiveBot
bot = LiveBot(mode=BotMode.LIVE, executor=MyExecutor())
```

## 📝 License

See repository license file.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## ⚠️ Disclaimer

This is a trading bot scaffold for educational and development purposes. The scaffold includes:

- ✅ Complete decision pipeline implementation
- ✅ Simulation and testing infrastructure
- ✅ CI/CD workflows
- ✅ Mock adapters for safe testing
- ❌ Production Solana/Jupiter/Drift/Jito adapters (must be added separately)
- ❌ Secret material (must be provided separately)

**Use at your own risk. Trading involves substantial risk of loss.**

## 📞 Support

- Documentation: [docs/](docs/)
- Issues: GitHub Issues
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

Built with ❤️ for the Solana ecosystem