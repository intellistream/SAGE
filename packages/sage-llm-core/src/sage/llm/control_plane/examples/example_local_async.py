# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Minimal example demonstrating local async execution coordinator usage.

This example shows:
- Create a ControlPlaneManager in local mode
- Register one local ExecutionInstance (vLLM engine mode)
- Submit a single request
- Wait briefly for processing and stop the control plane

Notes:
- LocalAsyncExecutionCoordinator depends on vLLM being installed and
  compiled with the async engine available. If vLLM is unavailable this
  example may raise on instance registration or execution.
"""

import asyncio
import logging
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# flake8: noqa: E402
from control_plane import (
    ControlPlaneManager,
    ExecutionInstance,
    RequestMetadata,
    RequestPriority,
)

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_local_async_one_request():
    logger.info("=== Example: Local Async - single request ===")

    # Create Control Plane with local executor
    cp = ControlPlaneManager(mode="local")

    # Register a single local engine-backed instance
    # Note: Adjust model_name and device/engine settings to your environment
    instance = ExecutionInstance(
        instance_id="local-engine-0",
        model_name="/home/smh/Qwen3-4B",
        host="localhost",
        port=0,  # port is unused for local engines but kept for compatibility
        tensor_parallel_size=1,
        pipeline_parallel_size=1,
        gpu_count=1,
    )

    try:
        cp.register_instance(instance)
        logger.info("Registered instance %s", instance.instance_id)
    except Exception as e:
        logger.exception(
            "Failed to register local instance (vLLM engine may be unavailable): %s",
            e,
        )

    # Start control plane background tasks
    await cp.start()

    # Submit a single request
    req = RequestMetadata(
        request_id="local-req-0",
        prompt="Write a short poem about autumn.",
        max_tokens=64,
        priority=RequestPriority.NORMAL,
        model_name=instance.model_name,
    )

    await cp.submit_request(req)
    logger.info("Submitted request %s", req.request_id)

    # Wait briefly to allow the scheduling loop to pick up the request
    await asyncio.sleep(5)

    # Print metrics
    metrics = cp.get_metrics()
    logger.info("Metrics after run: %s", metrics)

    # Stop control plane
    await cp.stop()
    logger.info("Control Plane stopped")


async def main():
    await example_local_async_one_request()


if __name__ == "__main__":
    asyncio.run(main())
