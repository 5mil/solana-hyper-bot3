# GUI Dashboard Usage

## Overview

The Solana Hyper-Bot includes an interactive GUI dashboard for real-time monitoring of trading simulations and live trading.

## Features

- **Real-time Status Display**: Shows bot status, current cycle, last update time, SOL price, and market regime
- **Performance Metrics**: Tracks balance, P&L, return %, trades, win rate, drawdown, and approval rate
- **Trade Log**: Scrolling log of all trades with timestamp, action, price, and P&L
- **Toggleable Themes**: Switch between dark and light modes
- **Flexible Views**: Toggle between compact and detailed views
- **Resizable Window**: Compact mode for minimal screen space, expanded for full details

## Requirements

The GUI requires `tkinter`, which is included with most Python installations but may need to be installed separately on some systems:

### Ubuntu/Debian
```bash
sudo apt-get install python3-tk
```

### macOS
tkinter is included with Python installations from python.org

### Windows
tkinter is included with standard Python installations

## Usage

### Basic Simulation with GUI

```bash
python tools/run_simulation.py --gui --iterations 100 --execute-trades
```

### Real-Time Mode with GUI

```bash
python tools/run_simulation.py --gui --real-time --iterations 50 --execute-trades
```

### Command-Line Options

- `--gui`: Enable the GUI dashboard
- `--real-time`: Use real-time market data from Jupiter/Birdeye APIs
- `--iterations N`: Number of simulation cycles (default: 100)
- `--delay D`: Delay between cycles in seconds (default: 1.0)
- `--execute-trades`: Execute paper trades (vs. just decisions)
- `--min-confidence C`: Minimum confidence threshold (default: 0.75)
- `--verbose`: Enable verbose logging

## GUI Controls

### Theme Toggle (🌙/☀️ button)
Switch between dark and light color themes for comfortable viewing

### View Toggle (📊 button)
Toggle between compact and detailed views:
- **Detailed**: Shows all metrics including current price and market regime
- **Compact**: Hides less critical information for cleaner display

### Window Resize (⬇️/⬆️ button)
Toggle window size:
- **Expanded** (900x700): Full view with complete trade log
- **Compact** (900x350): Minimal view for background monitoring

## Metrics Explained

### Balance Metrics
- **Current Balance**: Current account balance in USD
- **Total P&L**: Total profit/loss across all trades
- **Return %**: Percentage return on initial balance

### Trade Metrics
- **Total Trades**: Number of trades executed
- **Win Rate**: Percentage of profitable trades
- **Blocked**: Number of decisions blocked by filters

### Risk Metrics
- **Peak Balance**: Highest balance reached
- **Drawdown**: Current drawdown from peak
- **Approval Rate**: Percentage of cycles that resulted in trades

## Real-Time vs. Mock Mode

### Mock Mode (Default)
```bash
python tools/run_simulation.py --gui --execute-trades
```
- Uses synthetic random walk data
- No external API calls
- Fast and predictable for testing

### Real-Time Mode
```bash
python tools/run_simulation.py --gui --real-time --execute-trades
```
- Fetches live SOL price from Jupiter API
- Uses Birdeye for volume/liquidity metrics
- Real market conditions and volatility
- Requires internet connection

### Environment Variables (Optional)

For real-time mode, you can customize API endpoints:

```bash
export JUPITER_ENDPOINT="https://quote-api.jup.ag/v6"
export BIRDEYE_API_KEY="your_api_key_here"  # Optional, for higher rate limits

python tools/run_simulation.py --gui --real-time --execute-trades
```

## Troubleshooting

### GUI Not Launching

If you see "GUI not available (tkinter not installed)":
1. Install tkinter for your system (see Requirements above)
2. Verify installation: `python3 -c "import tkinter"`
3. If still not working, run without `--gui` flag

### Display Issues

- **Text too small**: Use light theme (☀️ button) for better contrast
- **Window too large**: Use compact mode (⬇️ button)
- **Log overwhelming**: Switch to compact view (📊 button)

### Performance

For long-running simulations (1000+ iterations):
- The trade log automatically limits to last 1000 lines
- GUI updates every 100ms for smooth real-time display
- Use compact mode to reduce rendering overhead

## Example Sessions

### Quick Test (Mock Data)
```bash
# 20 cycles, fast execution, with GUI
python tools/run_simulation.py --gui --iterations 20 --delay 0.5 --execute-trades
```

### Extended Simulation (Real Data)
```bash
# 500 cycles, real data, 2-second delay
python tools/run_simulation.py --gui --real-time --iterations 500 --delay 2.0 --execute-trades --min-confidence 0.7
```

### Background Monitoring
```bash
# Compact window, detailed metrics hidden, running indefinitely
python tools/run_simulation.py --gui --real-time --iterations 10000 --delay 5.0 --execute-trades
# Then click compact mode and compact view buttons
```

## Screenshots

The GUI displays:
- Header with bot title and control buttons
- Status panel showing bot state, cycle count, and time
- Metrics panel with 3 columns of performance data
- Trade log with scrolling history
- Footer with status messages

Note: Screenshots not included as this is a terminal-based documentation file. Run the GUI to see it in action!
