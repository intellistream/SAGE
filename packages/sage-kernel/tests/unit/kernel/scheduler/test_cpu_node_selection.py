"""
Test CPU Node Selection and Resource Allocation

Tests for CPU-only node support in SAGE:
- CPU node selection via NodeSelector
- Resource requirements (CPU, memory, no GPU)
- Scheduling strategies for CPU nodes
- Node filtering and ranking
"""

import time

import pytest

from sage.kernel.scheduler.decision import PlacementDecision
from sage.kernel.scheduler.node_selector import NodeResources, NodeSelector


class TestNodeResources:
    """Test NodeResources dataclass"""

    def test_can_fit_cpu_only(self):
        """Test that CPU-only nodes can fit CPU-only tasks"""
        node = NodeResources(
            node_id="cpu-node-1",
            hostname="cpu-worker-1",
            address="192.168.1.100",
            total_cpu=8.0,
            total_gpu=0.0,  # No GPU
            total_memory=16 * 1024**3,  # 16GB
            custom_resources={},
            available_cpu=6.0,
            available_gpu=0.0,
            available_memory=12 * 1024**3,
            cpu_usage=0.25,
            gpu_usage=0.0,
            memory_usage=0.25,
            task_count=2,
        )

        # Can fit CPU-only task
        assert node.can_fit(cpu_required=4, gpu_required=0, memory_required=8 * 1024**3)

        # Cannot fit task requiring more CPU
        assert not node.can_fit(cpu_required=8, gpu_required=0)

        # Cannot fit task requiring GPU (node has 0 GPU)
        assert not node.can_fit(cpu_required=2, gpu_required=1)

    def test_can_fit_insufficient_memory(self):
        """Test node rejection when memory is insufficient"""
        node = NodeResources(
            node_id="cpu-node-2",
            hostname="cpu-worker-2",
            address="192.168.1.101",
            total_cpu=16.0,
            total_gpu=0.0,
            total_memory=8 * 1024**3,  # Only 8GB
            custom_resources={},
            available_cpu=14.0,
            available_gpu=0.0,
            available_memory=4 * 1024**3,  # Only 4GB available
            cpu_usage=0.125,
            gpu_usage=0.0,
            memory_usage=0.5,
            task_count=1,
        )

        # Cannot fit task requiring 8GB when only 4GB available
        assert not node.can_fit(cpu_required=2, gpu_required=0, memory_required=8 * 1024**3)

        # Can fit smaller task
        assert node.can_fit(cpu_required=2, gpu_required=0, memory_required=2 * 1024**3)

    def test_compute_score_balanced(self):
        """Test balanced strategy scoring (lower usage = better score = lower value)"""
        # Low usage node (better for balanced)
        node_low = NodeResources(
            node_id="cpu-node-low",
            hostname="cpu-low",
            address="192.168.1.100",
            total_cpu=8.0,
            total_gpu=0.0,
            total_memory=16 * 1024**3,
            custom_resources={},
            available_cpu=6.0,
            available_gpu=0.0,
            available_memory=12 * 1024**3,
            cpu_usage=0.25,  # 25% CPU usage
            gpu_usage=0.0,
            memory_usage=0.25,  # 25% memory usage
        )

        # High usage node (worse for balanced)
        node_high = NodeResources(
            node_id="cpu-node-high",
            hostname="cpu-high",
            address="192.168.1.101",
            total_cpu=8.0,
            total_gpu=0.0,
            total_memory=16 * 1024**3,
            custom_resources={},
            available_cpu=2.0,
            available_gpu=0.0,
            available_memory=4 * 1024**3,
            cpu_usage=0.75,  # 75% CPU usage
            gpu_usage=0.0,
            memory_usage=0.75,  # 75% memory usage
        )

        score_low = node_low.compute_score(strategy="balanced")
        score_high = node_high.compute_score(strategy="balanced")

        # Lower usage should have lower (better) score
        assert score_low < score_high

    def test_compute_score_pack(self):
        """Test pack strategy scoring (higher usage = better score = lower value)"""
        node_low = NodeResources(
            node_id="cpu-node-low",
            hostname="cpu-low",
            address="192.168.1.100",
            total_cpu=8.0,
            total_gpu=0.0,
            total_memory=16 * 1024**3,
            custom_resources={},
            available_cpu=6.0,
            available_gpu=0.0,
            available_memory=12 * 1024**3,
            cpu_usage=0.25,
            gpu_usage=0.0,
            memory_usage=0.25,
        )

        node_high = NodeResources(
            node_id="cpu-node-high",
            hostname="cpu-high",
            address="192.168.1.101",
            total_cpu=8.0,
            total_gpu=0.0,
            total_memory=16 * 1024**3,
            custom_resources={},
            available_cpu=2.0,
            available_gpu=0.0,
            available_memory=4 * 1024**3,
            cpu_usage=0.75,
            gpu_usage=0.0,
            memory_usage=0.75,
        )

        score_low = node_low.compute_score(strategy="pack")
        score_high = node_high.compute_score(strategy="pack")

        # Higher usage should have lower (better) score for packing
        assert score_high < score_low


class TestNodeSelector:
    """Test NodeSelector for CPU node selection"""

    def test_select_cpu_only_node(self):
        """Test selecting a CPU-only node (no GPU required)"""
        selector = NodeSelector()

        # Mock node cache with CPU-only nodes
        selector.node_cache = {
            "cpu-node-1": NodeResources(
                node_id="cpu-node-1",
                hostname="cpu-worker-1",
                address="192.168.1.100",
                total_cpu=8.0,
                total_gpu=0.0,
                total_memory=16 * 1024**3,
                custom_resources={},
                available_cpu=6.0,
                available_gpu=0.0,
                available_memory=12 * 1024**3,
                cpu_usage=0.25,
                gpu_usage=0.0,
                memory_usage=0.25,
                task_count=2,
            ),
            "cpu-node-2": NodeResources(
                node_id="cpu-node-2",
                hostname="cpu-worker-2",
                address="192.168.1.101",
                total_cpu=16.0,
                total_gpu=0.0,
                total_memory=32 * 1024**3,
                custom_resources={},
                available_cpu=14.0,
                available_gpu=0.0,
                available_memory=28 * 1024**3,
                cpu_usage=0.125,
                gpu_usage=0.0,
                memory_usage=0.125,
                task_count=1,
            ),
        }
        # Prevent cache update from overwriting our mock data
        selector.last_update = time.time()

        # Select node for CPU-only task
        node_id = selector.select_best_node(cpu_required=4, gpu_required=0, strategy="balanced")

        assert node_id is not None
        assert node_id in ["cpu-node-1", "cpu-node-2"]

        # Should select cpu-node-2 (lower usage)
        assert node_id == "cpu-node-2"

    def test_reject_gpu_task_on_cpu_nodes(self):
        """Test that tasks requiring GPU are rejected on CPU-only nodes"""
        selector = NodeSelector()

        # Mock cache with only CPU nodes (no GPU)
        selector.node_cache = {
            "cpu-node-1": NodeResources(
                node_id="cpu-node-1",
                hostname="cpu-worker-1",
                address="192.168.1.100",
                total_cpu=8.0,
                total_gpu=0.0,  # No GPU
                total_memory=16 * 1024**3,
                custom_resources={},
                available_cpu=6.0,
                available_gpu=0.0,
                available_memory=12 * 1024**3,
                cpu_usage=0.25,
                gpu_usage=0.0,
                memory_usage=0.25,
            ),
        }
        # Prevent cache update from overwriting our mock data
        selector.last_update = time.time()

        # Try to select node for GPU task
        node_id = selector.select_best_node(
            cpu_required=2,
            gpu_required=1,  # Requires GPU
        )

        # Should return None (no suitable node)
        assert node_id is None

    def test_balanced_strategy_selects_lowest_usage(self):
        """Test that balanced strategy selects the node with lowest usage"""
        selector = NodeSelector()

        selector.node_cache = {
            "cpu-node-low": NodeResources(
                node_id="cpu-node-low",
                hostname="cpu-low",
                address="192.168.1.100",
                total_cpu=8.0,
                total_gpu=0.0,
                total_memory=16 * 1024**3,
                custom_resources={},
                available_cpu=7.0,
                available_gpu=0.0,
                available_memory=14 * 1024**3,
                cpu_usage=0.125,  # 12.5% usage (lowest)
                gpu_usage=0.0,
                memory_usage=0.125,
            ),
            "cpu-node-med": NodeResources(
                node_id="cpu-node-med",
                hostname="cpu-med",
                address="192.168.1.101",
                total_cpu=8.0,
                total_gpu=0.0,
                total_memory=16 * 1024**3,
                custom_resources={},
                available_cpu=5.0,
                available_gpu=0.0,
                available_memory=10 * 1024**3,
                cpu_usage=0.375,  # 37.5% usage
                gpu_usage=0.0,
                memory_usage=0.375,
            ),
            "cpu-node-high": NodeResources(
                node_id="cpu-node-high",
                hostname="cpu-high",
                address="192.168.1.102",
                total_cpu=8.0,
                total_gpu=0.0,
                total_memory=16 * 1024**3,
                custom_resources={},
                available_cpu=2.0,
                available_gpu=0.0,
                available_memory=4 * 1024**3,
                cpu_usage=0.75,  # 75% usage (highest)
                gpu_usage=0.0,
                memory_usage=0.75,
            ),
        }
        # Prevent cache update from overwriting our mock data
        selector.last_update = time.time()

        node_id = selector.select_best_node(cpu_required=1, gpu_required=0, strategy="balanced")

        # Should select the node with lowest usage
        assert node_id == "cpu-node-low"

    def test_pack_strategy_selects_highest_usage(self):
        """Test that pack strategy selects the node with highest usage"""
        selector = NodeSelector()

        selector.node_cache = {
            "cpu-node-low": NodeResources(
                node_id="cpu-node-low",
                hostname="cpu-low",
                address="192.168.1.100",
                total_cpu=8.0,
                total_gpu=0.0,
                total_memory=16 * 1024**3,
                custom_resources={},
                available_cpu=7.0,
                available_gpu=0.0,
                available_memory=14 * 1024**3,
                cpu_usage=0.125,
                gpu_usage=0.0,
                memory_usage=0.125,
            ),
            "cpu-node-high": NodeResources(
                node_id="cpu-node-high",
                hostname="cpu-high",
                address="192.168.1.102",
                total_cpu=8.0,
                total_gpu=0.0,
                total_memory=16 * 1024**3,
                custom_resources={},
                available_cpu=4.0,  # Still can fit task
                available_gpu=0.0,
                available_memory=8 * 1024**3,
                cpu_usage=0.5,  # Higher usage
                gpu_usage=0.0,
                memory_usage=0.5,
            ),
        }
        # Prevent cache update from overwriting our mock data
        selector.last_update = time.time()

        node_id = selector.select_best_node(cpu_required=2, gpu_required=0, strategy="pack")

        # Should select the node with higher usage (pack strategy)
        assert node_id == "cpu-node-high"

    def test_get_cluster_stats(self):
        """Test getting cluster statistics for CPU nodes"""
        selector = NodeSelector()

        selector.node_cache = {
            "cpu-node-1": NodeResources(
                node_id="cpu-node-1",
                hostname="cpu-worker-1",
                address="192.168.1.100",
                total_cpu=8.0,
                total_gpu=0.0,
                total_memory=16 * 1024**3,
                custom_resources={},
                available_cpu=6.0,
                available_gpu=0.0,
                available_memory=12 * 1024**3,
                cpu_usage=0.25,
                gpu_usage=0.0,
                memory_usage=0.25,
                task_count=2,
            ),
            "cpu-node-2": NodeResources(
                node_id="cpu-node-2",
                hostname="cpu-worker-2",
                address="192.168.1.101",
                total_cpu=16.0,
                total_gpu=0.0,
                total_memory=32 * 1024**3,
                custom_resources={},
                available_cpu=12.0,
                available_gpu=0.0,
                available_memory=24 * 1024**3,
                cpu_usage=0.25,
                gpu_usage=0.0,
                memory_usage=0.25,
                task_count=3,
            ),
        }
        # Prevent cache update from overwriting our mock data
        selector.last_update = time.time()

        # Track tasks
        selector.node_task_count = {"cpu-node-1": 2, "cpu-node-2": 3}

        stats = selector.get_cluster_stats()

        assert stats["node_count"] == 2
        assert stats["total_cpu"] == 24.0  # 8 + 16
        assert stats["total_gpu"] == 0.0  # CPU only
        assert stats["total_memory"] == 48 * 1024**3  # 16 + 32 GB
        assert stats["available_cpu"] == 18.0  # 6 + 12
        assert stats["total_tasks"] == 5  # 2 + 3
        assert stats["avg_cpu_usage"] == 0.25


class TestCPUScheduling:
    """Test CPU-only scheduling scenarios"""

    def test_cpu_task_placement_decision(self):
        """Test that CPU tasks get proper placement decisions"""
        from sage.kernel.scheduler.api import BaseScheduler

        class MockCPUScheduler(BaseScheduler):
            def make_decision(self, task_node):
                """Simple CPU scheduling decision"""
                return PlacementDecision(
                    target_node="cpu-node-1",
                    resource_requirements={"cpu": 2, "memory": "2GB", "gpu": 0},
                    placement_strategy="cpu_only",
                    reason="CPU task assigned to CPU node",
                )

        scheduler = MockCPUScheduler()

        # Mock task node
        class MockTaskNode:
            name = "cpu_task"
            transformation = None

        decision = scheduler.make_decision(MockTaskNode())

        assert decision.target_node == "cpu-node-1"
        assert decision.resource_requirements["cpu"] == 2
        assert decision.resource_requirements["gpu"] == 0
        assert decision.placement_strategy == "cpu_only"

    def test_cpu_resource_requirements_extraction(self):
        """Test extracting CPU resource requirements from operator"""

        class MockCPUOperator:
            cpu_required = 4
            memory_required = "4GB"
            gpu_required = 0

        op = MockCPUOperator()

        # Extract requirements
        cpu = getattr(op, "cpu_required", 1)
        memory = getattr(op, "memory_required", "1GB")
        gpu = getattr(op, "gpu_required", 0)

        assert cpu == 4
        assert memory == "4GB"
        assert gpu == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
