"""Tutorial: SAGE vLLM Control Plane - Intelligent Request Scheduling

Demonstrates ControlPlaneVLLMService API usage with real examples.

This tutorial shows how to use the Control Plane for intelligent request
scheduling across multiple vLLM instances.

In test/CI mode, only configuration examples are shown without requiring
actual vLLM servers.

Usage: python vllm_control_plane_tutorial.py

Test Configuration:
    @test_category: tutorials
    @test_speed: quick
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Check test mode first
_IS_TEST_MODE = (
    os.getenv("SAGE_TEST_MODE") == "true"
    or os.getenv("SAGE_EXAMPLES_MODE") == "test"
    or os.getenv("CI") == "true"
)

try:
    from sage.common.components.sage_llm import ControlPlaneVLLMService
    from sage.common.config.ports import SagePorts

    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    if not _IS_TEST_MODE:
        print("Warning: ControlPlaneVLLMService not available\n")


def demo_basic():
    """Basic single-instance usage."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Usage")
    print("=" * 60)

    # Use SagePorts for port configuration
    llm_port = SagePorts.get_recommended_llm_port() if AVAILABLE else 8901

    config = {
        "scheduling_policy": "fifo",
        "instances": [
            {
                "instance_id": "llm-1",
                "host": "localhost",
                "port": llm_port,
                "model_name": "Qwen/Qwen2.5-7B-Instruct",
            }
        ],
    }

    print("\nConfiguration example:")
    print(f"  Scheduling policy: {config['scheduling_policy']}")
    print(f"  Instance: llm-1 @ localhost:{llm_port}")
    print(f"  Model: {config['instances'][0]['model_name']}")

    # In test mode, only show configuration without actual connection
    if _IS_TEST_MODE:
        print("\n[Test mode] Skipping actual vLLM connection")
        print("  In production, this would connect to vLLM server and generate text.")
        return

    if not AVAILABLE:
        print("Skipping - module not available")
        return

    try:
        service = ControlPlaneVLLMService(config)
        service.setup()
        result = service.generate("What is AI?", max_tokens=50)
        print(f"Generated: {result[:80]}...")
        metrics = service.get_metrics()
        print(f"Metrics: {metrics['total_requests']} requests")
        service.cleanup()
    except Exception as e:
        print(f"Error: {e}")


def demo_multi():
    """Multi-instance load balancing."""
    print("\n" + "=" * 60)
    print("Demo 2: Multi-Instance Load Balancing")
    print("=" * 60)

    # Use SagePorts for port configuration
    base_port = SagePorts.BENCHMARK_LLM if AVAILABLE else 8901

    config = {
        "scheduling_policy": "adaptive",
        "instances": [
            {
                "instance_id": f"llm-{i}",
                "host": "localhost",
                "port": base_port + i,
                "model_name": "Qwen/Qwen2.5-7B-Instruct",
            }
            for i in range(3)
        ],
    }

    print("\nConfiguration example:")
    print(f"  Scheduling policy: {config['scheduling_policy']}")
    print("  Instances: 3 load-balanced instances")
    for inst in config["instances"]:
        print(f"    - {inst['instance_id']} @ localhost:{inst['port']}")

    # In test mode, only show configuration without actual connection
    if _IS_TEST_MODE:
        print("\n[Test mode] Skipping actual vLLM connection")
        print("  In production, Control Plane would:")
        print("    - Register all instances")
        print("    - Load balance requests across instances")
        print("    - Monitor health and performance")
        return

    if not AVAILABLE:
        print("Skipping - module not available")
        return

    try:
        service = ControlPlaneVLLMService(config)
        service.setup()
        instances = service.show_instances()
        print(f"Registered {len(instances)} instances")
        service.cleanup()
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all demos."""
    print("\nSAGE vLLM Control Plane Tutorial")
    print("=" * 60)

    for demo in [demo_basic, demo_multi]:
        try:
            demo()
        except KeyboardInterrupt:
            print("\nInterrupted")
            break

    print("\n" + "=" * 60)
    print("Complete! See vllm_control_plane_config_examples.md for details")


if __name__ == "__main__":
    main()
