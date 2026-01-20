#!/usr/bin/env python3
"""
Enhanced Run simulation CLI tool with production-ready features.

Runs MarketSimulator with MockQuoteClient for local testing.
Includes:
- Input validation and error handling
- Structured logging
- Progress tracking
- Metrics persistence
- Configuration validation
- Multiple subcommands (simulate, analyze, backtest)
"""
import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import csv
from typing import Optional, TypedDict

# Third-party imports (ensure these are in requirements.txt)
try:
    import tqdm
except ImportError:
    print("Warning: tqdm not found. Install with: pip install tqdm")
    tqdm = None

from src.simulation.market_simulator import MarketSimulator
from src.adapters.mock_quote_client import MockMarketDataFetcher, MockQuoteClient
from src.core.logic_gate import LogicGate
from src.core.hyper_ensemble import HyperEnsemble
from src.core.onflow_engine import OnflowEngine
from src.core.mdp_decision import MDPDecision
from src.execution.leverage_engine import LeverageEngine, LeverageConfig
from src.execution.twap_executor import TWAPExecutor
from src.simulation.paper_trader import PaperTrader


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure structured logging."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('simulation.log')
        ]
    )
    
    return logging.getLogger(__name__)


# ============================================================================
# TYPE DEFINITIONS
# 
