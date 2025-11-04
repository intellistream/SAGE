#!/usr/bin/env python3
"""
Auto-Scaling Chat System Example

This script demonstrates the Auto-Scaling Chat application from sage-apps.
It simulates elastic scaling of chat servers based on user load.

Requirements:
    pip install -e packages/sage-apps

Usage:
    python examples/apps/run_auto_scaling_chat.py
    python examples/apps/run_auto_scaling_chat.py --duration 60 --peak-rate 80
    python examples/apps/run_auto_scaling_chat.py --verbose

Test Configuration:
    @test_category: apps
    @test_speed: medium
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from sage.apps.auto_scaling_chat import run_auto_scaling_demo
    from sage.common.utils.logging.custom_logger import CustomLogger
except ImportError as e:
    print(f"Error importing sage.apps.auto_scaling_chat: {e}")
    print("\nPlease install sage-apps:")
    print("  pip install -e packages/sage-apps")
    sys.exit(1)


def main():
    """Run the auto-scaling chat system demo."""
    parser = argparse.ArgumentParser(
        description="SAGE Auto-Scaling Chat System - Elastic resource management demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run default simulation (30s)
  python %(prog)s

  # Short simulation with high peak
  python %(prog)s --duration 20 --peak-rate 80

  # Long simulation with moderate load
  python %(prog)s --duration 60 --peak-rate 40

  # Verbose mode with scaling events
  python %(prog)s --verbose

Features:
  - Simulated variable user load
  - Automatic server scaling (up/down)
  - Load balancing across servers
  - Real-time metrics collection
        """,
    )

    parser.add_argument(
        "--duration",
        "-d",
        type=int,
        default=30,
        help="Simulation duration in seconds (default: 30)",
    )

    parser.add_argument(
        "--base-rate",
        "-b",
        type=int,
        default=5,
        help="Base user load (default: 5)",
    )

    parser.add_argument(
        "--peak-rate",
        "-p",
        type=int,
        default=50,
        help="Peak user load (default: 50)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Disable global console debug unless verbose
    if not args.verbose:
        CustomLogger.disable_global_console_debug()

    print("=" * 70)
    print("SAGE Auto-Scaling Chat System - Example")
    print("=" * 70)
    print()

    # Run demo
    try:
        run_auto_scaling_demo(
            duration=args.duration,
            base_rate=args.base_rate,
            peak_rate=args.peak_rate,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"\nError running auto-scaling demo: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
