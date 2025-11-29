# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Unit tests for the hybrid_scheduler module (Task 3B components).

Tests cover:
- HybridRequestMetrics
- HybridMetricsCollector
- HybridBenchmarkRunner (initialization and configuration)
- HybridBenchmarkReporter
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sage.benchmark.benchmark_control_plane.hybrid_scheduler import (
    HybridBenchmarkConfig,
    HybridBenchmarkReporter,
    HybridBenchmarkResult,
    HybridBenchmarkRunner,
    HybridMetricsCollector,
    HybridPolicyResult,
    HybridRequestMetrics,
    HybridRequestResult,
    RequestType,
)


class TestHybridRequestMetrics:
    """Tests for HybridRequestMetrics dataclass."""

    def test_default_metrics(self) -> None:
        """Test default metrics creation."""
        metrics = HybridRequestMetrics()
        assert metrics.total_requests == 0
        assert metrics.llm_total_requests == 0
        assert metrics.embedding_total_requests == 0
        assert metrics.throughput_rps == 0.0
        assert metrics.llm_throughput_rps == 0.0
        assert metrics.embedding_throughput_rps == 0.0

    def test_metrics_to_dict(self) -> None:
        """Test metrics to_dict includes all sections."""
        metrics = HybridRequestMetrics()
        metrics.total_requests = 100
        metrics.llm_total_requests = 70
        metrics.embedding_total_requests = 30
        metrics.throughput_rps = 10.0
        metrics.llm_throughput_rps = 7.0
        metrics.embedding_throughput_rps = 3.0
        metrics.llm_ratio_actual = 0.7
        metrics.embedding_ratio_actual = 0.3

        result = metrics.to_dict()

        # Check base sections exist
        assert "request_counts" in result
        assert "throughput" in result
        assert "e2e_latency_ms" in result
        assert "slo" in result

        # Check hybrid-specific sections
        assert "llm" in result
        assert "embedding" in result
        assert "mixed_workload" in result

        # Check LLM metrics
        assert result["llm"]["request_counts"]["total"] == 70
        assert result["llm"]["throughput"]["requests_per_second"] == 7.0

        # Check Embedding metrics
        assert result["embedding"]["request_counts"]["total"] == 30
        assert result["embedding"]["throughput"]["requests_per_second"] == 3.0

        # Check mixed workload metrics
        assert result["mixed_workload"]["llm_ratio_actual"] == 0.7
        assert result["mixed_workload"]["embedding_ratio_actual"] == 0.3


class TestHybridMetricsCollector:
    """Tests for HybridMetricsCollector."""

    def _create_llm_result(
        self,
        request_id: str,
        success: bool = True,
        send_time: float = 1000.0,
        latency_s: float = 0.5,
        ttft_s: float = 0.1,
    ) -> HybridRequestResult:
        """Create a test LLM result."""
        result = HybridRequestResult(
            request_id=request_id,
            request_type=RequestType.LLM_CHAT,
            priority="NORMAL",
            slo_deadline_ms=1000,
            model_name="test-model",
        )
        result.send_time = send_time
        if success:
            result.completion_time = send_time + latency_s
            result.first_token_time = send_time + ttft_s
            result.inter_token_latencies = [10.0, 12.0, 15.0]
            result.output_token_count = 50
            result.success = True
        else:
            result.success = False
            result.error = "Test error"
        return result

    def _create_embedding_result(
        self,
        request_id: str,
        success: bool = True,
        send_time: float = 1000.0,
        latency_s: float = 0.1,
        batch_size: int = 8,
    ) -> HybridRequestResult:
        """Create a test embedding result."""
        result = HybridRequestResult(
            request_id=request_id,
            request_type=RequestType.EMBEDDING,
            priority="NORMAL",
            slo_deadline_ms=200,
            embedding_model="test-embed-model",
        )
        result.send_time = send_time
        if success:
            result.completion_time = send_time + latency_s
            result.batch_size = batch_size
            result.total_texts_embedded = batch_size
            result.success = True
        else:
            result.success = False
            result.error = "Test error"
        return result

    def test_empty_collector(self) -> None:
        """Test empty collector returns empty metrics."""
        collector = HybridMetricsCollector()
        metrics = collector.compute_metrics()
        assert metrics.total_requests == 0
        assert metrics.llm_total_requests == 0
        assert metrics.embedding_total_requests == 0

    def test_collector_counts_requests(self) -> None:
        """Test collector counts requests by type."""
        collector = HybridMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)

        # Add 7 LLM and 3 embedding results
        for i in range(7):
            collector.add_result(self._create_llm_result(f"llm-{i}"))
        for i in range(3):
            collector.add_result(self._create_embedding_result(f"embed-{i}"))

        metrics = collector.compute_metrics()

        assert metrics.total_requests == 10
        assert metrics.llm_total_requests == 7
        assert metrics.embedding_total_requests == 3
        assert metrics.llm_ratio_actual == 0.7
        assert metrics.embedding_ratio_actual == 0.3

    def test_collector_computes_throughput(self) -> None:
        """Test collector computes throughput metrics."""
        collector = HybridMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)  # 1 second

        for i in range(10):
            collector.add_result(self._create_llm_result(f"llm-{i}"))
        for i in range(10):
            collector.add_result(self._create_embedding_result(f"embed-{i}"))

        metrics = collector.compute_metrics()

        assert metrics.throughput_rps == 20.0
        assert metrics.llm_throughput_rps == 10.0
        assert metrics.embedding_throughput_rps == 10.0

    def test_collector_computes_llm_ttft(self) -> None:
        """Test collector computes LLM TTFT metrics."""
        collector = HybridMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)

        # Add results with 100ms TTFT
        for i in range(5):
            collector.add_result(self._create_llm_result(f"llm-{i}", ttft_s=0.1))

        metrics = collector.compute_metrics()

        assert abs(metrics.llm_ttft_avg_ms - 100.0) < 0.01
        assert abs(metrics.llm_ttft_p50_ms - 100.0) < 0.01
        assert abs(metrics.llm_ttft_p95_ms - 100.0) < 0.01

    def test_collector_computes_embedding_batch_efficiency(self) -> None:
        """Test collector computes embedding batch efficiency."""
        collector = HybridMetricsCollector(max_batch_size=32)
        collector.set_time_range(1000.0, 1001.0)

        # Add results with batch size 8 (25% efficiency)
        for i in range(4):
            collector.add_result(self._create_embedding_result(f"embed-{i}", batch_size=8))

        metrics = collector.compute_metrics()

        assert metrics.embedding_avg_batch_size == 8.0
        assert metrics.embedding_batch_efficiency == 0.25

    def test_collector_computes_slo_compliance(self) -> None:
        """Test collector computes SLO compliance by type."""
        collector = HybridMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)

        # LLM: 500ms latency, 1000ms deadline -> met
        collector.add_result(self._create_llm_result("llm-0", latency_s=0.5))
        # LLM: 1500ms latency, 1000ms deadline -> not met
        collector.add_result(self._create_llm_result("llm-1", latency_s=1.5))

        # Embedding: 100ms latency, 200ms deadline -> met
        collector.add_result(self._create_embedding_result("embed-0", latency_s=0.1))
        # Embedding: 300ms latency, 200ms deadline -> not met
        collector.add_result(self._create_embedding_result("embed-1", latency_s=0.3))

        metrics = collector.compute_metrics()

        assert metrics.llm_slo_compliance_rate == 0.5
        assert metrics.embedding_slo_compliance_rate == 0.5
        assert metrics.slo_compliance_rate == 0.5

    def test_collector_handles_failures(self) -> None:
        """Test collector handles failed requests."""
        collector = HybridMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)

        collector.add_result(self._create_llm_result("llm-0", success=True))
        collector.add_result(self._create_llm_result("llm-1", success=False))

        metrics = collector.compute_metrics()

        assert metrics.total_requests == 2
        assert metrics.completed_requests == 1
        assert metrics.failed_requests == 1
        assert metrics.llm_total_requests == 2
        assert metrics.llm_completed_requests == 1

    def test_collector_clear(self) -> None:
        """Test collector clear functionality."""
        collector = HybridMetricsCollector()
        collector.add_result(self._create_llm_result("llm-0"))
        collector.add_result(self._create_embedding_result("embed-0"))

        collector.clear()
        metrics = collector.compute_metrics()

        assert metrics.total_requests == 0

    def test_get_summary_string(self) -> None:
        """Test get_summary_string output."""
        collector = HybridMetricsCollector()
        collector.set_time_range(1000.0, 1001.0)
        collector.add_result(self._create_llm_result("llm-0"))
        collector.add_result(self._create_embedding_result("embed-0"))

        summary = collector.get_summary_string()

        assert "Hybrid Benchmark Metrics Summary" in summary
        assert "LLM Performance" in summary
        assert "Embedding Performance" in summary


class TestHybridBenchmarkRunner:
    """Tests for HybridBenchmarkRunner."""

    def test_runner_initialization(self) -> None:
        """Test runner initialization with config."""
        config = HybridBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=100,
            llm_ratio=0.7,
            embedding_ratio=0.3,
        )
        runner = HybridBenchmarkRunner(config)

        assert runner.config == config
        assert runner.verbose is True
        assert runner.enable_gpu_monitoring is True

    def test_runner_initialization_custom_options(self) -> None:
        """Test runner initialization with custom options."""
        config = HybridBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=100,
        )
        runner = HybridBenchmarkRunner(
            config,
            verbose=False,
            enable_gpu_monitoring=False,
            gpu_monitor_interval=1.0,
        )

        assert runner.verbose is False
        assert runner.enable_gpu_monitoring is False
        assert runner.gpu_monitor_interval == 1.0

    def test_runner_validates_config(self) -> None:
        """Test runner validates configuration."""
        config = HybridBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=-1,  # Invalid
        )
        runner = HybridBenchmarkRunner(config)

        with pytest.raises(ValueError) as exc_info:
            import asyncio

            asyncio.run(runner.run())

        assert "Invalid configuration" in str(exc_info.value)


class TestHybridBenchmarkReporter:
    """Tests for HybridBenchmarkReporter."""

    def _create_test_result(self) -> HybridBenchmarkResult:
        """Create a test benchmark result."""
        config = HybridBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=100,
            llm_ratio=0.7,
            embedding_ratio=0.3,
        )

        metrics = HybridRequestMetrics()
        metrics.total_requests = 100
        metrics.completed_requests = 98
        metrics.llm_total_requests = 70
        metrics.embedding_total_requests = 30
        metrics.throughput_rps = 50.0
        metrics.llm_throughput_rps = 35.0
        metrics.embedding_throughput_rps = 15.0
        metrics.e2e_latency_avg_ms = 100.0
        metrics.e2e_latency_p99_ms = 500.0
        metrics.slo_compliance_rate = 0.95
        metrics.llm_slo_compliance_rate = 0.94
        metrics.embedding_slo_compliance_rate = 0.97
        metrics.llm_ttft_avg_ms = 50.0
        metrics.llm_ttft_p99_ms = 150.0
        metrics.embedding_throughput_texts_ps = 120.0
        metrics.embedding_batch_efficiency = 0.5
        metrics.embedding_avg_batch_size = 8.0
        metrics.llm_ratio_actual = 0.7
        metrics.embedding_ratio_actual = 0.3

        policy_result = HybridPolicyResult(
            policy="fifo",
            metrics=metrics,
            raw_results=[],
        )

        result = HybridBenchmarkResult(config=config.to_dict())
        result.policy_results["fifo"] = policy_result
        result.best_throughput = "fifo"
        result.best_llm_throughput = "fifo"
        result.best_embedding_throughput = "fifo"
        result.best_slo_compliance = "fifo"

        return result

    def test_reporter_initialization(self) -> None:
        """Test reporter initialization."""
        result = self._create_test_result()
        reporter = HybridBenchmarkReporter(result)
        assert reporter.result == result

    def test_reporter_print_summary(self, capsys: pytest.CaptureFixture) -> None:
        """Test reporter print_summary output."""
        result = self._create_test_result()
        reporter = HybridBenchmarkReporter(result)
        reporter.print_summary()

        captured = capsys.readouterr()
        assert "sageLLM Hybrid Scheduling Policy Benchmark Report" in captured.out
        assert "Overall Performance" in captured.out
        assert "LLM Performance" in captured.out
        assert "Embedding Performance" in captured.out
        assert "Best Performers" in captured.out

    def test_reporter_save_json(self) -> None:
        """Test reporter save_json functionality."""
        result = self._create_test_result()
        reporter = HybridBenchmarkReporter(result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.json"
            saved_path = reporter.save_json(output_path)

            assert saved_path == output_path
            assert output_path.exists()

            with open(output_path) as f:
                data = json.load(f)

            assert "timestamp" in data
            assert "version" in data
            assert "benchmark_type" in data
            assert data["benchmark_type"] == "hybrid"
            assert "policy_results" in data
            assert "fifo" in data["policy_results"]

    def test_reporter_save_csv(self) -> None:
        """Test reporter save_csv functionality."""
        result = self._create_test_result()
        reporter = HybridBenchmarkReporter(result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report.csv"
            saved_path = reporter.save_csv(output_path)

            assert saved_path == output_path
            assert output_path.exists()

            with open(output_path) as f:
                content = f.read()

            # Check headers
            assert "policy" in content
            assert "throughput_rps" in content
            assert "llm_throughput_rps" in content
            assert "embedding_throughput_rps" in content

            # Check data
            assert "fifo" in content

    def test_reporter_get_comparison_table(self) -> None:
        """Test reporter get_comparison_table functionality."""
        result = self._create_test_result()
        reporter = HybridBenchmarkReporter(result)

        comparison = reporter.get_comparison_table()

        assert "fifo" in comparison
        assert "overall" in comparison["fifo"]
        assert "llm" in comparison["fifo"]
        assert "embedding" in comparison["fifo"]
        assert "gpu" in comparison["fifo"]

        assert comparison["fifo"]["overall"]["throughput_rps"] == 50.0
        assert comparison["fifo"]["llm"]["throughput_rps"] == 35.0
        assert comparison["fifo"]["embedding"]["throughput_rps"] == 15.0


class TestHybridPolicyResult:
    """Tests for HybridPolicyResult dataclass."""

    def test_policy_result_to_dict(self) -> None:
        """Test policy result to_dict."""
        metrics = HybridRequestMetrics()
        metrics.total_requests = 100

        result = HybridPolicyResult(
            policy="test_policy",
            metrics=metrics,
            start_time=1000.0,
            end_time=1010.0,
        )

        result_dict = result.to_dict()

        assert result_dict["policy"] == "test_policy"
        assert result_dict["start_time"] == 1000.0
        assert result_dict["end_time"] == 1010.0
        assert "metrics" in result_dict


class TestHybridBenchmarkResult:
    """Tests for HybridBenchmarkResult dataclass."""

    def test_benchmark_result_to_dict(self) -> None:
        """Test benchmark result to_dict."""
        result = HybridBenchmarkResult(config={"test": "config"})
        result.best_throughput = "fifo"
        result.best_llm_throughput = "priority"
        result.best_embedding_throughput = "fifo"

        result_dict = result.to_dict()

        assert result_dict["config"] == {"test": "config"}
        assert result_dict["summary"]["best_throughput"] == "fifo"
        assert result_dict["summary"]["best_llm_throughput"] == "priority"
        assert result_dict["summary"]["best_embedding_throughput"] == "fifo"
