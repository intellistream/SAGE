# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Unit tests for the llm_scheduler module.

Tests cover:
- LLMBenchmarkConfig
- LLMRequest and LLMWorkloadGenerator
- LLMRequestMetrics and LLMMetricsCollector
- LLMBenchmarkRunner (initialization and configuration)
- LLMBenchmarkReporter
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sage.benchmark.benchmark_control_plane.common import ArrivalPattern
from sage.benchmark.benchmark_control_plane.llm_scheduler import (
    LLMBenchmarkConfig,
    LLMBenchmarkReporter,
    LLMBenchmarkResult,
    LLMBenchmarkRunner,
    LLMMetricsCollector,
    LLMPolicyResult,
    LLMRequest,
    LLMRequestMetrics,
    LLMRequestResult,
    LLMWorkloadGenerator,
)


# =============================================================================
# Tests for LLMBenchmarkConfig
# =============================================================================
class TestLLMBenchmarkConfig:
    """Tests for LLMBenchmarkConfig class."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = LLMBenchmarkConfig()
        assert config.num_requests == 100
        assert config.request_rate == 10.0
        assert config.arrival_pattern == ArrivalPattern.POISSON
        # model_distribution is a dict, not model_name
        assert isinstance(config.model_distribution, dict)

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = LLMBenchmarkConfig(
            control_plane_url="http://localhost:9000",
            num_requests=500,
            request_rate=50.0,
            model_distribution={"custom-model": 1.0},
            prompt_len_range=(100, 1000),
            output_len_range=(50, 500),
        )
        assert config.control_plane_url == "http://localhost:9000"
        assert config.num_requests == 500
        assert config.request_rate == 50.0
        assert config.model_distribution == {"custom-model": 1.0}
        assert config.prompt_len_range == (100, 1000)
        assert config.output_len_range == (50, 500)

    def test_validate_success(self) -> None:
        """Test validation passes for valid config."""
        config = LLMBenchmarkConfig(
            num_requests=100,
            request_rate=10.0,
            warmup_requests=10,
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_invalid_prompt_range(self) -> None:
        """Test validation fails for invalid prompt length range."""
        config = LLMBenchmarkConfig(
            prompt_len_range=(1000, 100),  # min > max
        )
        errors = config.validate()
        assert any("prompt_len_range" in e for e in errors)

    def test_validate_invalid_output_range(self) -> None:
        """Test validation fails for invalid output length range."""
        config = LLMBenchmarkConfig(
            output_len_range=(500, 50),  # min > max
        )
        errors = config.validate()
        assert any("output_len_range" in e for e in errors)

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        config = LLMBenchmarkConfig(
            num_requests=200,
            model_distribution={"test-model": 1.0},
        )
        d = config.to_dict()
        assert d["num_requests"] == 200
        assert d["model_distribution"] == {"test-model": 1.0}

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        d = {
            "control_plane_url": "http://test:8000",
            "num_requests": 300,
            "request_rate": 30.0,
        }
        config = LLMBenchmarkConfig.from_dict(d)
        assert config.control_plane_url == "http://test:8000"
        assert config.num_requests == 300
        assert config.request_rate == 30.0


# =============================================================================
# Tests for LLMRequest
# =============================================================================
class TestLLMRequest:
    """Tests for LLMRequest dataclass."""

    def test_default_request(self) -> None:
        """Test request creation with all required fields."""
        request = LLMRequest(
            request_id="test-1",
            model_name="test-model",
            prompt="Hello, world.",
            max_tokens=100,
            priority="NORMAL",
            slo_deadline_ms=1000,
            scheduled_arrival_time=0.0,
        )
        assert request.request_id == "test-1"
        assert request.model_name == "test-model"
        assert request.prompt == "Hello, world."
        assert request.priority == "NORMAL"
        assert request.max_tokens == 100
        assert request.scheduled_arrival_time == 0.0

    def test_request_to_dict(self) -> None:
        """Test request serialization."""
        request = LLMRequest(
            request_id="test-1",
            model_name="test-model",
            prompt="Test prompt",
            max_tokens=100,
            priority="HIGH",
            slo_deadline_ms=500,
            scheduled_arrival_time=1.5,
        )
        d = request.to_dict()
        assert d["request_id"] == "test-1"
        assert d["prompt"] == "Test prompt"
        assert d["priority"] == "HIGH"
        assert d["model_name"] == "test-model"
        assert d["scheduled_arrival_time"] == 1.5


# =============================================================================
# Tests for LLMWorkloadGenerator
# =============================================================================
class TestLLMWorkloadGenerator:
    """Tests for LLMWorkloadGenerator class."""

    def test_generator_initialization(self) -> None:
        """Test generator initialization."""
        config = LLMBenchmarkConfig(
            num_requests=100,
            request_rate=10.0,
        )
        generator = LLMWorkloadGenerator(config)
        assert generator.config == config

    def test_generate_requests(self) -> None:
        """Test generating requests."""
        config = LLMBenchmarkConfig(
            num_requests=10,
            request_rate=10.0,
        )
        generator = LLMWorkloadGenerator(config)
        requests = generator.generate()

        assert len(requests) == 10
        for req in requests:
            assert req.request_id  # UUID generated
            assert req.priority in ["HIGH", "NORMAL", "LOW"]
            assert len(req.prompt) > 0
            assert req.scheduled_arrival_time >= 0

    def test_generate_model_distribution(self) -> None:
        """Test generating requests with model distribution."""
        config = LLMBenchmarkConfig(
            num_requests=100,
            model_distribution={"model-a": 0.7, "model-b": 0.3},
        )
        generator = LLMWorkloadGenerator(config, seed=42)
        requests = generator.generate()

        # Check that models are distributed
        model_counts = {}
        for req in requests:
            model_counts[req.model_name] = model_counts.get(req.model_name, 0) + 1

        assert "model-a" in model_counts
        assert "model-b" in model_counts

    def test_generate_inter_arrival_times_poisson(self) -> None:
        """Test inter-arrival times for Poisson pattern."""
        config = LLMBenchmarkConfig(
            num_requests=100,
            request_rate=10.0,
            arrival_pattern=ArrivalPattern.POISSON,
        )
        generator = LLMWorkloadGenerator(config)
        requests = generator.generate()

        # Check that scheduled times are generated
        scheduled_times = [r.scheduled_arrival_time for r in requests]
        assert all(t >= 0 for t in scheduled_times)
        # Times should be monotonically increasing
        assert scheduled_times == sorted(scheduled_times)

    def test_generate_inter_arrival_times_uniform(self) -> None:
        """Test inter-arrival times for uniform pattern."""
        config = LLMBenchmarkConfig(
            num_requests=10,
            request_rate=10.0,
            arrival_pattern=ArrivalPattern.UNIFORM,
        )
        generator = LLMWorkloadGenerator(config)
        requests = generator.generate()

        # For uniform, inter-arrival should be ~0.1s (1/10 req/s)
        scheduled_times = [r.scheduled_arrival_time for r in requests]
        intervals = [
            scheduled_times[i + 1] - scheduled_times[i] for i in range(len(scheduled_times) - 1)
        ]
        avg_interval = sum(intervals) / len(intervals)
        assert abs(avg_interval - 0.1) < 0.01


# =============================================================================
# Tests for LLMRequestResult
# =============================================================================
class TestLLMRequestResult:
    """Tests for LLMRequestResult dataclass."""

    def test_default_result(self) -> None:
        """Test default result creation."""
        result = LLMRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=1000,
        )
        assert result.request_id == "test-1"
        assert result.success is False
        assert result.output_token_count == 0

    def test_ttft_calculation(self) -> None:
        """Test time-to-first-token calculation."""
        result = LLMRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=1000,
        )
        result.send_time = 1000.0
        result.first_token_time = 1000.1  # 100ms TTFT
        # Allow for small floating point errors
        ttft = result.ttft_ms
        assert ttft is not None
        assert abs(ttft - 100.0) < 0.001

    def test_ttft_no_first_token(self) -> None:
        """Test TTFT returns None when no first token time."""
        result = LLMRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=1000,
        )
        result.send_time = 1000.0
        assert result.ttft_ms is None

    def test_inter_token_latencies(self) -> None:
        """Test inter-token latencies storage."""
        result = LLMRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=1000,
        )
        result.inter_token_latencies = [10.0, 15.0, 20.0]
        # TBT is computed at the collector level, not on LLMRequestResult
        assert result.inter_token_latencies == [10.0, 15.0, 20.0]
        assert len(result.inter_token_latencies) == 3

    def test_result_to_dict(self) -> None:
        """Test result serialization."""
        result = LLMRequestResult(
            request_id="test-1",
            priority="NORMAL",
            slo_deadline_ms=1000,
        )
        result.send_time = 1000.0
        result.completion_time = 1000.5
        result.success = True
        result.output_token_count = 50

        d = result.to_dict()
        assert d["request_id"] == "test-1"
        assert d["success"] is True
        assert d["output_token_count"] == 50


# =============================================================================
# Tests for LLMRequestMetrics
# =============================================================================
class TestLLMRequestMetrics:
    """Tests for LLMRequestMetrics dataclass."""

    def test_default_metrics(self) -> None:
        """Test default metrics creation."""
        metrics = LLMRequestMetrics()
        assert metrics.total_requests == 0
        assert metrics.throughput_rps == 0.0
        assert metrics.token_throughput_tps == 0.0
        assert metrics.ttft_avg_ms == 0.0

    def test_metrics_to_dict(self) -> None:
        """Test metrics serialization."""
        metrics = LLMRequestMetrics()
        metrics.total_requests = 100
        metrics.throughput_rps = 10.0
        metrics.token_throughput_tps = 500.0
        metrics.ttft_avg_ms = 50.0
        metrics.ttft_p99_ms = 150.0

        d = metrics.to_dict()
        assert d["request_counts"]["total"] == 100
        assert d["throughput"]["requests_per_second"] == 10.0
        assert d["throughput"]["tokens_per_second"] == 500.0
        assert d["ttft_ms"]["avg"] == 50.0
        assert d["ttft_ms"]["p99"] == 150.0


# =============================================================================
# Tests for LLMMetricsCollector
# =============================================================================
class TestLLMMetricsCollector:
    """Tests for LLMMetricsCollector class."""

    def _create_result(
        self,
        request_id: str,
        success: bool = True,
        send_time: float = 1000.0,
        latency_s: float = 0.5,
        ttft_s: float = 0.1,
        output_tokens: int = 50,
    ) -> LLMRequestResult:
        """Create a test result."""
        result = LLMRequestResult(
            request_id=request_id,
            priority="NORMAL",
            slo_deadline_ms=1000,
        )
        result.send_time = send_time
        if success:
            result.completion_time = send_time + latency_s
            result.first_token_time = send_time + ttft_s
            result.inter_token_latencies = [10.0, 12.0, 15.0]
            result.output_token_count = output_tokens
            result.success = True
        else:
            result.success = False
            result.error = "Test error"
        return result

    def test_empty_collector(self) -> None:
        """Test empty collector returns empty metrics."""
        collector = LLMMetricsCollector()
        metrics = collector.compute_metrics()
        assert metrics.total_requests == 0

    def test_collector_counts_requests(self) -> None:
        """Test collector counts requests."""
        collector = LLMMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)

        for i in range(10):
            collector.add_result(self._create_result(f"req-{i}"))

        metrics = collector.compute_metrics()
        assert metrics.total_requests == 10
        assert metrics.completed_requests == 10

    def test_collector_computes_throughput(self) -> None:
        """Test collector computes throughput."""
        collector = LLMMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)  # 1 second

        for i in range(10):
            collector.add_result(self._create_result(f"req-{i}", output_tokens=50))

        metrics = collector.compute_metrics()
        assert metrics.throughput_rps == 10.0
        assert metrics.token_throughput_tps == 500.0  # 10 * 50 tokens

    def test_collector_computes_ttft(self) -> None:
        """Test collector computes TTFT metrics."""
        collector = LLMMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)

        for i in range(5):
            collector.add_result(self._create_result(f"req-{i}", ttft_s=0.1))

        metrics = collector.compute_metrics()
        assert abs(metrics.ttft_avg_ms - 100.0) < 0.01

    def test_collector_computes_slo_compliance(self) -> None:
        """Test collector computes SLO compliance."""
        collector = LLMMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)

        # 500ms latency, 1000ms deadline -> met
        collector.add_result(self._create_result("req-0", latency_s=0.5))
        # 1500ms latency, 1000ms deadline -> not met
        collector.add_result(self._create_result("req-1", latency_s=1.5))

        metrics = collector.compute_metrics()
        assert metrics.slo_compliance_rate == 0.5

    def test_collector_handles_failures(self) -> None:
        """Test collector handles failed requests."""
        collector = LLMMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)

        collector.add_result(self._create_result("req-0", success=True))
        collector.add_result(self._create_result("req-1", success=False))

        metrics = collector.compute_metrics()
        assert metrics.total_requests == 2
        assert metrics.completed_requests == 1
        assert metrics.failed_requests == 1


# =============================================================================
# Tests for LLMBenchmarkRunner
# =============================================================================
class TestLLMBenchmarkRunner:
    """Tests for LLMBenchmarkRunner class."""

    def test_runner_initialization(self) -> None:
        """Test runner initialization."""
        config = LLMBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=100,
        )
        runner = LLMBenchmarkRunner(config)

        assert runner.config == config
        assert runner.verbose is True

    def test_runner_initialization_custom(self) -> None:
        """Test runner initialization with custom options."""
        config = LLMBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=100,
        )
        runner = LLMBenchmarkRunner(
            config,
            verbose=False,
            enable_gpu_monitoring=False,
        )

        assert runner.verbose is False
        assert runner.enable_gpu_monitoring is False

    def test_runner_validates_config(self) -> None:
        """Test runner validates configuration."""
        config = LLMBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=-1,  # Invalid
        )
        runner = LLMBenchmarkRunner(config)

        with pytest.raises(ValueError, match="Invalid configuration"):
            import asyncio

            asyncio.run(runner.run())


# =============================================================================
# Tests for LLMBenchmarkReporter
# =============================================================================
class TestLLMBenchmarkReporter:
    """Tests for LLMBenchmarkReporter class."""

    def _create_test_result(self) -> LLMBenchmarkResult:
        """Create a test benchmark result."""
        config = LLMBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=100,
        )

        metrics = LLMRequestMetrics()
        metrics.total_requests = 100
        metrics.completed_requests = 98
        metrics.throughput_rps = 50.0
        metrics.token_throughput_tps = 2500.0
        metrics.e2e_latency_avg_ms = 100.0
        metrics.e2e_latency_p99_ms = 500.0
        metrics.slo_compliance_rate = 0.95
        metrics.ttft_avg_ms = 50.0
        metrics.ttft_p99_ms = 150.0

        policy_result = LLMPolicyResult(
            policy="fifo",
            metrics=metrics,
            raw_results=[],
        )

        result = LLMBenchmarkResult(config=config.to_dict())
        result.policy_results["fifo"] = policy_result
        result.best_throughput = "fifo"
        result.best_slo_compliance = "fifo"

        return result

    def test_reporter_initialization(self) -> None:
        """Test reporter initialization."""
        result = self._create_test_result()
        reporter = LLMBenchmarkReporter(result)
        assert reporter.result == result

    def test_reporter_print_summary(self, capsys: pytest.CaptureFixture) -> None:
        """Test reporter print_summary output."""
        result = self._create_test_result()
        reporter = LLMBenchmarkReporter(result)
        reporter.print_summary()

        captured = capsys.readouterr()
        # Check that output contains key information
        assert "Benchmark Report" in captured.out
        assert "fifo" in captured.out

    def test_reporter_save_json(self) -> None:
        """Test reporter save_json functionality."""
        result = self._create_test_result()
        reporter = LLMBenchmarkReporter(result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.json"
            saved_path = reporter.save_json(output_path)

            assert saved_path == output_path
            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "policy_results" in data
            assert "fifo" in data["policy_results"]

    def test_reporter_save_csv(self) -> None:
        """Test reporter save_csv functionality."""
        result = self._create_test_result()
        reporter = LLMBenchmarkReporter(result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.csv"
            saved_path = reporter.save_csv(output_path)

            assert saved_path == output_path
            assert output_path.exists()

            with open(output_path) as f:
                content = f.read()

            assert "policy" in content
            assert "fifo" in content


# =============================================================================
# Tests for LLMPolicyResult and LLMBenchmarkResult
# =============================================================================
class TestLLMPolicyResult:
    """Tests for LLMPolicyResult dataclass."""

    def test_policy_result_to_dict(self) -> None:
        """Test policy result to_dict."""
        metrics = LLMRequestMetrics()
        metrics.total_requests = 100

        result = LLMPolicyResult(
            policy="test_policy",
            metrics=metrics,
            start_time=1000.0,
            end_time=1010.0,
        )

        result_dict = result.to_dict()
        assert result_dict["policy"] == "test_policy"
        assert result_dict["start_time"] == 1000.0
        assert result_dict["end_time"] == 1010.0


class TestLLMBenchmarkResult:
    """Tests for LLMBenchmarkResult dataclass."""

    def test_benchmark_result_to_dict(self) -> None:
        """Test benchmark result to_dict."""
        result = LLMBenchmarkResult(config={"test": "config"})
        result.best_throughput = "fifo"
        result.best_slo_compliance = "priority"

        result_dict = result.to_dict()
        assert result_dict["config"] == {"test": "config"}
        assert result_dict["summary"]["best_throughput"] == "fifo"
        assert result_dict["summary"]["best_slo_compliance"] == "priority"
