"""
Auto-Scaling Chat System Pipeline

Main pipeline implementation using SAGE operators for auto-scaling demonstration.
"""

from __future__ import annotations

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment

from .operators import (
    AutoScaler,
    LoadBalancer,
    MetricsCollector,
    RequestProcessor,
    ScalingEventsSink,
    UserTrafficSource,
)


def run_auto_scaling_demo(
    duration: int = 30,
    base_rate: int = 5,
    peak_rate: int = 50,
    verbose: bool = False,
) -> None:
    """
    Run the auto-scaling chat system demonstration.

    Args:
        duration: Simulation duration in seconds
        base_rate: Base user load (concurrent users)
        peak_rate: Peak user load (concurrent users)
        verbose: Enable verbose logging

    Example:
        >>> from sage.apps.auto_scaling_chat import run_auto_scaling_demo
        >>> run_auto_scaling_demo(duration=30, peak_rate=50)
    """
    print("\n" + "⚡" * 35)
    print(" " * 10 + "SAGE Auto-Scaling Chat System Demo")
    print("⚡" * 35)
    print()
    print("=" * 70)
    print("📋 Configuration")
    print("=" * 70)
    print(f"   Simulation duration: {duration}s")
    print(f"   Base load: {base_rate} concurrent users")
    print(f"   Peak load: {peak_rate} concurrent users")
    print(f"   Verbose logging: {verbose}")
    print("=" * 70)
    print()

    print("=" * 70)
    print("🎯 System Behavior")
    print("=" * 70)
    print("   Phase 1 (0-30%):  Gradual load increase")
    print("   Phase 2 (30-70%): Peak load period")
    print("   Phase 3 (70-100%): Load decrease")
    print()
    print("   Scaling Policy:")
    print("   - Scale UP when avg load/server > 30 users")
    print("   - Scale DOWN when avg load/server < 10 users")
    print("   - Min servers: 2, Max servers: 10")
    print("=" * 70)
    print()

    # Create SAGE environment
    env = LocalEnvironment("auto_scaling_chat")

    # Build pipeline:
    # 1. UserTrafficSource: Generate simulated user requests
    # 2. AutoScaler: Make scaling decisions based on load
    # 3. LoadBalancer: Distribute requests across servers
    # 4. RequestProcessor: Process requests on servers
    # 5. MetricsCollector: Collect and display metrics
    # 6. ScalingEventsSink: Log scaling events
    pipeline = (
        env.from_batch(
            UserTrafficSource,
            duration=duration,
            base_rate=base_rate,
            peak_rate=peak_rate,
        )
        .map(AutoScaler, scale_up_threshold=30, scale_down_threshold=10)
        .map(LoadBalancer, initial_servers=2)
        .map(RequestProcessor, processing_time=0.05)
        .sink(MetricsCollector)
    )

    if verbose:
        pipeline.sink(ScalingEventsSink)

    # Execute pipeline
    print("🚀 Starting auto-scaling simulation...")
    print()
    env.submit(autostop=True)

    print("\n⚡" * 35)
    print(" " * 20 + "Demo completed!")
    print("⚡" * 35 + "\n")


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SAGE Auto-Scaling Chat System - Elastic resource management demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run default simulation (30s)
  python -m sage.apps.auto_scaling_chat.pipeline

  # Short simulation with high peak
  python -m sage.apps.auto_scaling_chat.pipeline --duration 20 --peak-rate 80

  # Long simulation with moderate load
  python -m sage.apps.auto_scaling_chat.pipeline --duration 60 --peak-rate 40

  # Verbose mode with scaling events
  python -m sage.apps.auto_scaling_chat.pipeline --verbose
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

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Disable global console debug unless verbose
    if not args.verbose:
        CustomLogger.disable_global_console_debug()

    # Run demo
    run_auto_scaling_demo(
        duration=args.duration,
        base_rate=args.base_rate,
        peak_rate=args.peak_rate,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
