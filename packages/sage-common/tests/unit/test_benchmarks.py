# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Tests for benchmarks module."""

import time

import pytest

from sage.common.components.sage_llm.sageLLM.benchmarks.metrics import (
    KVCacheMetric,
    LatencyMetric,
    MemoryMetric,
    MetricRegistry,
    MetricSummary,
    MetricType,
    MFUMetric,
    ThroughputMetric,
)
from sage.common.components.sage_llm.sageLLM.benchmarks.profiler import ExecutionTracer
from sage.common.components.sage_llm.sageLLM.benchmarks.reporters import (
    ConsoleReporter,
    JSONReporter,
)


class TestMetrics:
    """Test metric implementations."""

    def test_throughput_metric(self):
        """Test throughput measurement."""
        metric = ThroughputMetric()
        metric.start()

        # Simulate token generation
        time.sleep(0.01)
        metric.record(tokens=100, requests=1)
        time.sleep(0.01)
        metric.record(tokens=200, requests=1)

        result = metric.compute()

        assert result.total_tokens == 300
        assert result.total_requests == 2
        assert result.duration_s > 0
        assert result.tokens_per_second > 0
        assert result.requests_per_second > 0

    def test_latency_metric(self):
        """Test latency measurement."""
        metric = LatencyMetric()

        # Simulate prefill
        metric.record_prefill_start()
        time.sleep(0.01)
        metric.record_prefill_end()

        # Simulate decode tokens
        for _ in range(5):
            time.sleep(0.002)
            metric.record_decode_token()

        result = metric.compute()

        assert result.prefill_latency_ms > 0
        assert result.decode_latency_ms > 0
        assert result.ttft_ms > 0
        assert result.tpot_ms > 0
        assert result.e2e_latency_ms > 0
        assert result.e2e_latency_ms > result.prefill_latency_ms

    def test_memory_metric(self):
        """Test memory calculation."""
        metric = MemoryMetric()

        result = metric.compute(
            weight_bytes=7_000_000_000,  # 7 GB (not GiB)
            kv_cache_bytes=2_000_000_000,  # 2 GB
            activation_bytes=1_000_000_000,  # 1 GB
            total_memory_gb=80.0,
        )

        assert result.weight_memory_gb == pytest.approx(7.0, rel=0.01)
        assert result.kv_cache_memory_gb == pytest.approx(2.0, rel=0.01)
        assert result.activation_memory_gb == pytest.approx(1.0, rel=0.01)
        assert result.total_memory_gb == pytest.approx(10.0, rel=0.01)
        assert 0 < result.memory_utilization < 1

    def test_kv_cache_metric(self):
        """Test KV cache efficiency."""
        metric = KVCacheMetric()

        # Simulate cache operations
        metric.record_hit()
        metric.record_hit()
        metric.record_miss()

        metric.record_migration(bytes_moved=1024 * 1024)
        metric.record_reuse(reused_tokens=50, total_tokens=100)

        result = metric.compute()

        assert result.hit_rate == pytest.approx(2 / 3)
        assert result.migration_bytes == 1024 * 1024
        assert result.migration_count == 1
        assert result.reuse_ratio == 0.5
        assert result.avg_prefix_length == 50.0

    def test_mfu_metric(self):
        """Test MFU calculation."""
        metric = MFUMetric()

        result = metric.compute(
            num_tokens=1024,
            num_layers=32,
            hidden_size=4096,
            intermediate_size=11008,
            duration_s=0.1,
            gpu_tflops=312.0,  # A100 80GB
        )

        assert 0 <= result.mfu <= 1
        assert result.achieved_tflops > 0
        assert result.theoretical_tflops == 312.0
        assert result.total_flops > 0
        assert result.duration_s == 0.1

    def test_metric_registry(self):
        """Test metric registry."""
        # Check registered metrics
        metrics = MetricRegistry.list_all()
        assert "throughput" in metrics
        assert "latency" in metrics
        assert "memory" in metrics
        assert "kv_cache" in metrics
        assert "mfu" in metrics

        # Get metric instances
        throughput = MetricRegistry.get("throughput")
        assert isinstance(throughput, ThroughputMetric)
        assert throughput.metric_type == MetricType.THROUGHPUT

    def test_metric_summary(self):
        """Test metric summary."""
        pytest.importorskip("numpy")

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        summary = MetricSummary.from_values("test_metric", values, "ms")

        assert summary.name == "test_metric"
        assert summary.mean == 3.0
        assert summary.min == 1.0
        assert summary.max == 5.0
        assert summary.count == 5
        assert summary.unit == "ms"


class TestProfiler:
    """Test execution profiler."""

    def test_execution_tracer(self):
        """Test execution tracing."""
        tracer = ExecutionTracer()

        # Trace some operations
        with tracer.trace("operation1"):
            time.sleep(0.01)

        with tracer.trace("operation2"):
            time.sleep(0.02)

        with tracer.trace("operation1"):
            time.sleep(0.01)

        events = tracer.get_events()
        assert len(events) == 3

        # Check event details
        assert events[0].name == "operation1"
        assert events[0].duration_ms > 0

        # Filter by name
        op1_events = tracer.get_events_by_name("operation1")
        assert len(op1_events) == 2

        # Check totals
        total_time = tracer.get_total_time()
        assert total_time > 0

        avg_time = tracer.get_avg_time("operation1")
        assert avg_time > 0

    def test_chrome_trace_export(self, tmp_path):
        """Test Chrome Tracing export."""
        tracer = ExecutionTracer()

        with tracer.trace("test_op"):
            time.sleep(0.001)

        output_file = tmp_path / "trace.json"
        tracer.export_chrome_trace(str(output_file))

        assert output_file.exists()

        # Verify JSON structure
        import json

        with open(output_file) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "test_op"
        assert data[0]["ph"] == "X"


class TestReporters:
    """Test report generators."""

    def test_console_reporter(self, capsys):
        """Test console reporter."""
        reporter = ConsoleReporter()

        reporter.report_metric("throughput", 1234.5, "tokens/s")
        captured = capsys.readouterr()
        assert "throughput" in captured.out
        assert "1234.5" in captured.out

        reporter.report_summary({"mfu": 0.65, "latency_ms": 12.3})
        captured = capsys.readouterr()
        assert "Benchmark Summary" in captured.out

    def test_json_reporter(self, tmp_path):
        """Test JSON reporter."""
        output_file = tmp_path / "results.json"
        reporter = JSONReporter(output_file)

        reporter.add_metric("throughput", 1234.5, "tokens/s")
        reporter.add_metric("latency", 12.3, "ms")
        reporter.add_metadata("model", "Qwen2.5-7B")

        reporter.save()

        assert output_file.exists()

        # Load and verify
        data = JSONReporter.load(output_file)
        assert "metrics" in data
        assert "throughput" in data["metrics"]
        assert data["metrics"]["throughput"]["value"] == 1234.5
        assert data["metadata"]["model"] == "Qwen2.5-7B"

    def test_json_reporter_comparison(self, tmp_path):
        """Test JSON report comparison."""
        # Create baseline
        baseline_file = tmp_path / "baseline.json"
        baseline = JSONReporter(baseline_file)
        baseline.add_metric("throughput", 1000.0, "tokens/s")
        baseline.add_metric("latency", 10.0, "ms")
        baseline.save()

        # Create current
        current_file = tmp_path / "current.json"
        current = JSONReporter(current_file)
        current.add_metric("throughput", 1200.0, "tokens/s")
        current.add_metric("latency", 9.0, "ms")
        current.save()

        # Compare
        comparison = JSONReporter.compare(baseline_file, current_file)

        assert "changes" in comparison
        assert "throughput" in comparison["changes"]

        throughput_change = comparison["changes"]["throughput"]
        assert throughput_change["baseline"] == 1000.0
        assert throughput_change["current"] == 1200.0
        assert throughput_change["change_pct"] == pytest.approx(20.0)


class TestIntegration:
    """Integration tests."""

    def test_full_benchmark_workflow(self, tmp_path):
        """Test complete benchmark workflow."""
        # Create metrics
        throughput = ThroughputMetric()
        latency = LatencyMetric()
        tracer = ExecutionTracer()

        # Simulate benchmark
        throughput.start()

        with tracer.trace("prefill"):
            latency.record_prefill_start()
            time.sleep(0.01)
            latency.record_prefill_end()

        for i in range(10):
            with tracer.trace("decode_token"):
                time.sleep(0.001)
                latency.record_decode_token()
                throughput.record(tokens=1)

        # Compute results
        throughput_result = throughput.compute()
        latency_result = latency.compute()

        # Report to console
        console = ConsoleReporter()
        console.report_summary(
            {
                "throughput_tokens_per_s": throughput_result.tokens_per_second,
                "latency_ttft_ms": latency_result.ttft_ms,
                "latency_tpot_ms": latency_result.tpot_ms,
            }
        )

        # Save to JSON
        output_file = tmp_path / "benchmark_results.json"
        json_reporter = JSONReporter(output_file)
        json_reporter.add_metric("throughput", throughput_result.tokens_per_second, "tokens/s")
        json_reporter.add_metric("ttft", latency_result.ttft_ms, "ms")
        json_reporter.add_metadata("num_tokens", 10)
        json_reporter.save()

        assert output_file.exists()

        # Export trace
        trace_file = tmp_path / "trace.json"
        tracer.export_chrome_trace(str(trace_file))
        assert trace_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
