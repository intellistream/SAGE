"""
Schema migration test suite - Issue #1437

Tests that verify:
1. ResourceSpec / PlacementStrategy / PlacementSchema correctness
2. PlacementDecision.to_schema() → schema-only output (no runtime types)
3. All scheduler impls produce schema-clean PlacementDecision
4. Round-trip serialization (to_dict / from_dict)
5. parse_memory / format_memory utilities
"""

from __future__ import annotations

import pytest

from sage.kernel.scheduler.decision import PlacementDecision
from sage.kernel.scheduler.schema import (
    PlacementSchema,
    PlacementStrategy,
    ResourceSpec,
    format_memory,
    parse_memory,
)

# ============================================================================
# ResourceSpec tests
# ============================================================================


class TestResourceSpec:
    def test_default_is_empty(self):
        spec = ResourceSpec()
        assert spec.is_empty()
        assert spec.cpu is None
        assert spec.gpu is None
        assert spec.memory_bytes is None

    def test_non_empty_with_cpu(self):
        spec = ResourceSpec(cpu=2.0)
        assert not spec.is_empty()

    def test_non_empty_with_gpu(self):
        assert not ResourceSpec(gpu=1.0).is_empty()

    def test_non_empty_with_memory(self):
        assert not ResourceSpec(memory_bytes=1024).is_empty()

    def test_non_empty_with_custom_resources(self):
        assert not ResourceSpec(custom_resources={"tpu": 1.0}).is_empty()

    def test_validate_negative_cpu_raises(self):
        with pytest.raises(ValueError, match="cpu"):
            ResourceSpec(cpu=-1).validate()

    def test_validate_negative_gpu_raises(self):
        with pytest.raises(ValueError, match="gpu"):
            ResourceSpec(gpu=-0.5).validate()

    def test_validate_negative_memory_raises(self):
        with pytest.raises(ValueError, match="memory"):
            ResourceSpec(memory_bytes=-100).validate()

    def test_to_dict_round_trip(self):
        spec = ResourceSpec(
            cpu=4.0,
            gpu=1.0,
            memory_bytes=8 * 1024**3,
            custom_resources={"fpga": 2.0},
            affinity_tags={"zone": "us-west"},
        )
        d = spec.to_dict()
        restored = ResourceSpec.from_dict(d)
        assert restored.cpu == spec.cpu
        assert restored.gpu == spec.gpu
        assert restored.memory_bytes == spec.memory_bytes
        assert restored.custom_resources == spec.custom_resources
        assert restored.affinity_tags == spec.affinity_tags

    def test_from_dict_empty_produces_empty(self):
        spec = ResourceSpec.from_dict({})
        assert spec.is_empty()

    def test_equality(self):
        a = ResourceSpec(cpu=2.0, gpu=1.0)
        b = ResourceSpec(cpu=2.0, gpu=1.0)
        assert a == b


# ============================================================================
# PlacementStrategy tests
# ============================================================================


class TestPlacementStrategy:
    def test_string_enum_values(self):
        assert PlacementStrategy.DEFAULT == "default"
        assert PlacementStrategy.SPREAD == "spread"
        assert PlacementStrategy.PACK == "pack"
        assert PlacementStrategy.AFFINITY == "affinity"
        assert PlacementStrategy.ANTI_AFFINITY == "anti_affinity"

    def test_can_construct_from_value(self):
        assert PlacementStrategy("pack") is PlacementStrategy.PACK
        assert PlacementStrategy("spread") is PlacementStrategy.SPREAD

    def test_no_ray_strings(self):
        """PlacementStrategy values must not contain Ray-specific naming."""
        for member in PlacementStrategy:
            assert "ray" not in member.value.lower(), (
                f"PlacementStrategy.{member.name} contains 'ray': '{member.value}'"
            )


# ============================================================================
# parse_memory / format_memory tests
# ============================================================================


class TestParseMemory:
    def test_integer_passthrough(self):
        assert parse_memory(1024) == 1024
        assert parse_memory(0) == 0

    def test_gigabytes(self):
        assert parse_memory("8GB") == 8 * 1024**3
        assert parse_memory("1.5GB") == int(1.5 * 1024**3)

    def test_megabytes(self):
        assert parse_memory("512MB") == 512 * 1024**2

    def test_kilobytes(self):
        assert parse_memory("1024KB") == 1024 * 1024

    def test_round_trip_with_format(self):
        original = 8 * 1024**3
        formatted = format_memory(original)
        restored = parse_memory(formatted)
        assert abs(restored - original) / original < 0.01  # within 1%

    def test_invalid_string_raises_value_error(self):
        """Invalid strings must raise ValueError (fail-fast, no silent fallback)."""
        with pytest.raises(ValueError, match="Cannot parse memory"):
            parse_memory("not_a_number")


# ============================================================================
# PlacementSchema tests
# ============================================================================


class TestPlacementSchema:
    def test_default_construction(self):
        schema = PlacementSchema()
        assert schema.strategy == PlacementStrategy.DEFAULT
        assert schema.resource.is_empty()
        assert schema.delay_seconds == 0.0
        assert schema.target_node_hint is None

    def test_to_dict_round_trip(self):
        schema = PlacementSchema(
            resource=ResourceSpec(cpu=4, gpu=1),
            strategy=PlacementStrategy.SPREAD,
            target_node_hint="node-42",
            delay_seconds=1.5,
            priority=5,
            affinity_task_ids=["task-1"],
            anti_affinity_task_ids=["task-2"],
            reason="test schema",
        )
        d = schema.to_dict()
        restored = PlacementSchema.from_dict(d)
        assert restored.strategy == schema.strategy
        assert restored.resource.cpu == schema.resource.cpu
        assert restored.resource.gpu == schema.resource.gpu
        assert restored.target_node_hint == schema.target_node_hint
        assert restored.delay_seconds == schema.delay_seconds
        assert restored.priority == schema.priority
        assert restored.affinity_task_ids == schema.affinity_task_ids
        assert restored.anti_affinity_task_ids == schema.anti_affinity_task_ids

    def test_strategy_in_dict_is_string(self):
        """Schema dict must contain plain strings, not enum objects."""
        schema = PlacementSchema(strategy=PlacementStrategy.PACK)
        d = schema.to_dict()
        assert isinstance(d["strategy"], str)
        assert d["strategy"] == "pack"

    def test_no_runtime_types_in_dict(self):
        """Schema dict must not contain any Ray / Flownet internal types."""
        schema = PlacementSchema(
            resource=ResourceSpec(cpu=2, gpu=1, memory_bytes=parse_memory("4GB")),
            strategy=PlacementStrategy.SPREAD,
        )
        d = schema.to_dict()
        _assert_no_runtime_types(d)


# ============================================================================
# PlacementDecision.to_schema() tests
# ============================================================================


class TestPlacementDecisionToSchema:
    def test_to_schema_returns_placement_schema(self):
        decision = PlacementDecision(
            target_node="node-1",
            resource=ResourceSpec(cpu=4, gpu=1),
            placement_strategy=PlacementStrategy.SPREAD,
            reason="Test",
        )
        schema = decision.to_schema()
        assert isinstance(schema, PlacementSchema)

    def test_to_schema_preserves_resource(self):
        spec = ResourceSpec(cpu=4, gpu=1, memory_bytes=parse_memory("8GB"))
        decision = PlacementDecision(resource=spec)
        schema = decision.to_schema()
        assert schema.resource.cpu == 4
        assert schema.resource.gpu == 1
        assert schema.resource.memory_bytes == parse_memory("8GB")

    def test_to_schema_preserves_strategy(self):
        decision = PlacementDecision(placement_strategy=PlacementStrategy.PACK)
        schema = decision.to_schema()
        assert schema.strategy == PlacementStrategy.PACK

    def test_to_schema_no_runtime_types(self):
        """to_schema() output must not leak any Ray/Flownet internal types."""
        decision = PlacementDecision(
            resource=ResourceSpec(cpu=2, gpu=1),
            placement_strategy=PlacementStrategy.SPREAD,
        )
        schema = decision.to_schema()
        d = schema.to_dict()
        _assert_no_runtime_types(d)

    def test_to_schema_from_immediate_default(self):
        decision = PlacementDecision.immediate_default(reason="quick")
        schema = decision.to_schema()
        assert schema.strategy == PlacementStrategy.DEFAULT
        assert schema.resource.is_empty()

    def test_to_schema_from_with_resources(self):
        decision = PlacementDecision.with_resources(cpu=4, gpu=1, memory="8GB")
        schema = decision.to_schema()
        assert schema.resource.cpu == 4
        assert schema.resource.gpu == 1
        assert schema.resource.memory_bytes == parse_memory("8GB")


# ============================================================================
# Scheduler impl: schema-clean output tests
# ============================================================================


class TestSchedulerSchemaCleanOutput:
    """All scheduler impls must produce schema-clean PlacementDecision (no runtime types)."""

    def _make_mock_task(self, cpu=1, gpu=0, memory="512MB"):
        from unittest.mock import Mock

        task_node = Mock()
        task_node.name = "test_task"
        task_node.priority = 5  # numeric, needed by PriorityScheduler
        task_node.transformation = Mock()
        task_node.transformation.cpu_required = cpu
        task_node.transformation.gpu_required = gpu
        task_node.transformation.memory_required = memory
        task_node.transformation.custom_resources = {}
        task_node.task_factory = Mock()
        task_node.task_factory.remote = False
        return task_node

    def test_fifo_scheduler_output_is_schema_clean(self):
        from sage.kernel.scheduler.impl import FIFOScheduler

        scheduler = FIFOScheduler(platform="local")
        decision = scheduler.make_decision(self._make_mock_task())
        _assert_decision_is_schema_clean(decision)

    def test_load_aware_scheduler_output_is_schema_clean(self):
        from sage.kernel.scheduler.impl import LoadAwareScheduler

        scheduler = LoadAwareScheduler()
        decision = scheduler.make_decision(self._make_mock_task(cpu=4, gpu=1))
        _assert_decision_is_schema_clean(decision)

    def test_priority_scheduler_output_is_schema_clean(self):
        from sage.kernel.scheduler.impl.priority_scheduler import PriorityScheduler

        scheduler = PriorityScheduler()
        decision = scheduler.make_decision(self._make_mock_task())
        _assert_decision_is_schema_clean(decision)

    def test_round_robin_scheduler_output_is_schema_clean(self):
        from sage.kernel.scheduler.impl.round_robin_scheduler import RoundRobinScheduler

        scheduler = RoundRobinScheduler()
        decision = scheduler.make_decision(self._make_mock_task())
        _assert_decision_is_schema_clean(decision)

    def test_random_scheduler_output_is_schema_clean(self):
        from sage.kernel.scheduler.impl.random_scheduler import RandomScheduler

        scheduler = RandomScheduler()
        decision = scheduler.make_decision(self._make_mock_task())
        _assert_decision_is_schema_clean(decision)


# ============================================================================
# PlacementDecision round-trip serialization
# ============================================================================


class TestPlacementDecisionSerialization:
    def test_to_dict_from_dict_round_trip(self):
        decision = PlacementDecision(
            target_node="node-7",
            resource=ResourceSpec(cpu=8, gpu=2, memory_bytes=parse_memory("16GB")),
            placement_strategy=PlacementStrategy.SPREAD,
            delay=0.5,
            immediate=False,
            affinity_tasks=["t1", "t2"],
            anti_affinity_tasks=["t3"],
            reason="full round-trip test",
            priority=3,
        )
        d = decision.to_dict()
        restored = PlacementDecision.from_dict(d)

        assert restored.target_node == decision.target_node
        assert restored.resource.cpu == decision.resource.cpu
        assert restored.resource.gpu == decision.resource.gpu
        assert restored.resource.memory_bytes == decision.resource.memory_bytes
        assert restored.placement_strategy == decision.placement_strategy
        assert restored.delay == decision.delay
        assert restored.immediate == decision.immediate
        assert restored.affinity_tasks == decision.affinity_tasks
        assert restored.anti_affinity_tasks == decision.anti_affinity_tasks
        assert restored.reason == decision.reason
        assert restored.priority == decision.priority

    def test_dict_strategy_value_is_string(self):
        decision = PlacementDecision(placement_strategy=PlacementStrategy.PACK)
        d = decision.to_dict()
        assert isinstance(d["placement_strategy"], str)
        assert d["placement_strategy"] == "pack"

    def test_from_dict_accepting_string_strategy(self):
        data = {
            "target_node": None,
            "resource": {"cpu": 2},
            "placement_strategy": "spread",
            "reason": "string strategy",
        }
        decision = PlacementDecision.from_dict(data)
        assert decision.placement_strategy == PlacementStrategy.SPREAD


# ============================================================================
# Helper assertions
# ============================================================================


_RAY_MARKERS = ("ray", "ActorHandle", "ObjectRef", "RemoteFunction")
_FLOWNET_INTERNAL = ("FlowTask", "ActorMethodRef", "TransformationFrame")


def _assert_no_runtime_types(obj, _path="root"):
    """Recursively assert no Ray/Flownet internal type names appear in a dict."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_runtime_types(v, f"{_path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _assert_no_runtime_types(item, f"{_path}[{i}]")
    elif isinstance(obj, str):
        lower = obj.lower()
        for marker in _RAY_MARKERS:
            assert marker.lower() not in lower or marker == "reason", (
                f"Runtime type marker '{marker}' found at {_path}: {obj!r}"
            )


def _assert_decision_is_schema_clean(decision: PlacementDecision):
    """Assert a PlacementDecision uses typed schema and no runtime internals."""
    # 1. resource field must be ResourceSpec
    assert isinstance(decision.resource, ResourceSpec), (
        f"Expected ResourceSpec, got {type(decision.resource)}"
    )

    # 2. placement_strategy must be PlacementStrategy enum
    assert isinstance(decision.placement_strategy, PlacementStrategy), (
        f"Expected PlacementStrategy, got {type(decision.placement_strategy)} "
        f"= {decision.placement_strategy!r}"
    )

    # 3. to_schema() must not raise
    schema = decision.to_schema()
    assert isinstance(schema, PlacementSchema)

    # 4. Schema dict must not contain runtime type markers
    _assert_no_runtime_types(schema.to_dict())
