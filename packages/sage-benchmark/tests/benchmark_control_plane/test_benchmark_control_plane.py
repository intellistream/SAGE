"""
Tests for benchmark_control_plane module.

This module tests the Control Plane benchmark components including:
- Configuration validation
- Workload generation
- Metrics collection
- Report generation
"""

from sage.benchmark.benchmark_control_plane.config import (
    ArrivalPattern,
    BenchmarkConfig,
    SchedulingPolicy,
    SLOConfig,
)
from sage.benchmark.benchmark_control_plane.metrics import MetricsCollector, RequestMetrics
from sage.benchmark.benchmark_control_plane.workload import Request, WorkloadGenerator


class TestBenchmarkConfig:
    """Tests for BenchmarkConfig class."""

    def test_default_config_creation(self):
        """Test that default configuration can be created."""
        config = BenchmarkConfig()
        assert config.control_plane_url == "http://localhost:8889"
        assert config.num_requests == 100
        assert config.request_rate == 10.0
        assert config.arrival_pattern == ArrivalPattern.POISSON

    def test_config_validation_success(self):
        """Test validation passes for valid config."""
        config = BenchmarkConfig(
            num_requests=100,
            request_rate=10.0,
            warmup_requests=10,
            model_distribution={"model-a": 0.5, "model-b": 0.5},
            priority_distribution={"HIGH": 0.3, "NORMAL": 0.5, "LOW": 0.2},
        )
        errors = config.validate()
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

    def test_config_validation_negative_requests(self):
        """Test validation fails for negative requests."""
        config = BenchmarkConfig(num_requests=-1)
        errors = config.validate()
        assert any("num_requests" in e for e in errors)

    def test_config_validation_zero_rate(self):
        """Test validation fails for zero request rate."""
        config = BenchmarkConfig(request_rate=0)
        errors = config.validate()
        assert any("request_rate" in e for e in errors)

    def test_config_validation_warmup_exceeds_requests(self):
        """Test validation fails when warmup exceeds total requests."""
        config = BenchmarkConfig(num_requests=10, warmup_requests=15)
        errors = config.validate()
        assert any("warmup" in e.lower() for e in errors)

    def test_config_validation_invalid_model_distribution(self):
        """Test validation fails for model distribution not summing to 1."""
        config = BenchmarkConfig(model_distribution={"model-a": 0.3, "model-b": 0.3})
        errors = config.validate()
        assert any("model_distribution" in e for e in errors)

    def test_config_validation_invalid_priority_distribution(self):
        """Test validation fails for priority distribution not summing to 1."""
        config = BenchmarkConfig(priority_distribution={"HIGH": 0.5, "LOW": 0.1})
        errors = config.validate()
        assert any("priority_distribution" in e for e in errors)

    def test_config_validation_invalid_policy(self):
        """Test validation fails for unknown policy."""
        config = BenchmarkConfig(policies=["fifo", "unknown_policy"])
        errors = config.validate()
        assert any("Unknown policy" in e for e in errors)

    def test_config_from_dict(self):
        """Test configuration can be created from dictionary."""
        data = {
            "control_plane_url": "http://test:8080",
            "num_requests": 500,
            "request_rate": 50.0,
            "policies": ["fifo", "priority"],
            "arrival_pattern": "uniform",
        }
        config = BenchmarkConfig.from_dict(data)
        assert config.control_plane_url == "http://test:8080"
        assert config.num_requests == 500
        assert config.request_rate == 50.0
        assert config.policies == ["fifo", "priority"]
        assert config.arrival_pattern == ArrivalPattern.UNIFORM

    def test_config_to_dict(self):
        """Test configuration can be serialized to dictionary."""
        config = BenchmarkConfig(
            control_plane_url="http://test:8080",
            num_requests=500,
        )
        data = config.to_dict()
        assert data["control_plane_url"] == "http://test:8080"
        assert data["num_requests"] == 500
        assert "policies" in data
        assert "arrival_pattern" in data

    def test_config_roundtrip(self):
        """Test config can be serialized and deserialized."""
        original = BenchmarkConfig(
            control_plane_url="http://example:8080",
            num_requests=1000,
            request_rate=100.0,
            policies=["aegaeon"],
        )
        data = original.to_dict()
        restored = BenchmarkConfig.from_dict(data)
        assert restored.control_plane_url == original.control_plane_url
        assert restored.num_requests == original.num_requests
        assert restored.request_rate == original.request_rate
        assert restored.policies == original.policies


class TestSLOConfig:
    """Tests for SLOConfig class."""

    def test_default_slo_config(self):
        """Test default SLO configuration values."""
        slo = SLOConfig()
        assert slo.high_priority_deadline_ms == 500
        assert slo.normal_priority_deadline_ms == 1000
        assert slo.low_priority_deadline_ms == 2000

    def test_get_deadline_for_priority(self):
        """Test getting deadline by priority level."""
        slo = SLOConfig(
            high_priority_deadline_ms=100,
            normal_priority_deadline_ms=500,
            low_priority_deadline_ms=1000,
        )
        assert slo.get_deadline_for_priority("HIGH") == 100
        assert slo.get_deadline_for_priority("NORMAL") == 500
        assert slo.get_deadline_for_priority("LOW") == 1000
        # Unknown priority should default to normal
        assert slo.get_deadline_for_priority("UNKNOWN") == 500


class TestSchedulingPolicy:
    """Tests for SchedulingPolicy enum."""

    def test_policy_values(self):
        """Test all policy values exist."""
        assert SchedulingPolicy.FIFO.value == "fifo"
        assert SchedulingPolicy.PRIORITY.value == "priority"
        assert SchedulingPolicy.SLO_AWARE.value == "slo_aware"
        assert SchedulingPolicy.ADAPTIVE.value == "adaptive"
        assert SchedulingPolicy.AEGAEON.value == "aegaeon"


class TestWorkloadGenerator:
    """Tests for WorkloadGenerator class."""

    def test_generator_creates_correct_count(self):
        """Test generator creates correct number of requests."""
        config = BenchmarkConfig(num_requests=50, request_rate=10.0)
        generator = WorkloadGenerator(config, seed=42)
        workload = generator.generate()
        assert len(workload) == 50

    def test_generator_reproducible_with_seed(self):
        """Test generator produces reproducible results with same seed."""
        config = BenchmarkConfig(num_requests=20)
        gen1 = WorkloadGenerator(config, seed=42)
        gen2 = WorkloadGenerator(config, seed=42)
        workload1 = gen1.generate()
        workload2 = gen2.generate()
        # Request IDs will differ (UUIDs), but prompts should be similar patterns
        assert len(workload1) == len(workload2)

    def test_generator_request_structure(self):
        """Test generated requests have correct structure."""
        config = BenchmarkConfig(num_requests=10)
        generator = WorkloadGenerator(config, seed=42)
        workload = generator.generate()

        for request in workload:
            assert isinstance(request, Request)
            assert request.request_id is not None
            assert request.model_name is not None
            assert request.prompt is not None
            assert request.max_tokens > 0
            assert request.priority in ["HIGH", "NORMAL", "LOW"]
            assert request.slo_deadline_ms > 0
            assert request.scheduled_arrival_time >= 0

    def test_generator_arrival_times_ordered(self):
        """Test arrival times are non-decreasing."""
        config = BenchmarkConfig(num_requests=20, arrival_pattern=ArrivalPattern.UNIFORM)
        generator = WorkloadGenerator(config, seed=42)
        workload = generator.generate()

        arrival_times = [r.scheduled_arrival_time for r in workload]
        for i in range(1, len(arrival_times)):
            assert arrival_times[i] >= arrival_times[i - 1]

    def test_generator_model_distribution(self):
        """Test model distribution is approximately correct."""
        config = BenchmarkConfig(
            num_requests=1000,
            model_distribution={"model-a": 0.7, "model-b": 0.3},
        )
        generator = WorkloadGenerator(config, seed=42)
        workload = generator.generate()

        model_counts = {}
        for request in workload:
            model_counts[request.model_name] = model_counts.get(request.model_name, 0) + 1

        # Check approximate distribution (within 10%)
        assert abs(model_counts.get("model-a", 0) / 1000 - 0.7) < 0.1
        assert abs(model_counts.get("model-b", 0) / 1000 - 0.3) < 0.1

    def test_generator_priority_distribution(self):
        """Test priority distribution is approximately correct."""
        config = BenchmarkConfig(
            num_requests=1000,
            priority_distribution={"HIGH": 0.2, "NORMAL": 0.5, "LOW": 0.3},
        )
        generator = WorkloadGenerator(config, seed=42)
        workload = generator.generate()

        priority_counts = {}
        for request in workload:
            priority_counts[request.priority] = priority_counts.get(request.priority, 0) + 1

        # Check approximate distribution (within 10%)
        assert abs(priority_counts.get("HIGH", 0) / 1000 - 0.2) < 0.1
        assert abs(priority_counts.get("NORMAL", 0) / 1000 - 0.5) < 0.1
        assert abs(priority_counts.get("LOW", 0) / 1000 - 0.3) < 0.1


class TestRequest:
    """Tests for Request dataclass."""

    def test_request_to_dict(self):
        """Test request serialization to dictionary."""
        request = Request(
            request_id="test-123",
            model_name="test-model",
            prompt="Hello, world!",
            max_tokens=100,
            priority="NORMAL",
            slo_deadline_ms=1000,
            scheduled_arrival_time=1.5,
        )
        data = request.to_dict()
        assert data["request_id"] == "test-123"
        assert data["model_name"] == "test-model"
        assert data["prompt"] == "Hello, world!"
        assert data["max_tokens"] == 100
        assert data["priority"] == "NORMAL"
        assert data["slo_deadline_ms"] == 1000
        assert data["scheduled_arrival_time"] == 1.5


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_empty_collector_returns_empty_metrics(self):
        """Test empty collector returns zero metrics."""
        collector = MetricsCollector()
        metrics = collector.compute_metrics()
        assert metrics.total_requests == 0
        assert metrics.completed_requests == 0

    def test_collector_counts_requests(self):
        """Test collector correctly counts requests."""
        collector = MetricsCollector()

        # Create mock results
        from sage.benchmark.benchmark_control_plane.client import RequestResult

        result1 = RequestResult(
            request_id="1",
            model_name="test",
            priority="NORMAL",
            slo_deadline_ms=1000,
            success=True,
            send_time=0.0,
            completion_time=0.5,
        )
        result2 = RequestResult(
            request_id="2",
            model_name="test",
            priority="HIGH",
            slo_deadline_ms=500,
            success=True,
            send_time=0.1,
            completion_time=0.4,
        )
        result3 = RequestResult(
            request_id="3",
            model_name="test",
            priority="LOW",
            slo_deadline_ms=2000,
            success=False,
            error="Test error",
            send_time=0.2,
            completion_time=0.3,
        )

        collector.add_results([result1, result2, result3])
        metrics = collector.compute_metrics()

        assert metrics.total_requests == 3
        assert metrics.completed_requests == 2
        assert metrics.failed_requests == 1

    def test_collector_computes_slo_compliance(self):
        """Test SLO compliance calculation."""
        from sage.benchmark.benchmark_control_plane.client import RequestResult

        collector = MetricsCollector()

        # Request that meets SLO (500ms deadline, 400ms actual)
        result1 = RequestResult(
            request_id="1",
            model_name="test",
            priority="NORMAL",
            slo_deadline_ms=500,
            success=True,
            send_time=0.0,
            completion_time=0.4,  # 400ms
        )
        # Request that misses SLO (500ms deadline, 600ms actual)
        result2 = RequestResult(
            request_id="2",
            model_name="test",
            priority="NORMAL",
            slo_deadline_ms=500,
            success=True,
            send_time=0.0,
            completion_time=0.6,  # 600ms
        )

        collector.add_results([result1, result2])
        metrics = collector.compute_metrics()

        assert metrics.slo_compliance_rate == 0.5  # 1 of 2 met SLO

    def test_collector_clear(self):
        """Test clearing collector resets state."""
        from sage.benchmark.benchmark_control_plane.client import RequestResult

        collector = MetricsCollector()
        result = RequestResult(
            request_id="1",
            model_name="test",
            priority="NORMAL",
            slo_deadline_ms=1000,
            success=True,
        )
        collector.add_result(result)
        assert len(collector._results) == 1

        collector.clear()
        assert len(collector._results) == 0


class TestRequestResult:
    """Tests for RequestResult dataclass."""

    def test_e2e_latency_calculation(self):
        """Test E2E latency is calculated correctly."""
        from sage.benchmark.benchmark_control_plane.client import RequestResult

        result = RequestResult(
            request_id="1",
            model_name="test",
            priority="NORMAL",
            slo_deadline_ms=1000,
            send_time=1.0,
            completion_time=1.5,
        )
        assert result.e2e_latency_ms == 500.0  # (1.5 - 1.0) * 1000

    def test_ttft_calculation(self):
        """Test TTFT is calculated correctly."""
        from sage.benchmark.benchmark_control_plane.client import RequestResult

        result = RequestResult(
            request_id="1",
            model_name="test",
            priority="NORMAL",
            slo_deadline_ms=1000,
            send_time=1.0,
            first_token_time=1.1,
        )
        # Use approximate comparison for floating point
        assert abs(result.ttft_ms - 100.0) < 0.01  # (1.1 - 1.0) * 1000

    def test_met_slo_true(self):
        """Test met_slo is True when deadline is met."""
        from sage.benchmark.benchmark_control_plane.client import RequestResult

        result = RequestResult(
            request_id="1",
            model_name="test",
            priority="NORMAL",
            slo_deadline_ms=1000,
            success=True,
            send_time=0.0,
            completion_time=0.5,  # 500ms < 1000ms deadline
        )
        assert result.met_slo is True

    def test_met_slo_false(self):
        """Test met_slo is False when deadline is missed."""
        from sage.benchmark.benchmark_control_plane.client import RequestResult

        result = RequestResult(
            request_id="1",
            model_name="test",
            priority="NORMAL",
            slo_deadline_ms=500,
            success=True,
            send_time=0.0,
            completion_time=1.0,  # 1000ms > 500ms deadline
        )
        assert result.met_slo is False

    def test_result_to_dict(self):
        """Test result serialization to dictionary."""
        from sage.benchmark.benchmark_control_plane.client import RequestResult

        result = RequestResult(
            request_id="test-123",
            model_name="test-model",
            priority="HIGH",
            slo_deadline_ms=500,
            success=True,
            send_time=1.0,
            first_token_time=1.05,
            completion_time=1.2,
        )
        data = result.to_dict()
        assert data["request_id"] == "test-123"
        assert data["model_name"] == "test-model"
        assert data["priority"] == "HIGH"
        assert data["success"] is True
        assert "e2e_latency_ms" in data
        assert "ttft_ms" in data
        assert "met_slo" in data


class TestRequestMetrics:
    """Tests for RequestMetrics dataclass."""

    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = RequestMetrics()
        assert metrics.total_requests == 0
        assert metrics.throughput_rps == 0.0
        assert metrics.slo_compliance_rate == 0.0

    def test_metrics_to_dict(self):
        """Test metrics serialization to dictionary."""
        metrics = RequestMetrics(
            total_requests=100,
            completed_requests=95,
            failed_requests=5,
            throughput_rps=50.0,
            e2e_latency_avg_ms=200.0,
            slo_compliance_rate=0.9,
        )
        data = metrics.to_dict()
        assert data["request_counts"]["total"] == 100
        assert data["request_counts"]["completed"] == 95
        assert data["throughput"]["requests_per_second"] == 50.0
        assert data["slo"]["compliance_rate"] == 0.9
