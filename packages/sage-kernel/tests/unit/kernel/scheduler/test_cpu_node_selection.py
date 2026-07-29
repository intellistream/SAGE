"""
Test CPU Node Selection and Resource Allocation

Tests for CPU-only node support in SAGE:
- CPU node selection via NodeSelector
- Resource requirements (CPU, memory, no GPU)
- Scheduling strategies for CPU nodes
- Node filtering and ranking
- ResourceProvider abstraction (LocalSnapshotProvider, FlownetRuntimeProvider)
"""

from unittest.mock import MagicMock

import pytest

from sage.kernel.scheduler.decision import PlacementDecision
from sage.kernel.scheduler.node_selector import NodeResources, NodeSelector
from sage.kernel.scheduler.resource_provider import (
    FlownetRuntimeProvider,
    LocalSnapshotProvider,
    ResourceProvider,
)
from sage.kernel.scheduler.schema import PlacementStrategy, ResourceSpec, parse_memory


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

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _make_selector(nodes: list[NodeResources]) -> NodeSelector:
        """Build a NodeSelector backed by a fixed list of NodeResources."""

        class _FixedProvider(ResourceProvider):
            def get_nodes(self) -> list[NodeResources]:
                return nodes

        return NodeSelector(provider=_FixedProvider())

    # -----------------------------------------------------------------------
    # Tests
    # -----------------------------------------------------------------------

    def test_select_cpu_only_node(self):
        """Test selecting a CPU-only node (no GPU required)"""
        selector = self._make_selector(
            [
                NodeResources(
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
                NodeResources(
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
            ]
        )

        node_id = selector.select_best_node(cpu_required=4, gpu_required=0, strategy="balanced")

        assert node_id is not None
        assert node_id in ["cpu-node-1", "cpu-node-2"]
        # Should select cpu-node-2 (lower usage)
        assert node_id == "cpu-node-2"

    def test_reject_gpu_task_on_cpu_nodes(self):
        """Test that tasks requiring GPU are rejected on CPU-only nodes"""
        selector = self._make_selector(
            [
                NodeResources(
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
                ),
            ]
        )

        node_id = selector.select_best_node(cpu_required=2, gpu_required=1)
        assert node_id is None

    def test_balanced_strategy_selects_lowest_usage(self):
        """Test that balanced strategy selects the node with lowest usage"""
        selector = self._make_selector(
            [
                NodeResources(
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
                NodeResources(
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
                    cpu_usage=0.375,
                    gpu_usage=0.0,
                    memory_usage=0.375,
                ),
                NodeResources(
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
                    cpu_usage=0.75,
                    gpu_usage=0.0,
                    memory_usage=0.75,
                ),
            ]
        )

        node_id = selector.select_best_node(cpu_required=1, gpu_required=0, strategy="balanced")

        # Should select the node with lowest usage
        assert node_id == "cpu-node-low"

    def test_pack_strategy_selects_highest_usage(self):
        """Test that pack strategy selects the node with highest usage"""
        selector = self._make_selector(
            [
                NodeResources(
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
                NodeResources(
                    node_id="cpu-node-high",
                    hostname="cpu-high",
                    address="192.168.1.102",
                    total_cpu=8.0,
                    total_gpu=0.0,
                    total_memory=16 * 1024**3,
                    custom_resources={},
                    available_cpu=4.0,
                    available_gpu=0.0,
                    available_memory=8 * 1024**3,
                    cpu_usage=0.5,
                    gpu_usage=0.0,
                    memory_usage=0.5,
                ),
            ]
        )

        node_id = selector.select_best_node(cpu_required=2, gpu_required=0, strategy="pack")
        # Should select the node with higher usage (pack strategy)
        assert node_id == "cpu-node-high"

    def test_get_cluster_stats(self):
        """Test getting cluster statistics for CPU nodes"""
        selector = self._make_selector(
            [
                NodeResources(
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
                NodeResources(
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
            ]
        )

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
                    resource=ResourceSpec(cpu=2, gpu=0, memory_bytes=parse_memory("2GB")),
                    placement_strategy=PlacementStrategy.DEFAULT,
                    reason="CPU task assigned to CPU node",
                )

        scheduler = MockCPUScheduler()

        # Mock task node
        class MockTaskNode:
            name = "cpu_task"
            transformation = None

        decision = scheduler.make_decision(MockTaskNode())

        assert decision.target_node == "cpu-node-1"
        assert decision.resource.cpu == 2
        assert decision.resource.gpu == 0
        assert decision.placement_strategy == PlacementStrategy.DEFAULT

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


# ---------------------------------------------------------------------------
# New: ResourceProvider abstraction tests
# ---------------------------------------------------------------------------


class TestLocalSnapshotProvider:
    """Test LocalSnapshotProvider (default single-node resource backend)."""

    def test_returns_one_node(self):
        """LocalSnapshotProvider always returns exactly one (local) node."""
        provider = LocalSnapshotProvider(node_id="test-local", cache_ttl=0.0)
        nodes = provider.get_nodes()
        assert len(nodes) == 1
        assert nodes[0].node_id == "test-local"

    def test_node_has_positive_cpu(self):
        """Local snapshot reports at least 1 CPU."""
        provider = LocalSnapshotProvider(cache_ttl=0.0)
        nodes = provider.get_nodes()
        assert nodes[0].total_cpu >= 1.0

    def test_node_has_positive_memory(self):
        """Local snapshot reports positive total memory."""
        provider = LocalSnapshotProvider(cache_ttl=0.0)
        nodes = provider.get_nodes()
        assert nodes[0].total_memory > 0

    def test_available_not_exceeds_total(self):
        """available_cpu / available_memory must not exceed totals."""
        provider = LocalSnapshotProvider(cache_ttl=0.0)
        node = provider.get_nodes()[0]
        assert node.available_cpu <= node.total_cpu
        assert node.available_memory <= node.total_memory

    def test_usage_in_valid_range(self):
        """Usage fractions must be in [0, 1]."""
        provider = LocalSnapshotProvider(cache_ttl=0.0)
        node = provider.get_nodes()[0]
        assert 0.0 <= node.cpu_usage <= 1.0
        assert 0.0 <= node.gpu_usage <= 1.0
        assert 0.0 <= node.memory_usage <= 1.0

    def test_cache_returns_same_object_within_ttl(self):
        """Within TTL the same cached list is returned (no re-collection)."""
        provider = LocalSnapshotProvider(cache_ttl=60.0)
        result1 = provider.get_nodes()
        result2 = provider.get_nodes()
        assert result1 is result2

    def test_cache_refreshes_after_ttl(self):
        """After TTL expires, a new snapshot is collected."""
        provider = LocalSnapshotProvider(cache_ttl=0.0)
        result1 = provider.get_nodes()
        result2 = provider.get_nodes()
        # With ttl=0.0 every call creates a new list (different object)
        assert result1 is not result2

    def test_custom_address_and_hostname(self):
        """Provider respects custom address and hostname."""
        provider = LocalSnapshotProvider(
            node_id="n1", hostname="myhost", address="10.0.0.1", cache_ttl=0.0
        )
        node = provider.get_nodes()[0]
        assert node.node_id == "n1"
        assert node.hostname == "myhost"
        assert node.address == "10.0.0.1"

    def test_selector_with_local_provider_returns_local_node(self):
        """NodeSelector backed by LocalSnapshotProvider can select the local node."""
        selector = NodeSelector(provider=LocalSnapshotProvider(cache_ttl=0.0))
        node_id = selector.select_best_node(cpu_required=0, gpu_required=0, strategy="balanced")
        assert node_id == "local"

    def test_selector_set_provider(self):
        """NodeSelector.set_provider replaces the provider and invalidates cache."""

        class _NullProvider(ResourceProvider):
            def get_nodes(self) -> list[NodeResources]:
                return []

        selector = NodeSelector()
        selector.set_provider(_NullProvider())
        # After switching to a provider returning no nodes, selection returns None
        result = selector.select_best_node()
        assert result is None


class TestFlownetRuntimeProvider:
    """Test FlownetRuntimeProvider mapping from ClusterView nodes."""

    @staticmethod
    def _make_mock_cluster_view(nodes_data: list[dict]) -> MagicMock:
        """Build a minimal ClusterView mock from a list of node data dicts."""
        mock_nodes = []
        for nd in nodes_data:
            n = MagicMock()
            n.node_id = nd["node_id"]
            n.address = nd.get("address", "127.0.0.1")
            n.host_id = nd.get("host_id", nd["node_id"])
            n.resource_summary = nd.get("resource_summary", {})
            mock_nodes.append(n)

        cv = MagicMock()
        cv.list_nodes.return_value = mock_nodes
        cv.is_node_healthy.return_value = True
        return cv

    def test_maps_resource_summary_to_node_resources(self):
        """FlownetRuntimeProvider correctly maps resource_summary fields."""
        cv = self._make_mock_cluster_view(
            [
                {
                    "node_id": "fn-node-1",
                    "address": "10.0.0.1",
                    "resource_summary": {
                        "cpu_total": 8.0,
                        "cpu_available": 6.0,
                        "gpu_total": 2.0,
                        "gpu_available": 2.0,
                        "mem_total": 16 * 1024**3,
                        "mem_available": 12 * 1024**3,
                    },
                }
            ]
        )
        provider = FlownetRuntimeProvider(cv)
        nodes = provider.get_nodes()

        assert len(nodes) == 1
        node = nodes[0]
        assert node.node_id == "fn-node-1"
        assert node.total_cpu == 8.0
        assert node.available_cpu == 6.0
        assert node.total_gpu == 2.0
        assert node.total_memory == 16 * 1024**3
        assert node.available_memory == 12 * 1024**3

    def test_infers_usage_from_total_available(self):
        """Usage fraction is inferred when not explicitly provided."""
        cv = self._make_mock_cluster_view(
            [
                {
                    "node_id": "fn-node-2",
                    "resource_summary": {
                        "cpu_total": 10.0,
                        "cpu_available": 2.0,  # 80% used
                        "mem_total": 1000,
                        "mem_available": 250,  # 75% used
                    },
                }
            ]
        )
        provider = FlownetRuntimeProvider(cv)
        node = provider.get_nodes()[0]

        assert abs(node.cpu_usage - 0.8) < 1e-6
        assert abs(node.memory_usage - 0.75) < 1e-6

    def test_empty_resource_summary_produces_zeros(self):
        """Nodes with empty resource_summary default to all-zero resources."""
        cv = self._make_mock_cluster_view([{"node_id": "fn-empty", "resource_summary": {}}])
        provider = FlownetRuntimeProvider(cv)
        node = provider.get_nodes()[0]

        assert node.total_cpu == 0.0
        assert node.total_gpu == 0.0
        assert node.total_memory == 0

    def test_unhealthy_nodes_excluded_by_default(self):
        """Unhealthy nodes are filtered out when healthy_only=True (default)."""
        cv = self._make_mock_cluster_view(
            [
                {"node_id": "healthy-node", "resource_summary": {"cpu_total": 4.0}},
                {"node_id": "sick-node", "resource_summary": {"cpu_total": 8.0}},
            ]
        )
        # Make the second node unhealthy
        cv.is_node_healthy.side_effect = lambda nid: nid != "sick-node"

        provider = FlownetRuntimeProvider(cv, healthy_only=True)
        nodes = provider.get_nodes()

        assert len(nodes) == 1
        assert nodes[0].node_id == "healthy-node"

    def test_unhealthy_nodes_included_when_flag_off(self):
        """Unhealthy nodes are included when healthy_only=False."""
        cv = self._make_mock_cluster_view(
            [
                {"node_id": "healthy-node", "resource_summary": {}},
                {"node_id": "sick-node", "resource_summary": {}},
            ]
        )
        cv.is_node_healthy.side_effect = lambda nid: nid != "sick-node"

        provider = FlownetRuntimeProvider(cv, healthy_only=False)
        nodes = provider.get_nodes()
        assert len(nodes) == 2

    def test_custom_resources_extracted(self):
        """Non-standard resource_summary keys become custom_resources."""
        cv = self._make_mock_cluster_view(
            [
                {
                    "node_id": "fn-custom",
                    "resource_summary": {
                        "cpu_total": 4.0,
                        "max_tasks": 100.0,
                        "tpu_count": 2.0,
                    },
                }
            ]
        )
        provider = FlownetRuntimeProvider(cv)
        node = provider.get_nodes()[0]

        assert "max_tasks" in node.custom_resources
        assert node.custom_resources["max_tasks"] == 100.0
        assert "tpu_count" in node.custom_resources

    def test_selector_with_flownet_provider_multi_node(self):
        """NodeSelector backed by FlownetRuntimeProvider selects correctly across nodes."""
        cv = self._make_mock_cluster_view(
            [
                {
                    "node_id": "fn-low",
                    "resource_summary": {
                        "cpu_total": 8.0,
                        "cpu_available": 7.0,
                        "mem_total": 16 * 1024**3,
                        "mem_available": 14 * 1024**3,
                    },
                },
                {
                    "node_id": "fn-high",
                    "resource_summary": {
                        "cpu_total": 8.0,
                        "cpu_available": 2.0,
                        "mem_total": 16 * 1024**3,
                        "mem_available": 4 * 1024**3,
                    },
                },
            ]
        )
        cv.is_node_healthy.return_value = True

        provider = FlownetRuntimeProvider(cv)
        selector = NodeSelector(provider=provider)

        # balanced → picks node with lowest inferred cpu_usage (fn-low has ~12.5%)
        node_id = selector.select_best_node(cpu_required=1, strategy="balanced")
        assert node_id == "fn-low"

        # pack → picks node with highest inferred cpu_usage (fn-high has 75%)
        node_id = selector.select_best_node(cpu_required=1, strategy="pack")
        assert node_id == "fn-high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
