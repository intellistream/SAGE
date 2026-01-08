# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Control Plane Usage Examples

This comprehensive example demonstrates:
1. Deployment scenarios (single-machine, multi-machine, hybrid)
2. Request priorities and SLO management
3. Scheduling policy usage and switching
4. Performance monitoring
5. Custom scheduling strategies

All examples use HTTP client mode - vLLM instances are accessed uniformly
via OpenAI-compatible API regardless of location (local or remote).
"""

import asyncio
import logging
import random

from control_plane import (
    ControlPlaneManager,
    ExecutionInstance,
    RequestMetadata,
    RequestPriority,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def example_local_single_machine():
    """
    Example 1: Local single-machine deployment (4 GPUs).

    Prerequisites:
        Start 4 vLLM servers on localhost ports 8000-8003:

        CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
            --model meta-llama/Llama-2-7b --port 8000
        CUDA_VISIBLE_DEVICES=1 python -m vllm.entrypoints.openai.api_server \
            --model meta-llama/Llama-2-7b --port 8001
        CUDA_VISIBLE_DEVICES=2 python -m vllm.entrypoints.openai.api_server \
            --model meta-llama/Llama-2-7b --port 8002
        CUDA_VISIBLE_DEVICES=3 python -m vllm.entrypoints.openai.api_server \
            --model meta-llama/Llama-2-7b --port 8003
    """
    logger.info("=== Example 1: Local Single Machine (4 GPUs) ===")

    # Create Control Plane
    cp = ControlPlaneManager(
        scheduling_policy="adaptive",
        routing_strategy="load_balanced",
    )

    # Register 4 local GPU instances
    for gpu_id in range(4):
        instance = ExecutionInstance(
            instance_id=f"local-gpu-{gpu_id}",
            host="localhost",
            port=8000 + gpu_id,
            model_name="meta-llama/Llama-2-7b",
            tensor_parallel_size=1,
            gpu_count=1,
        )
        cp.register_instance(instance)
        logger.info(f"Registered {instance.instance_id}")

    # Start Control Plane
    await cp.start()
    logger.info("Control Plane started")

    # Submit test requests
    requests = [
        RequestMetadata(
            request_id=f"req-{i}",
            prompt=f"Request {i}: Tell me about AI and machine learning",
            max_tokens=100,
            priority=RequestPriority.NORMAL,
        )
        for i in range(10)
    ]

    for request in requests:
        await cp.submit_request(request)
        logger.info(f"Submitted {request.request_id}")

    # Wait for processing
    await asyncio.sleep(5)

    # Get metrics
    metrics = cp.get_metrics()
    logger.info(f"Metrics: {metrics}")

    # Stop Control Plane
    await cp.stop()
    logger.info("Control Plane stopped")


async def example_multi_machine():
    """
    Example 2: Multi-machine deployment.

    Prerequisites:
        - Machine A (192.168.1.100): 4 GPUs running vLLM on ports 8000-8003
        - Machine B (192.168.1.101): 4 GPUs running vLLM on ports 8000-8003
        - Control Plane can run on any machine (even without GPU)
    """
    logger.info("=== Example 2: Multi-Machine (8 GPUs across 2 machines) ===")

    cp = ControlPlaneManager(
        scheduling_policy="cost_optimized",
        routing_strategy="load_balanced",
    )

    # Register Machine A's GPUs
    for gpu_id in range(4):
        instance = ExecutionInstance(
            instance_id=f"machine-a-gpu-{gpu_id}",
            host="192.168.1.100",
            port=8000 + gpu_id,
            model_name="meta-llama/Llama-2-7b",
            gpu_count=1,
        )
        cp.register_instance(instance)

    # Register Machine B's GPUs
    for gpu_id in range(4):
        instance = ExecutionInstance(
            instance_id=f"machine-b-gpu-{gpu_id}",
            host="192.168.1.101",
            port=8000 + gpu_id,
            model_name="meta-llama/Llama-2-7b",
            gpu_count=1,
        )
        cp.register_instance(instance)

    logger.info("Registered 8 GPUs across 2 machines")

    await cp.start()

    # Submit requests - Control Plane will schedule across all 8 GPUs
    for i in range(20):
        request = RequestMetadata(
            request_id=f"cross-machine-req-{i}",
            prompt=f"Request {i}: Explain quantum computing",
            max_tokens=150,
            priority=RequestPriority.HIGH if i < 5 else RequestPriority.NORMAL,
        )
        await cp.submit_request(request)

    await asyncio.sleep(10)
    await cp.stop()


async def example_mixed_deployment():
    """
    Example 3: Mixed deployment (local + remote).

    Use local GPUs first (low latency), overflow to remote when busy.
    """
    logger.info("=== Example 3: Mixed Local + Remote ===")

    cp = ControlPlaneManager(
        scheduling_policy="slo_aware",
        routing_strategy="load_balanced",
    )

    # Local GPUs (prioritized)
    for gpu_id in range(2):
        instance = ExecutionInstance(
            instance_id=f"local-gpu-{gpu_id}",
            host="localhost",
            port=8000 + gpu_id,
            model_name="meta-llama/Llama-2-7b",
            gpu_count=1,
        )
        cp.register_instance(instance)

    # Remote backup cluster
    for gpu_id in range(4):
        instance = ExecutionInstance(
            instance_id=f"remote-gpu-{gpu_id}",
            host="192.168.1.200",
            port=8000 + gpu_id,
            model_name="meta-llama/Llama-2-7b",
            gpu_count=1,
        )
        cp.register_instance(instance)

    await cp.start()

    # High priority requests (will use local first)
    for i in range(5):
        request = RequestMetadata(
            request_id=f"priority-req-{i}",
            prompt=f"Urgent: {i}",
            max_tokens=50,
            priority=RequestPriority.CRITICAL,
            slo_deadline_ms=500,
        )
        await cp.submit_request(request)

    await asyncio.sleep(3)
    await cp.stop()


async def example_custom_scheduling():
    """
    Example 4: Custom scheduling policy implementation focus.

    The key benefit: You can now focus purely on implementing
    scheduling strategies without worrying about vLLM integration.
    """
    logger.info("=== Example 4: Custom Scheduling Focus ===")

    # With HTTP client mode, you can:
    # 1. Implement custom scheduling policies in policies.py
    # 2. Optimize for different metrics (latency, cost, throughput)
    # 3. Not worry about GPU management or vLLM internals

    cp = ControlPlaneManager(
        scheduling_policy="adaptive",  # Or your custom policy
    )

    # Register instances (transparent whether local or remote)
    instances = [
        ExecutionInstance(
            instance_id=f"gpu-{i}",
            host="localhost" if i < 2 else "192.168.1.100",
            port=8000 + (i % 4),
            model_name="meta-llama/Llama-2-7b",
            gpu_count=1,
        )
        for i in range(6)
    ]

    for instance in instances:
        cp.register_instance(instance)

    await cp.start()

    # Your custom scheduling policy will decide how to distribute these
    requests = [
        RequestMetadata(
            request_id=f"custom-{i}",
            prompt=f"Custom scheduling request {i}",
            max_tokens=100,
            priority=RequestPriority.HIGH if i % 2 == 0 else RequestPriority.LOW,
            slo_deadline_ms=1000 if i < 5 else None,
        )
        for i in range(15)
    ]

    for request in requests:
        await cp.submit_request(request)

    await asyncio.sleep(5)

    # Check how scheduling performed
    all_instances = cp.executor.get_all_instances()
    for instance in all_instances:
        logger.info(
            f"{instance.instance_id}: load={instance.current_load:.2f}, "
            f"active={instance.active_requests}, "
            f"avg_latency={instance.avg_latency_ms:.2f}ms"
        )

    await cp.stop()


async def example_priorities_and_monitoring():
    """
    Example 5: Priority-based scheduling with performance monitoring.

    Demonstrates different request priorities and real-time monitoring.
    """
    logger.info("=== Example 5: Priorities and Monitoring ===")

    cp = ControlPlaneManager(
        scheduling_policy="priority",
        routing_strategy="load_balanced",
        enable_monitoring=True,
    )

    # Setup 4 local instances
    for i in range(4):
        instance = ExecutionInstance(
            instance_id=f"gpu-{i}",
            host="localhost",
            port=8000 + i,
            model_name="meta-llama/Llama-2-7b",
            gpu_count=1,
        )
        cp.register_instance(instance)

    await cp.start()
    logger.info("Control Plane started with 4 instances")

    # Submit requests with different priorities
    logger.info("Submitting requests with different priorities...")

    # Critical requests (highest priority)
    for i in range(2):
        request = RequestMetadata(
            request_id=f"critical-{i}",
            prompt=f"URGENT: Critical request {i}",
            max_tokens=50,
            priority=RequestPriority.CRITICAL,
            slo_deadline_ms=500,
        )
        await cp.submit_request(request)
    logger.info("✓ Submitted 2 CRITICAL requests (SLO: 500ms)")

    # High priority requests
    for i in range(3):
        request = RequestMetadata(
            request_id=f"high-{i}",
            prompt=f"High priority request {i}",
            max_tokens=100,
            priority=RequestPriority.HIGH,
            slo_deadline_ms=1000,
        )
        await cp.submit_request(request)
    logger.info("✓ Submitted 3 HIGH priority requests (SLO: 1000ms)")

    # Normal requests
    for i in range(10):
        request = RequestMetadata(
            request_id=f"normal-{i}",
            prompt=f"Normal request {i}: {random.choice(['Explain AI', 'What is ML', 'Tell me about Python'])}",
            max_tokens=random.randint(50, 150),
            priority=RequestPriority.NORMAL,
            slo_deadline_ms=2000,
        )
        await cp.submit_request(request)
    logger.info("✓ Submitted 10 NORMAL priority requests (SLO: 2000ms)")

    # Low priority batch requests
    for i in range(5):
        request = RequestMetadata(
            request_id=f"low-{i}",
            prompt=f"Batch request {i}",
            max_tokens=200,
            priority=RequestPriority.LOW,
        )
        await cp.submit_request(request)
    logger.info("✓ Submitted 5 LOW priority batch requests")

    # Monitor performance for 10 seconds
    logger.info("\nMonitoring performance...")
    for sec in range(10):
        await asyncio.sleep(1)

        status = cp.get_status()
        metrics = cp.get_metrics()

        logger.info(
            f"[{sec + 1}s] Pending: {status['pending_requests']}, "
            f"Running: {status['running_requests']}, "
            f"Completed: {metrics.completed_requests}, "
            f"Avg Latency: {metrics.avg_latency_ms:.2f}ms, "
            f"SLO Compliance: {metrics.slo_compliance_rate:.1%}"
        )

        # Show instance loads
        if sec % 3 == 0:
            logger.info("  Instance Status:")
            for instance in cp.get_instances():
                inst_metrics = cp.get_instance_metrics(instance.instance_id)
                if inst_metrics:
                    logger.info(
                        f"    {instance.instance_id}: "
                        f"Load={inst_metrics['current_load']:.1%}, "
                        f"Active={inst_metrics['active_requests']}, "
                        f"Healthy={inst_metrics['is_healthy']}"
                    )

    # Final report
    final_metrics = cp.get_metrics()
    logger.info("\n=== Final Metrics ===")
    logger.info(f"Total Requests: {final_metrics.total_requests}")
    logger.info(f"Completed: {final_metrics.completed_requests}")
    logger.info(f"Failed: {final_metrics.failed_requests}")
    logger.info(f"SLO Violations: {final_metrics.slo_violations}")
    logger.info(f"SLO Compliance Rate: {final_metrics.slo_compliance_rate:.2%}")
    logger.info(f"Average Latency: {final_metrics.avg_latency_ms:.2f}ms")

    await cp.stop()


async def example_policy_switching():
    """
    Example 6: Dynamic policy switching demonstration.

    Shows how to change scheduling policies at runtime.
    """
    logger.info("=== Example 6: Dynamic Policy Switching ===")

    cp = ControlPlaneManager(
        scheduling_policy="fifo",  # Start with FIFO
        routing_strategy="load_balanced",
    )

    # Setup instances
    for i in range(3):
        instance = ExecutionInstance(
            instance_id=f"gpu-{i}",
            host="localhost",
            port=8000 + i,
            model_name="meta-llama/Llama-2-7b",
            gpu_count=1,
        )
        cp.register_instance(instance)

    await cp.start()

    # Test different policies
    policies = [
        ("fifo", "First-In-First-Out"),
        ("priority", "Priority-based"),
        ("slo_aware", "SLO-aware"),
        ("cost_optimized", "Cost-optimized"),
        ("adaptive", "Adaptive"),
    ]

    for policy_name, policy_desc in policies:
        logger.info(f"\n--- Testing {policy_desc} Policy ---")
        cp.update_policy(policy_name)

        # Submit test requests
        for i in range(5):
            request = RequestMetadata(
                request_id=f"{policy_name}-req-{i}",
                prompt=f"Test request for {policy_desc} policy",
                max_tokens=50,
                priority=random.choice(list(RequestPriority)),
                slo_deadline_ms=random.choice([500, 1000, 2000]) if random.random() > 0.3 else None,
            )
            await cp.submit_request(request)

        # Let it process
        await asyncio.sleep(2)

        metrics = cp.get_metrics()
        logger.info(
            f"{policy_desc} - Completed: {metrics.completed_requests}, "
            f"Avg Latency: {metrics.avg_latency_ms:.2f}ms"
        )

    await cp.stop()
    logger.info("\nPolicy switching demonstration completed")


async def main():
    """Run examples."""
    print("\n" + "=" * 70)
    print("Control Plane HTTP Client Mode Examples")
    print("=" * 70 + "\n")

    # Uncomment the example you want to run:

    # await example_local_single_machine()
    # await example_multi_machine()
    # await example_mixed_deployment()
    # await example_custom_scheduling()
    await example_priorities_and_monitoring()
    # await example_policy_switching()

    print("\n" + "=" * 70)
    print("Example completed! Check logs above for details.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
