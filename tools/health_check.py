#!/usr/bin/env python3
"""Health check script for bot monitoring.

Exits 0 if bot is healthy (metrics file exists), non-zero otherwise.
Used by Docker health check and monitoring systems.
"""

import sys
import json
from pathlib import Path


def main():
    """Perform health check."""
    # Check if metrics file exists
    metrics_path = Path("data/performance_stats.json")
    
    if not metrics_path.exists():
        print("UNHEALTHY: Metrics file not found")
        sys.exit(1)
    
    # Try to load metrics
    try:
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
        
        # Check for circuit breaker (if available)
        if isinstance(metrics, dict):
            if metrics.get("circuit_breaker_triggered", False):
                print("UNHEALTHY: Circuit breaker triggered")
                sys.exit(1)
        
        print("HEALTHY: Metrics file exists and is valid")
        sys.exit(0)
    
    except Exception as e:
        print(f"UNHEALTHY: Failed to read metrics: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
