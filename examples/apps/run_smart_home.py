#!/usr/bin/env python3
"""
Smart Home System Example

This script demonstrates the Smart Home application from sage-apps.
It simulates IoT device coordination for automated laundry workflow.

Requirements:
    pip install -e packages/sage-apps

Usage:
    python examples/apps/run_smart_home.py
    python examples/apps/run_smart_home.py --cycles 3
    python examples/apps/run_smart_home.py --verbose

Test Configuration:
    @test_category: apps
    @test_speed: fast
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from sage.apps.smart_home import run_smart_home_demo
    from sage.common.utils.logging.custom_logger import CustomLogger
except ImportError as e:
    print(f"Error importing sage.apps.smart_home: {e}")
    print("\nPlease install sage-apps:")
    print("  pip install -e packages/sage-apps")
    sys.exit(1)


def main():
    """Run the smart home automation demo."""
    parser = argparse.ArgumentParser(
        description="SAGE Smart Home System - IoT device automation demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single laundry cycle
  python %(prog)s

  # Run multiple cycles
  python %(prog)s --cycles 3

  # Verbose mode with event logging
  python %(prog)s --cycles 2 --verbose

Features:
  - IoT device simulation (robot, washer, dryer, sensors)
  - Automated workflow coordination
  - Environmental monitoring
  - Event-driven architecture
        """,
    )

    parser.add_argument(
        "--cycles",
        "-c",
        type=int,
        default=1,
        help="Number of laundry cycles to run (default: 1)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Disable global console debug unless verbose
    if not args.verbose:
        CustomLogger.disable_global_console_debug()

    print("=" * 70)
    print("SAGE Smart Home System - Example")
    print("=" * 70)
    print()

    # Run demo
    try:
        run_smart_home_demo(num_cycles=args.cycles, verbose=args.verbose)
    except Exception as e:
        print(f"\nError running smart home demo: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
