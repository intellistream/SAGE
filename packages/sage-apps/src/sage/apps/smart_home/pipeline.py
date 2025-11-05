"""
Smart Home Pipeline

Main pipeline implementation using SAGE operators for smart home automation.
"""

from __future__ import annotations

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment

from .operators import (
    DeviceExecutor,
    EnvironmentMonitor,
    EventLogSink,
    LaundryWorkflowSource,
    WorkflowProgressSink,
)


def run_smart_home_demo(num_cycles: int = 1, verbose: bool = False) -> None:
    """
    Run the smart home laundry automation demonstration.

    Args:
        num_cycles: Number of laundry cycles to run
        verbose: Enable verbose logging

    Example:
        >>> from sage.apps.smart_home import run_smart_home_demo
        >>> run_smart_home_demo(num_cycles=1)
    """
    print("\n" + "🏠" * 35)
    print(" " * 15 + "SAGE Smart Home Automation Demo")
    print("🏠" * 35)
    print()
    print("=" * 70)
    print("📋 Configuration")
    print("=" * 70)
    print(f"   Laundry cycles: {num_cycles}")
    print(f"   Verbose logging: {verbose}")
    print("=" * 70)
    print()

    print("=" * 70)
    print("🔄 Automated Laundry Workflow")
    print("=" * 70)
    print("   Steps:")
    print("   1. Check environmental conditions (humidity)")
    print("   2. Robot collects laundry from basket")
    print("   3. Washer runs wash cycle")
    print("   4. Robot moves laundry to dryer")
    print("   5. Dryer runs dry cycle")
    print("   6. Robot moves laundry to drying rack")
    print("=" * 70)
    print()

    # Create SAGE environment
    env = LocalEnvironment("smart_home")

    # Build pipeline:
    # 1. LaundryWorkflowSource: Generate workflow tasks
    # 2. DeviceExecutor: Execute tasks on simulated devices
    # 3. EnvironmentMonitor: Monitor environmental conditions
    # 4. WorkflowProgressSink: Track progress
    # 5. EventLogSink: Log all events
    pipeline = (
        env.from_batch(
            LaundryWorkflowSource,
            num_cycles=num_cycles,
        )
        .map(DeviceExecutor)
        .map(EnvironmentMonitor)
        .sink(WorkflowProgressSink)
    )

    if verbose:
        pipeline.sink(EventLogSink)

    # Execute pipeline
    print("🚀 Starting smart home automation...")
    print()
    env.submit(autostop=True)

    print("\n🏠" * 35)
    print(" " * 20 + "Demo completed!")
    print("🏠" * 35 + "\n")


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SAGE Smart Home System - IoT device automation demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single laundry cycle
  python -m sage.apps.smart_home.pipeline

  # Run multiple cycles
  python -m sage.apps.smart_home.pipeline --cycles 3

  # Verbose mode
  python -m sage.apps.smart_home.pipeline --verbose
        """,
    )

    parser.add_argument(
        "--cycles",
        "-c",
        type=int,
        default=1,
        help="Number of laundry cycles to run (default: 1)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Disable global console debug unless verbose
    if not args.verbose:
        CustomLogger.disable_global_console_debug()

    # Run demo
    run_smart_home_demo(num_cycles=args.cycles, verbose=args.verbose)


if __name__ == "__main__":
    main()
