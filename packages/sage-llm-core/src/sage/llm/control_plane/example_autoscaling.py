# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Example: Using Control Plane with Autoscaling.

This example demonstrates how to use the sageLLM Control Plane with
SLA-based autoscaling for Prefill/Decode instances.
"""

import asyncio
import logging

from control_plane import (
    AutoscalerConfig,
    ControlPlaneManager,
    DecodingConfig,
    ExecutionInstance,
    ExecutionInstanceType,
    PDSeparationConfig,
    PreffillingConfig,
    RequestMetadata,
    RequestPriority,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """Main example demonstrating autoscaling."""

    # ===== 1. Configure Autoscaler =====
    autoscaler_config = AutoscalerConfig(
        # SLA targets
        target_ttft_ms=200.0,  # Target Time To First Token
        target_itl_ms=50.0,  # Target Inter-Token Latency
        # Scaling parameters
        adjustment_interval_sec=60,  # Adjust every 60 seconds
        min_prefill_instances=1,
        max_prefill_instances=5,
        min_decode_instances=2,
        max_decode_instances=10,
        # GPU budget
        max_gpu_budget=24,  # Total GPU budget
        prefill_gpus_per_instance=4,  # Prefill uses 4 GPUs
        decode_gpus_per_instance=1,  # Decode uses 1 GPU
        # Load prediction
        load_predictor_type="moving_average",  # constant, moving_average, arima, prophet
        prediction_window_size=10,
        # Performance profiles (optional)
        profile_data_dir=None,  # Set to profile directory if available
        enable_online_learning=True,  # Use online learning if no profiles
        # Correction factors
        enable_correction=True,  # Enable correction factors
        # Dry-run mode (for testing)
        no_operation=False,  # Set True to see decisions without applying
    )

    # ===== 2. Configure PD Separation =====
    pd_config = PDSeparationConfig(
        enabled=True,
        routing_policy="adaptive",
        prefilling_threshold_input_tokens=800,
        prefilling_threshold_ratio=4.0,
    )

    # ===== 3. Create Control Plane with Autoscaling =====
    manager = ControlPlaneManager(
        scheduling_policy="adaptive",
        routing_strategy="load_balanced",
        enable_auto_scaling=True,  # Enable autoscaling
        enable_monitoring=True,
        enable_pd_separation=True,
        pd_config=pd_config,
        autoscaler_config=autoscaler_config,
    )

    # Initialize executor HTTP session
    await manager.executor.initialize()

    # ===== 4. Register Initial Instances =====
    # These instances should be running vLLM servers

    # Prefilling instance (high throughput)
    prefilling_instance = ExecutionInstance(
        instance_id="prefill-1",
        host="localhost",
        port=8001,
        model_name="meta-llama/Llama-2-7b",
        tensor_parallel_size=4,
        gpu_count=4,
        instance_type=ExecutionInstanceType.PREFILLING,
        prefilling_config=PreffillingConfig(
            target_batch_size=64,
            tensor_parallel_size=4,
            enable_chunked_prefill=True,
        ),
    )

    # Decoding instances (low latency)
    decoding_instance_1 = ExecutionInstance(
        instance_id="decode-1",
        host="localhost",
        port=8002,
        model_name="meta-llama/Llama-2-7b",
        tensor_parallel_size=1,
        gpu_count=1,
        instance_type=ExecutionInstanceType.DECODING,
        decoding_config=DecodingConfig(
            target_latency_ms=50,
            max_parallel_requests=200,
        ),
    )

    decoding_instance_2 = ExecutionInstance(
        instance_id="decode-2",
        host="localhost",
        port=8003,
        model_name="meta-llama/Llama-2-7b",
        tensor_parallel_size=1,
        gpu_count=1,
        instance_type=ExecutionInstanceType.DECODING,
        decoding_config=DecodingConfig(
            target_latency_ms=50,
            max_parallel_requests=200,
        ),
    )

    manager.register_instance(prefilling_instance)
    manager.register_instance(decoding_instance_1)
    manager.register_instance(decoding_instance_2)

    logger.info("Registered instances:")
    for instance in manager.get_instances():
        logger.info(
            f"  - {instance.instance_id}: {instance.instance_type.name}, "
            f"{instance.host}:{instance.port}, GPUs={instance.gpu_count}"
        )

    # ===== 5. Start Control Plane =====
    await manager.start()

    logger.info("Control Plane started with autoscaling enabled")
    logger.info("=" * 60)

    # ===== 6. Submit Requests =====
    # In a real application, requests would come from users
    # Here we simulate a few requests

    requests = [
        RequestMetadata(
            request_id=f"req-{i}",
            prompt=f"Example prompt {i} " * (100 if i % 2 == 0 else 10),
            priority=RequestPriority.NORMAL,
            max_tokens=512,
        )
        for i in range(5)
    ]

    for request in requests:
        await manager.submit_request(request)
        logger.info(f"Submitted request: {request.request_id}")

    # ===== 7. Monitor Autoscaler =====
    logger.info("=" * 60)
    logger.info("Monitoring autoscaler (will run for 5 minutes)...")
    logger.info("The autoscaler will:")
    logger.info("  - Collect metrics every 60 seconds")
    logger.info("  - Predict future load")
    logger.info("  - Calculate required instances")
    logger.info("  - Scale up/down as needed")
    logger.info("=" * 60)

    # Run for 5 minutes (5 autoscaling cycles)
    for cycle in range(5):
        await asyncio.sleep(60)

        # Get autoscaler status
        status = manager.get_autoscaler_status()
        logger.info(f"\n--- Autoscaler Status (Cycle {cycle + 1}) ---")
        logger.info(f"  Running: {status.get('running', False)}")
        logger.info(f"  Correction Factors: {status.get('correction_factors', {})}")

        # Get current instance counts
        instances = manager.get_instances()
        prefill_count = sum(
            1 for i in instances if i.instance_type == ExecutionInstanceType.PREFILLING
        )
        decode_count = sum(
            1 for i in instances if i.instance_type == ExecutionInstanceType.DECODING
        )

        logger.info(f"  Current Instances: Prefill={prefill_count}, Decode={decode_count}")

        # Get control plane metrics
        metrics = manager.get_metrics()
        logger.info(f"  Active Requests: {metrics.active_requests}")
        logger.info(f"  Pending Requests: {len(manager.pending_queue)}")
        logger.info(f"  Completed Requests: {metrics.completed_requests}")

    # ===== 8. Cleanup =====
    logger.info("\n" + "=" * 60)
    logger.info("Shutting down...")
    await manager.stop()
    await manager.executor.cleanup()

    logger.info("Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
