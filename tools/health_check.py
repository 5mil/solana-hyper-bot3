#!/usr/bin/env python3
"""
Health check script for monitoring bot status.

Exits 0 if performance stats file exists and is valid.
Exits non-zero otherwise.
"""
import sys
import json
from pathlib import Path


def main():
    """Run health check."""
    metrics_path = Path("data/performance_stats.json")
    
    if not metrics_path.exists():
        print("❌ Health check failed: metrics file not found")
        sys.exit(1)
    
    try:
        with open(metrics_path) as f:
            data = json.load(f)
        
        # Basic validation
        if "mode" not in data:
            print("❌ Health check failed: invalid metrics format")
            sys.exit(1)
        
        print("✅ Health check passed")
        print(f"   Mode: {data.get('mode', 'unknown')}")
        print(f"   Cycles: {data.get('cycle_count', 0)}")
        print(f"   Trades: {data.get('total_trades', 0)}")
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        print("❌ Health check failed: invalid JSON in metrics file")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
