#!/usr/bin/env python3
"""
Wrapper script for Task Planning data preparation.

This script is a convenience wrapper that calls the data preparation logic
in the agent_benchmark source directory.

The actual implementation is in:
    sage/data/sources/agent_benchmark/prepare_planning_data.py

Usage:
    python prepare_planning_data.py
    python prepare_planning_data.py --output /path/to/data --num_samples 300
"""

import sys
from pathlib import Path

# Setup paths to find the source module
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_ROOT = SCRIPT_DIR.parent.parent.parent.parent.parent.parent  # sage-benchmark
sys.path.insert(0, str(BENCHMARK_ROOT / "src"))

# Import and run the main function from the source location
from sage.data.sources.agent_benchmark.prepare_planning_data import main

if __name__ == "__main__":
    main()
