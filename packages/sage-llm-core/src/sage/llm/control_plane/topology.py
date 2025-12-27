# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""GPU topology detection and management."""

import logging
import re
import socket
import subprocess
from typing import Any

from .types import ExecutionInstance

logger = logging.getLogger(__name__)


class TopologyDetector:
    """Detect GPU topology information for scheduling optimization."""

    @staticmethod
    def get_machine_id() -> str:
        """
        Get unique machine identifier.

        Uses hostname as the machine ID. In production, you might want to
        use DMI UUID or other hardware-based identifiers.

        Returns:
            Machine identifier string
        """
        return socket.gethostname()

    @staticmethod
    def detect_nvlink_topology() -> dict[int, list[int]]:
        """
        Detect NVLINK topology between GPUs.

        Uses nvidia-smi topo -m to detect NVLINK connections.

        Returns:
            Dictionary mapping GPU ID to list of connected GPU IDs
            Example: {0: [1, 2], 1: [0, 3], ...}
        """
        try:
            # Run nvidia-smi topo -m
            result = subprocess.run(
                ["nvidia-smi", "topo", "-m"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning("nvidia-smi topo -m failed: %s", result.stderr)
                return {}

            # Parse output
            topology = TopologyDetector._parse_nvlink_output(result.stdout)
            logger.info("Detected NVLINK topology: %s", topology)
            return topology

        except FileNotFoundError:
            logger.warning("nvidia-smi not found, skipping NVLINK detection")
            return {}
        except subprocess.TimeoutExpired:
            logger.error("nvidia-smi topo -m timed out")
            return {}
        except Exception as e:
            logger.error("Failed to detect NVLINK topology: %s", e)
            return {}

    @staticmethod
    def _parse_nvlink_output(output: str) -> dict[int, list[int]]:
        """
        Parse nvidia-smi topo -m output.

        The output looks like:
                GPU0    GPU1    GPU2    GPU3
        GPU0     X      NV12    NV12    NV12
        GPU1    NV12     X      NV12    NV12
        ...

        NV* indicates NVLINK connection.

        Args:
            output: nvidia-smi topo -m output

        Returns:
            NVLINK topology dictionary
        """
        topology: dict[int, list[int]] = {}
        lines = output.strip().split("\n")

        # Find the header line (contains GPU0, GPU1, ...)
        header_idx = -1
        for i, line in enumerate(lines):
            if "GPU0" in line and "GPU1" in line:
                header_idx = i
                break

        if header_idx == -1:
            logger.warning("Could not find GPU header in nvidia-smi output")
            return {}

        # Parse data lines
        for line in lines[header_idx + 1 :]:
            if not line.strip() or not line.startswith("GPU"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            # Extract GPU ID
            gpu_match = re.match(r"GPU(\d+)", parts[0])
            if not gpu_match:
                continue

            gpu_id = int(gpu_match.group(1))
            topology[gpu_id] = []

            # Check connections (NV indicates NVLINK)
            for i, conn in enumerate(parts[1:]):
                if conn.startswith("NV"):
                    # Connected via NVLINK
                    topology[gpu_id].append(i)

        return topology

    @staticmethod
    def detect_numa_nodes() -> dict[int, int]:
        """
        Detect NUMA node for each GPU.

        Uses nvidia-smi topo -m to detect NUMA affinity.

        Returns:
            Dictionary mapping GPU ID to NUMA node
            Example: {0: 0, 1: 0, 2: 1, 3: 1}
        """
        try:
            result = subprocess.run(
                ["nvidia-smi", "topo", "-m"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {}

            # Parse NUMA information from output
            numa_map = TopologyDetector._parse_numa_output(result.stdout)
            logger.info("Detected NUMA mapping: %s", numa_map)
            return numa_map

        except Exception as e:
            logger.error("Failed to detect NUMA nodes: %s", e)
            return {}

    @staticmethod
    def _parse_numa_output(output: str) -> dict[int, int]:
        """
        Parse NUMA information from nvidia-smi output.

        Args:
            output: nvidia-smi output

        Returns:
            GPU to NUMA node mapping
        """
        # This is a simplified parser. In production, you might need
        # more sophisticated parsing based on your system's output format.
        numa_map: dict[int, int] = {}

        # Try to extract NUMA info from "Affinity" or "CPU Affinity" lines
        lines = output.strip().split("\n")
        for line in lines:
            if "CPU Affinity" in line or "NUMA" in line:
                # Example: "GPU0  CPU Affinity: 0-23"
                match = re.search(r"GPU(\d+).*?(\d+)", line)
                if match:
                    gpu_id = int(match.group(1))
                    numa_node = int(match.group(2))
                    numa_map[gpu_id] = numa_node

        return numa_map

    @staticmethod
    def get_gpu_bus_id(gpu_id: int) -> str | None:
        """
        Get PCIe bus ID for a GPU.

        Args:
            gpu_id: CUDA device ID

        Returns:
            PCIe bus ID (e.g., "0000:01:00.0") or None if not found
        """
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--id={gpu_id}",
                    "--query-gpu=pci.bus_id",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                bus_id = result.stdout.strip()
                return bus_id if bus_id else None

        except Exception as e:
            logger.error("Failed to get GPU bus ID for GPU %d: %s", gpu_id, e)

        return None

    @staticmethod
    def create_instance_with_topology(
        instance_id: str,
        gpu_id: int,
        host: str,
        port: int,
        model_name: str,
        **kwargs: Any,
    ) -> ExecutionInstance:
        """
        Create an ExecutionInstance with auto-detected topology information.

        Args:
            instance_id: Instance identifier
            gpu_id: CUDA device ID
            host: Host address
            port: Port number
            model_name: Model name
            **kwargs: Additional ExecutionInstance parameters

        Returns:
            ExecutionInstance with topology information
        """
        # Detect machine ID
        machine_id = TopologyDetector.get_machine_id()

        # Detect NVLINK topology
        nvlink_topology = TopologyDetector.detect_nvlink_topology()
        nvlink_peers_ids = nvlink_topology.get(gpu_id, [])

        # Convert GPU IDs to instance IDs (assuming naming pattern)
        # This is a simple heuristic - in production, you'd need a registry
        nvlink_peers = [
            f"{instance_id.rsplit('-', 1)[0]}-{peer_id}" for peer_id in nvlink_peers_ids
        ]

        # Detect NUMA node
        numa_nodes = TopologyDetector.detect_numa_nodes()
        numa_node = numa_nodes.get(gpu_id)

        # Get bus ID
        gpu_bus_id = TopologyDetector.get_gpu_bus_id(gpu_id)

        # Create instance
        instance = ExecutionInstance(
            instance_id=instance_id,
            host=host,
            port=port,
            model_name=model_name,
            machine_id=machine_id,
            gpu_device_id=gpu_id,
            gpu_bus_id=gpu_bus_id,
            nvlink_peers=nvlink_peers,
            numa_node=numa_node,
            **kwargs,
        )

        logger.info(
            "Created instance %s with topology: machine=%s, nvlink_peers=%s, numa=%s",
            instance_id,
            machine_id,
            nvlink_peers,
            numa_node,
        )

        return instance

    @staticmethod
    def auto_detect_local_instances(
        base_instance_id: str,
        host: str,
        base_port: int,
        model_name: str,
        **kwargs: Any,
    ) -> list[ExecutionInstance]:
        """
        Auto-detect all local GPUs and create instances.

        Args:
            base_instance_id: Base name for instances (will append GPU ID)
            host: Host address
            base_port: Base port number (will increment for each GPU)
            model_name: Model name
            **kwargs: Additional ExecutionInstance parameters

        Returns:
            List of ExecutionInstances with topology information
        """
        instances: list[ExecutionInstance] = []

        try:
            # Get GPU count
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=count", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                logger.warning("Could not detect GPU count")
                return instances

            gpu_count = int(result.stdout.strip().split("\n")[0])
            logger.info("Detected %d GPUs", gpu_count)

            # Create instance for each GPU
            for gpu_id in range(gpu_count):
                instance = TopologyDetector.create_instance_with_topology(
                    instance_id=f"{base_instance_id}-{gpu_id}",
                    gpu_id=gpu_id,
                    host=host,
                    port=base_port + gpu_id,
                    model_name=model_name,
                    **kwargs,
                )
                instances.append(instance)

        except Exception as e:
            logger.error("Failed to auto-detect local instances: %s", e)

        return instances
