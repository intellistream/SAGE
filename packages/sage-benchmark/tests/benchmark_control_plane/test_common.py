# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project
"""
Tests for benchmark_control_plane common modules.

This module tests the shared base classes and utilities:
- Base configuration classes
- Base metrics classes
- GPU monitor
- Strategy adapter
"""

import time
from dataclasses import dataclass
from typing import Any

import pytest

from sage.benchmark.benchmark_control_plane.common import (
    ArrivalPattern,
    BaseBenchmarkConfig,
    BaseMetricsCollector,
    BaseRequestMetrics,
    BaseRequestResult,
    BaseSLOConfig,
    GPUMetrics,
    GPUMonitor,
    SchedulingPolicy,
    StrategyAdapter,
)


# =============================================================================
# Test concrete implementations for abstract base classes
# =============================================================================
@dataclass
class ConcreteBenchmarkConfig(BaseBenchmarkConfig):
    """Concrete implementation for testing."""

    test_field: str = "test"

    def validate(self) -> list[str]:
        """Validate configuration."""
        return self.validate_base()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = self.to_base_dict()
        d["test_field"] = self.test_field
        return d


class ConcreteMetricsCollector(BaseMetricsCollector):
    """Concrete implementation for testing."""

    def compute_metrics(self) -> BaseRequestMetrics:
        """Compute metrics."""
        return self._compute_base_metrics()


# =============================================================================
# Tests for ArrivalPattern
# =============================================================================
class TestArrivalPattern:
    """Tests for ArrivalPattern enum."""

    def test_pattern_values(self):
        """Test that all arrival patterns have correct values."""
        assert ArrivalPattern.UNIFORM.value == "uniform"
        assert ArrivalPattern.POISSON.value == "poisson"
        assert ArrivalPattern.BURST.value == "burst"


# =============================================================================
# Tests for SchedulingPolicy
# =============================================================================
class TestSchedulingPolicy:
    """Tests for SchedulingPolicy enum."""

    def test_policy_values(self):
        """Test that all policies have correct values."""
        assert SchedulingPolicy.FIFO.value == "fifo"
        assert SchedulingPolicy.PRIORITY.value == "priority"
        assert SchedulingPolicy.SLO_AWARE.value == "slo_aware"
        assert SchedulingPolicy.COST_OPTIMIZED.value == "cost_optimized"
        assert SchedulingPolicy.ADAPTIVE.value == "adaptive"
        assert SchedulingPolicy.AEGAEON.value == "aegaeon"
        assert SchedulingPolicy.HYBRID.value == "hybrid"


# =============================================================================
# Tests for BaseSLOConfig
# =============================================================================
class TestBaseSLOConfig:
    """Tests for BaseSLOConfig class."""

    def test_default_config(self):
        """Test default SLO configuration."""
        config = BaseSLOConfig()
        assert config.high_priority_deadline_ms == 500
        assert config.normal_priority_deadline_ms == 1000
        assert config.low_priority_deadline_ms == 2000

    def test_custom_config(self):
        """Test custom SLO configuration."""
        config = BaseSLOConfig(
            high_priority_deadline_ms=100,
            normal_priority_deadline_ms=200,
            low_priority_deadline_ms=500,
        )
        assert config.high_priority_deadline_ms == 100
        assert config.normal_priority_deadline_ms == 200
        assert config.low_priority_deadline_ms == 500

    def test_get_deadline_for_priority(self):
        """Test getting deadline for different priorities."""
        config = BaseSLOConfig()
        assert config.get_deadline_for_priority("HIGH") == 500
        assert config.get_deadline_for_priority("high") == 500
        assert config.get_deadline_for_priority("NORMAL") == 1000
        assert config.get_deadline_for_priority("LOW") == 2000
        assert config.get_deadline_for_priority("unknown") == 1000  # default

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = BaseSLOConfig(high_priority_deadline_ms=100)
        d = config.to_dict()
        assert d["high_priority_deadline_ms"] == 100
        assert d["normal_priority_deadline_ms"] == 1000
        assert d["low_priority_deadline_ms"] == 2000


# =============================================================================
# Tests for BaseBenchmarkConfig (using concrete subclass)
# =============================================================================
class TestBaseBenchmarkConfig:
    """Tests for BaseBenchmarkConfig class using concrete subclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = ConcreteBenchmarkConfig()
        assert config.num_requests == 100
        assert config.request_rate == 10.0
        assert config.arrival_pattern == ArrivalPattern.POISSON

    def test_validate_base_success(self):
        """Test validation passes for valid config."""
        config = ConcreteBenchmarkConfig(
            num_requests=100, request_rate=10.0, warmup_requests=10, timeout_seconds=30.0
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_base_negative_requests(self):
        """Test validation fails for negative requests."""
        config = ConcreteBenchmarkConfig(num_requests=-1)
        errors = config.validate()
        assert any("num_requests" in e for e in errors)

    def test_validate_base_zero_rate(self):
        """Test validation fails for zero request rate."""
        config = ConcreteBenchmarkConfig(request_rate=0)
        errors = config.validate()
        assert any("request_rate" in e for e in errors)

    def test_validate_base_warmup_exceeds_requests(self):
        """Test validation fails when warmup exceeds total requests."""
        config = ConcreteBenchmarkConfig(num_requests=10, warmup_requests=15)
        errors = config.validate()
        assert any("warmup" in e.lower() for e in errors)

    def test_to_base_dict(self):
        """Test serialization to dictionary."""
        config = ConcreteBenchmarkConfig(num_requests=500, request_rate=50.0)
        d = config.to_dict()
        assert d["num_requests"] == 500
        assert d["request_rate"] == 50.0


# =============================================================================
# Tests for BaseRequestResult
# =============================================================================
class TestBaseRequestResult:
    """Tests for BaseRequestResult class."""

    def test_default_result(self):
        """Test default request result."""
        result = BaseRequestResult(
            request_id="test-1", priority="NORMAL", slo_deadline_ms=1000
        )
        assert result.request_id == "test-1"
        assert result.priority == "NORMAL"
        assert result.success is False

    def test_e2e_latency(self):
        """Test end-to-end latency calculation."""
        result = BaseRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=1000,
            send_time=1000.0,
            completion_time=1000.5,
            success=True,
        )
        assert result.e2e_latency_ms == 500.0

    def test_e2e_latency_no_completion(self):
        """Test latency returns None when no completion time."""
        result = BaseRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=1000,
            send_time=1000.0,
        )
        assert result.e2e_latency_ms is None

    def test_met_slo_true(self):
        """Test SLO met when latency is within deadline."""
        result = BaseRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=1000,
            send_time=1000.0,
            completion_time=1000.4,  # 400ms latency
            success=True,
        )
        assert result.met_slo is True

    def test_met_slo_false(self):
        """Test SLO not met when latency exceeds deadline."""
        result = BaseRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=500,  # 500ms deadline
            send_time=1000.0,
            completion_time=1000.6,  # 600ms latency
            success=True,
        )
        assert result.met_slo is False

    def test_met_slo_no_completion(self):
        """Test SLO not met when no completion time."""
        result = BaseRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=500,
            send_time=1000.0,
        )
        assert result.met_slo is False


# =============================================================================
# Tests for BaseRequestMetrics
# =============================================================================
class TestBaseRequestMetrics:
    """Tests for BaseRequestMetrics class."""

    def test_default_metrics(self):
        """Test default metrics."""
        metrics = BaseRequestMetrics()
        assert metrics.total_requests == 0
        assert metrics.completed_requests == 0
        assert metrics.throughput_rps == 0.0

    def test_metrics_to_base_dict(self):
        """Test serialization to dictionary."""
        metrics = BaseRequestMetrics(
            total_requests=100, completed_requests=95, throughput_rps=10.0
        )
        d = metrics.to_base_dict()
        assert d["request_counts"]["total"] == 100
        assert d["request_counts"]["completed"] == 95
        assert d["throughput"]["requests_per_second"] == 10.0


# =============================================================================
# Tests for BaseMetricsCollector (using concrete subclass)
# =============================================================================
class TestBaseMetricsCollector:
    """Tests for BaseMetricsCollector class using concrete subclass."""

    def test_empty_collector(self):
        """Test empty collector has no results."""
        collector = ConcreteMetricsCollector()
        assert len(collector._results) == 0

    def test_add_result(self):
        """Test adding result to collector."""
        collector = ConcreteMetricsCollector()
        result = BaseRequestResult(
            request_id="test-1", priority="NORMAL", slo_deadline_ms=1000, success=True
        )
        collector.add_result(result)
        assert len(collector._results) == 1

    def test_clear(self):
        """Test clearing collector."""
        collector = ConcreteMetricsCollector()
        result = BaseRequestResult(
            request_id="test-1", priority="NORMAL", slo_deadline_ms=1000
        )
        collector.add_result(result)
        collector.clear()
        assert len(collector._results) == 0


# =============================================================================
# Tests for GPUMonitor
# =============================================================================
class TestGPUMonitor:
    """Tests for GPUMonitor class."""

    def test_init(self):
        """Test monitor initialization."""
        monitor = GPUMonitor()
        assert monitor.backend is not None

    def test_get_metrics(self):
        """Test getting current metrics."""
        monitor = GPUMonitor()
        metrics = monitor.get_metrics()
        assert isinstance(metrics, GPUMetrics)
        assert metrics.timestamp > 0

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = GPUMetrics(
            timestamp=time.time(),
            device_count=1,
            utilization_percent=[50.0],
            memory_used_mb=[1000.0],
            memory_total_mb=[8000.0],
            memory_percent=[12.5],
            temperature_celsius=[60.0],
            power_watts=[100.0],
        )
        d = metrics.to_dict()
        assert d["device_count"] == 1
        assert d["utilization_percent"] == [50.0]

    def test_metrics_avg_utilization(self):
        """Test average utilization calculation."""
        metrics = GPUMetrics(utilization_percent=[50.0, 60.0, 70.0])
        assert metrics.avg_utilization == 60.0


# =============================================================================
# Tests for StrategyAdapter
# =============================================================================
class TestStrategyAdapter:
    """Tests for StrategyAdapter class."""

    def test_list_strategies(self):
        """Test listing available strategies."""
        adapter = StrategyAdapter()
        strategies = adapter.list_strategies()
        assert "fifo" in strategies
        assert "priority" in strategies
        assert "slo_aware" in strategies
        assert "aegaeon" in strategies
        assert "hybrid" in strategies

    def test_get_strategy(self):
        """Test getting a strategy by name."""
        adapter = StrategyAdapter()
        strategy = adapter.get_strategy("fifo")
        assert strategy is not None

    def test_get_strategy_info(self):
        """Test getting strategy info."""
        adapter = StrategyAdapter()
        info = adapter.get_strategy_info("fifo")
        assert info is not None
        assert info.name == "fifo"

    def test_get_unknown_strategy(self):
        """Test getting unknown strategy raises error."""
        adapter = StrategyAdapter()
        with pytest.raises(ValueError, match="Unknown strategy"):
            adapter.get_strategy("unknown_strategy")

    def test_validate_policy_valid(self):
        """Test validating a valid policy."""
        errors = StrategyAdapter.validate_policy("fifo")
        assert len(errors) == 0
        errors = StrategyAdapter.validate_policy("aegaeon")
        assert len(errors) == 0

    def test_validate_policy_invalid(self):
        """Test validating an invalid policy."""
        errors = StrategyAdapter.validate_policy("unknown")
        assert len(errors) > 0
