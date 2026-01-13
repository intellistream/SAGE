"""
Tests for agent runtime module.
"""

import pytest
from sage_libs.sage_agentic.agents.runtime import (
    BenchmarkAdapter,
    Orchestrator,
    PlannerConfig,
    RuntimeConfig,
    SelectorConfig,
    TelemetryCollector,
    TelemetryConfig,
    TimingConfig,
)


class TestRuntimeConfig:
    """Test runtime configuration models."""

    def test_default_config(self):
        """Test creating config with defaults."""
        config = RuntimeConfig()

        assert config.max_turns == 8
        assert config.timeout == 30.0
        assert config.selector.name == "keyword"
        assert config.planner.name == "llm"
        assert config.timing.name == "rule_based"
        assert config.telemetry.enabled is True

    def test_custom_config(self):
        """Test creating config with custom values."""
        config = RuntimeConfig(
            selector=SelectorConfig(name="embedding", top_k=10),
            planner=PlannerConfig(name="hierarchical", max_steps=15),
            timing=TimingConfig(name="llm_based", threshold=0.7),
            max_turns=12,
        )

        assert config.selector.name == "embedding"
        assert config.selector.top_k == 10
        assert config.planner.name == "hierarchical"
        assert config.planner.max_steps == 15
        assert config.timing.name == "llm_based"
        assert config.timing.threshold == 0.7
        assert config.max_turns == 12

    def test_config_dict_conversion(self):
        """Test config can be created from dict."""
        config_dict = {
            "selector": {"name": "bm25", "top_k": 3},
            "planner": {"name": "cot", "max_steps": 8},
            "max_turns": 10,
        }

        config = RuntimeConfig(**config_dict)

        assert config.selector.name == "bm25"
        assert config.selector.top_k == 3
        assert config.planner.name == "cot"
        assert config.planner.max_steps == 8


class TestTelemetry:
    """Test telemetry collection."""

    def test_telemetry_collection(self):
        """Test basic telemetry collection."""
        config = TelemetryConfig(enabled=True)
        collector = TelemetryCollector(config)

        # Start and finish operation
        record = collector.start("tool_selection", metadata={"top_k": 5})
        assert record.operation == "tool_selection"
        assert record.metadata["top_k"] == 5

        collector.finish(record, success=True)
        assert record.success is True
        assert record.duration is not None
        assert record.duration >= 0

    def test_telemetry_metrics(self):
        """Test metrics aggregation."""
        config = TelemetryConfig(enabled=True)
        collector = TelemetryCollector(config)

        # Simulate multiple operations
        for i in range(5):
            record = collector.start("tool_selection")
            collector.finish(record, success=i < 4)  # 1 failure

        metrics = collector.get_metrics()

        assert metrics["total_operations"] == 5
        assert metrics["successful_operations"] == 4
        assert metrics["failed_operations"] == 1
        assert metrics["success_rate"] == 0.8
        assert "avg_latency" in metrics

    def test_telemetry_disabled(self):
        """Test telemetry when disabled."""
        config = TelemetryConfig(enabled=False)
        collector = TelemetryCollector(config)

        record = collector.start("tool_selection")
        collector.finish(record)

        # Should not collect when disabled
        assert len(collector.records) == 0


class MockSelector:
    """Mock tool selector for testing."""

    def select(self, query, top_k=5):
        """Return mock selections."""
        return [{"tool_id": f"tool_{i}", "score": 1.0 - i * 0.1} for i in range(top_k)]


class MockPlanner:
    """Mock planner for testing."""

    def plan(self, request):
        """Return mock plan."""
        return {"steps": [{"action": "step1"}, {"action": "step2"}]}


class MockTimingDecider:
    """Mock timing decider for testing."""

    def decide(self, message):
        """Return mock decision."""
        return {"decision": "call", "confidence": 0.9}


class TestOrchestrator:
    """Test orchestrator functionality."""

    def test_orchestrator_initialization(self):
        """Test creating orchestrator."""
        config = RuntimeConfig()
        orchestrator = Orchestrator(config=config)

        assert orchestrator.config == config
        assert orchestrator.telemetry is not None

    def test_tool_selection_execution(self):
        """Test tool selection through orchestrator."""
        config = RuntimeConfig()
        selector = MockSelector()
        orchestrator = Orchestrator(config=config, selector=selector)

        result = orchestrator.execute_tool_selection("test query", top_k=3)

        assert len(result) == 3
        assert result[0]["tool_id"] == "tool_0"

        # Check telemetry
        metrics = orchestrator.get_telemetry_metrics()
        assert metrics["total_operations"] == 1
        assert "tool_selection" in metrics["by_operation"]

    def test_planning_execution(self):
        """Test planning through orchestrator."""
        config = RuntimeConfig()
        planner = MockPlanner()
        orchestrator = Orchestrator(config=config, planner=planner)

        result = orchestrator.execute_planning("test request")

        assert "steps" in result
        assert len(result["steps"]) == 2

        # Check telemetry
        metrics = orchestrator.get_telemetry_metrics()
        assert metrics["total_operations"] == 1

    def test_timing_execution(self):
        """Test timing decision through orchestrator."""
        config = RuntimeConfig()
        timing_decider = MockTimingDecider()
        orchestrator = Orchestrator(config=config, timing_decider=timing_decider)

        result = orchestrator.execute_timing_decision("test message")

        assert result["decision"] == "call"
        assert result["confidence"] == 0.9

    def test_orchestrator_without_component_raises(self):
        """Test orchestrator raises error when component missing."""
        config = RuntimeConfig()
        orchestrator = Orchestrator(config=config)

        with pytest.raises(RuntimeError, match="Tool selector not configured"):
            orchestrator.execute_tool_selection("test")

        with pytest.raises(RuntimeError, match="Planner not configured"):
            orchestrator.execute_planning("test")

        with pytest.raises(RuntimeError, match="Timing decider not configured"):
            orchestrator.execute_timing_decision("test")


class TestBenchmarkAdapter:
    """Test benchmark adapter functionality."""

    def test_adapter_initialization(self):
        """Test creating adapter."""
        config = RuntimeConfig()
        orchestrator = Orchestrator(config=config)
        adapter = BenchmarkAdapter(orchestrator)

        assert adapter.orchestrator == orchestrator

    def test_adapter_tool_selection(self):
        """Test tool selection through adapter."""
        config = RuntimeConfig()
        selector = MockSelector()
        orchestrator = Orchestrator(config=config, selector=selector)
        adapter = BenchmarkAdapter(orchestrator)

        result = adapter.run_tool_selection("test query", top_k=5)

        assert len(result) == 5
        assert all("tool_id" in r for r in result)

    def test_adapter_planning(self):
        """Test planning through adapter."""
        config = RuntimeConfig()
        planner = MockPlanner()
        orchestrator = Orchestrator(config=config, planner=planner)
        adapter = BenchmarkAdapter(orchestrator)

        result = adapter.run_planning("test request")

        assert "steps" in result

    def test_adapter_timing(self):
        """Test timing through adapter."""
        config = RuntimeConfig()
        timing_decider = MockTimingDecider()
        orchestrator = Orchestrator(config=config, timing_decider=timing_decider)
        adapter = BenchmarkAdapter(orchestrator)

        result = adapter.run_timing("test message")

        assert result["decision"] == "call"

    def test_adapter_get_metrics(self):
        """Test getting metrics from adapter."""
        config = RuntimeConfig()
        selector = MockSelector()
        orchestrator = Orchestrator(config=config, selector=selector)
        adapter = BenchmarkAdapter(orchestrator)

        # Execute some operations
        adapter.run_tool_selection("query1")
        adapter.run_tool_selection("query2")

        metrics = adapter.get_metrics()

        assert metrics["total_operations"] == 2
        assert metrics["successful_operations"] == 2

    def test_adapter_reset(self):
        """Test resetting adapter state."""
        config = RuntimeConfig()
        selector = MockSelector()
        orchestrator = Orchestrator(config=config, selector=selector)
        adapter = BenchmarkAdapter(orchestrator)

        # Execute operations
        adapter.run_tool_selection("query1")
        assert adapter.get_metrics()["total_operations"] == 1

        # Reset
        adapter.reset()
        assert adapter.get_metrics() == {}
