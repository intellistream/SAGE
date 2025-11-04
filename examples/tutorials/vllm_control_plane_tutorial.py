"""Tutorial: SAGE vLLM Control Plane - Intelligent Request Scheduling

Demonstrates ControlPlaneVLLMService API usage with real examples.

Usage: python vllm_control_plane_tutorial.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from sage.common.components.sage_vllm import ControlPlaneVLLMService

    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    print("Warning: ControlPlaneVLLMService not available\n")


def demo_basic():
    """Basic single-instance usage."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Usage")
    print("=" * 60)

    config = {
        "scheduling_policy": "fifo",
        "instances": [
            {
                "instance_id": "llm-1",
                "host": "localhost",
                "port": 8000,
                "model_name": "meta-llama/Llama-2-7b-hf",
            }
        ],
    }

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

    config = {
        "scheduling_policy": "adaptive",
        "instances": [
            {
                "instance_id": f"llm-{i}",
                "host": "localhost",
                "port": 8000 + i,
                "model_name": "meta-llama/Llama-2-7b-hf",
            }
            for i in range(3)
        ],
    }

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
