#!/usr/bin/env python3
"""
Wrapper script for Tool Selection data preparation.

This script is a convenience wrapper that calls the data preparation logic
in the agent_benchmark source directory.

The actual implementation is in:
    sage/data/sources/agent_benchmark/prepare_runtime_data.py

Usage:
    python prepare_tool_selection_data.py --validate
    python prepare_tool_selection_data.py --generate --samples 500
    python prepare_tool_selection_data.py --create-splits --num-candidates 100,500,1000
"""

import sys
from pathlib import Path

# Setup paths to find the source module
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_ROOT = SCRIPT_DIR.parent.parent.parent.parent.parent.parent  # sage-benchmark
sys.path.insert(0, str(BENCHMARK_ROOT / "src"))

# Import and run the main function from the source location
from sage.data.sources.agent_benchmark.prepare_runtime_data import main

if __name__ == "__main__":
    main()
