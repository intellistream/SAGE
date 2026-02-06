#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project
"""
Control Plane Benchmark Demo
=============================

This script demonstrates how to use the Control Plane Benchmark framework
for evaluating scheduling policies.

Usage:
    python examples/tutorials/benchmark_control_plane_demo.py

Note: This demo uses Mock mode (no actual Control Plane needed).
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


def demo_1_llm_benchmark_config():
    """Demo 1: Create and validate LLM Benchmark configuration."""
    print("\n" + "=" * 60)
    print("Demo 1: LLM Benchmark Configuration")
    print("=" * 60)

    from sage.benchmark.benchmark_control_plane import (
        ArrivalPattern,
        LLMBenchmarkConfig,
        LLMSLOConfig,
        SchedulingPolicy,
    )

    # Create configuration
    config = LLMBenchmarkConfig(
        control_plane_url="http://localhost:8080",
        num_requests=100,
        request_rate=10.0,
        warmup_requests=5,
        timeout_seconds=30.0,
        arrival_pattern=ArrivalPattern.POISSON,
        policies=[SchedulingPolicy.FIFO, SchedulingPolicy.PRIORITY],
        model_distribution={
            "Qwen/Qwen2.5-7B-Instruct": 0.7,
            "meta-llama/Llama-3-8B": 0.3,
        },
        priority_distribution={"HIGH": 0.2, "NORMAL": 0.6, "LOW": 0.2},
        slo_config=LLMSLOConfig(
            high_priority_deadline_ms=500,
            normal_priority_deadline_ms=1000,
            low_priority_deadline_ms=2000,
        ),
    )

    # Validate
    errors = config.validate()
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("Configuration is valid.")

    # Show configuration
    print("\nConfiguration summary:")
    print(f"  - Control Plane: {config.control_plane_url}")
    print(f"  - Requests: {config.num_requests}")
    print(f"  - Rate: {config.request_rate} req/s")
    print(f"  - Arrival: {config.arrival_pattern.value}")
    print(f"  - Policies: {[p.value if hasattr(p, 'value') else str(p) for p in config.policies]}")  # type: ignore
    print(f"  - Models: {config.model_distribution}")

    return config


def demo_2_hybrid_benchmark_config():
    """Demo 2: Create Hybrid (LLM + Embedding) Benchmark configuration."""
    print("\n" + "=" * 60)
    print("Demo 2: Hybrid Benchmark Configuration")
    print("=" * 60)

    from sage.benchmark.benchmark_control_plane.hybrid_scheduler import (
        HybridBenchmarkConfig,
        HybridSLOConfig,
    )

    # Create hybrid configuration
    config = HybridBenchmarkConfig(
        control_plane_url="http://localhost:8080",
        num_requests=100,
        request_rate=20.0,
        warmup_requests=5,
        # Hybrid-specific settings
        llm_ratio=0.7,  # 70% LLM, 30% Embedding
        embedding_ratio=0.3,
        llm_model_distribution={"Qwen/Qwen2.5-7B-Instruct": 1.0},
        embedding_model="BAAI/bge-m3",
        hybrid_slo_config=HybridSLOConfig(
            high_priority_deadline_ms=500,
            normal_priority_deadline_ms=1000,
            low_priority_deadline_ms=2000,
            embedding_high_priority_deadline_ms=100,
            embedding_normal_priority_deadline_ms=200,
            embedding_low_priority_deadline_ms=500,
        ),
    )

    # Validate
    errors = config.validate()
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("Hybrid configuration is valid.")

    print("\nHybrid configuration summary:")
    print(f"  - LLM Ratio: {config.llm_ratio * 100:.0f}%")
    print(f"  - Embedding Ratio: {config.embedding_ratio * 100:.0f}%")
    print(f"  - LLM Models: {config.llm_model_distribution}")
    print(f"  - Embedding Model: {config.embedding_model}")
    print(f"  - Embedding Batch Sizes: {config.embedding_batch_sizes}")

    return config


def demo_3_workload_generation():
    """Demo 3: Generate workloads for benchmarking."""
    print("\n" + "=" * 60)
    print("Demo 3: Workload Generation")
    print("=" * 60)

    from sage.benchmark.benchmark_control_plane import (
        LLMBenchmarkConfig,
        LLMWorkloadGenerator,
    )
    from sage.benchmark.benchmark_control_plane.hybrid_scheduler import (
        HybridBenchmarkConfig,
        HybridWorkloadGenerator,
    )

    # LLM Workload
    print("\n[LLM Workload]")
    llm_config = LLMBenchmarkConfig(num_requests=10, request_rate=5.0)
    llm_generator = LLMWorkloadGenerator(llm_config)
    llm_requests = llm_generator.generate()

    print(f"  Generated {len(llm_requests)} LLM requests:")
    for i, req in enumerate(llm_requests[:3]):
        print(
            f"    {i + 1}. model={req.model_name}, priority={req.priority}, time={req.scheduled_arrival_time:.2f}s"
        )
    if len(llm_requests) > 3:
        print(f"    ... and {len(llm_requests) - 3} more")

    # Hybrid Workload
    print("\n[Hybrid Workload]")
    hybrid_config = HybridBenchmarkConfig(
        num_requests=10, request_rate=5.0, llm_ratio=0.6, embedding_ratio=0.4
    )
    hybrid_generator = HybridWorkloadGenerator(hybrid_config)
    hybrid_requests = hybrid_generator.generate()

    llm_count = sum(1 for r in hybrid_requests if r.request_type.value.startswith("llm"))
    embed_count = len(hybrid_requests) - llm_count

    print(f"  Generated {len(hybrid_requests)} hybrid requests:")
    print(f"    - LLM requests: {llm_count} ({llm_count / len(hybrid_requests) * 100:.0f}%)")
    print(
        f"    - Embedding requests: {embed_count} ({embed_count / len(hybrid_requests) * 100:.0f}%)"
    )

    for i, req in enumerate(hybrid_requests[:5]):
        print(f"    {i + 1}. type={req.request_type.value}, time={req.scheduled_arrival_time:.2f}s")


def demo_4_strategy_adapter():
    """Demo 4: List available scheduling strategies."""
    print("\n" + "=" * 60)
    print("Demo 4: Available Scheduling Strategies")
    print("=" * 60)

    from sage.benchmark.benchmark_control_plane import StrategyAdapter

    print("\nAvailable strategies:")
    strategy_names = StrategyAdapter.list_strategies()
    for name in strategy_names:
        info = StrategyAdapter.get_strategy_info(name)
        if info:
            status = "available" if info.cls is not None else "not installed"
            hybrid = " (hybrid)" if info.is_hybrid else ""
            print(f"  - {info.name}: {info.description}{hybrid} [{status}]")
        else:
            print(f"  - {name}: (info not available)")


def demo_5_gpu_monitor():
    """Demo 5: GPU monitoring (auto-detect backend)."""
    print("\n" + "=" * 60)
    print("Demo 5: GPU Monitoring")
    print("=" * 60)

    from sage.benchmark.benchmark_control_plane import GPUMonitor

    # Auto-detect backend (will use mock if no GPU)
    monitor = GPUMonitor()

    print(f"\nGPU Monitor backend: {monitor.backend.value}")
    print("Starting monitoring...")
    monitor.start_monitoring(interval_seconds=0.5)

    import time

    time.sleep(1.5)  # Collect some samples

    monitor.stop_monitoring()

    summary = monitor.get_summary()
    print("\nGPU Metrics Summary:")
    print(f"  - Samples: {summary.samples}")
    print(f"  - Duration: {summary.duration_seconds:.1f}s")
    print(f"  - Avg Utilization: {summary.utilization_avg:.1f}%")
    print(f"  - Max Utilization: {summary.utilization_max:.1f}%")
    print(f"  - Avg Memory Used: {summary.memory_used_avg_mb:.0f} MB")
    print(f"  - Max Memory Used: {summary.memory_used_max_mb:.0f} MB")


def demo_6_metrics_collection():
    """Demo 6: Metrics collection and aggregation."""
    print("\n" + "=" * 60)
    print("Demo 6: Metrics Collection")
    print("=" * 60)

    from sage.benchmark.benchmark_control_plane.llm_scheduler.client import (
        LLMRequestResult,
    )
    from sage.benchmark.benchmark_control_plane.llm_scheduler.metrics import (
        LLMMetricsCollector,
    )

    collector = LLMMetricsCollector()

    # Simulate some request results
    import random
    import time

    base_time = time.time()
    for i in range(20):
        latency_s = 0.1 + random.random() * 0.2  # 100-300ms
        result = LLMRequestResult(
            request_id=f"req_{i}",
            model_name="Qwen/Qwen2.5-7B-Instruct",
            priority="NORMAL" if random.random() > 0.3 else "HIGH",
            slo_deadline_ms=500,
            send_time=base_time + i * 0.05,
            completion_time=base_time + i * 0.05 + latency_s,
            success=random.random() > 0.1,  # 90% success rate
            first_token_time=base_time + i * 0.05 + 0.02 + random.random() * 0.05,
            output_token_count=50 + int(random.random() * 100),
        )
        collector.add_result(result)

    # Set time range for accurate throughput
    collector.set_time_range(base_time, base_time + 20 * 0.05 + 0.3)

    # Get aggregated metrics
    metrics = collector.compute_metrics()

    print("\nAggregated Metrics:")
    print("  [Throughput]")
    print(f"    - Requests/s: {metrics.throughput_rps:.2f}")
    print(f"    - Tokens/s: {metrics.token_throughput_tps:.2f}")
    print("  [Latency]")
    print(f"    - E2E Avg: {metrics.e2e_latency_avg_ms:.1f} ms")
    print(f"    - E2E P50: {metrics.e2e_latency_p50_ms:.1f} ms")
    print(f"    - E2E P99: {metrics.e2e_latency_p99_ms:.1f} ms")
    print(f"    - TTFT Avg: {metrics.ttft_avg_ms:.1f} ms")
    print("  [Quality]")
    print(f"    - Success Rate: {(1 - metrics.error_rate) * 100:.1f}%")
    print(f"    - SLO Compliance: {metrics.slo_compliance_rate * 100:.1f}%")
    print("  [Volume]")
    print(f"    - Total Requests: {metrics.total_requests}")
    print(f"    - Completed: {metrics.completed_requests}")


def demo_7_chart_generation():
    """Demo 7: Generate benchmark charts."""
    print("\n" + "=" * 60)
    print("Demo 7: Chart Generation")
    print("=" * 60)

    try:
        import matplotlib

        matplotlib.use("Agg")
    except ImportError:
        print("  matplotlib not installed, skipping chart demo")
        return

    from sage.benchmark.benchmark_control_plane.visualization import BenchmarkCharts

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        charts = BenchmarkCharts(output_dir=output_dir)

        # Prepare sample data
        policy_metrics = {
            "fifo": {
                "throughput": {"requests_per_second": 95.2, "tokens_per_second": 4521},
                "latency": {
                    "e2e_avg_ms": 152.3,
                    "e2e_p50_ms": 142.0,
                    "e2e_p90_ms": 189.5,
                    "e2e_p95_ms": 215.2,
                    "e2e_p99_ms": 289.1,
                },
                "slo": {"compliance_rate": 0.92},
            },
            "priority": {
                "throughput": {"requests_per_second": 91.5, "tokens_per_second": 4312},
                "latency": {
                    "e2e_avg_ms": 168.7,
                    "e2e_p50_ms": 155.0,
                    "e2e_p90_ms": 201.3,
                    "e2e_p95_ms": 234.8,
                    "e2e_p99_ms": 312.5,
                },
                "slo": {"compliance_rate": 0.89},
            },
            "slo_aware": {
                "throughput": {"requests_per_second": 88.3, "tokens_per_second": 4156},
                "latency": {
                    "e2e_avg_ms": 145.2,
                    "e2e_p50_ms": 138.0,
                    "e2e_p90_ms": 175.6,
                    "e2e_p95_ms": 198.4,
                    "e2e_p99_ms": 256.7,
                },
                "slo": {"compliance_rate": 0.96},
            },
        }

        print("\nGenerating charts...")

        # Generate throughput comparison
        path = charts.plot_throughput_comparison(policy_metrics)
        if path:
            print(f"  - Throughput comparison: {path.name}")

        # Generate latency percentiles
        path = charts.plot_latency_percentiles(policy_metrics)
        if path:
            print(f"  - Latency percentiles: {path.name}")

        # Generate SLO compliance
        path = charts.plot_slo_compliance(policy_metrics)
        if path:
            print(f"  - SLO compliance: {path.name}")

        charts_files = list(output_dir.glob("*.png"))
        print(f"\nCharts generated: {len(charts_files)} files")
        for f in charts_files:
            print(f"  - {f.name}")


def demo_8_cli_commands():
    """Demo 8: Show CLI commands."""
    print("\n" + "=" * 60)
    print("Demo 8: CLI Commands Reference")
    print("=" * 60)

    print(
        """
The benchmark framework provides a CLI tool: sage-cp-bench

[Available Commands]

1. Run a single benchmark:
   sage-cp-bench run --mode llm --policy fifo --requests 100 --rate 10
   sage-cp-bench run --mode hybrid --policy hybrid --llm-ratio 0.7 --requests 100

2. Compare multiple policies:
   sage-cp-bench compare --mode llm --policies fifo,priority,slo_aware --requests 500
   sage-cp-bench compare --mode hybrid --policies fifo,hybrid --llm-ratio 0.7

3. Sweep request rates:
   sage-cp-bench sweep --mode llm --policy fifo --rates 10,50,100,200

4. Run predefined experiments:
   sage-cp-bench experiment --name throughput --policies fifo,priority
   sage-cp-bench experiment --name latency --policies fifo,slo_aware
   sage-cp-bench experiment --name slo --policies fifo,priority,slo_aware
   sage-cp-bench experiment --name mixed_ratio --policies hybrid

5. Generate visualizations from results:
   sage-cp-bench visualize --input results.json --output ./charts --format all

6. Show/save example config:
   sage-cp-bench config --show
   sage-cp-bench config --save ./my_config.yaml

7. Validate config file:
   sage-cp-bench validate --config ./my_config.yaml

[Common Options]
   --control-plane, -c   Control Plane URL (default: http://localhost:8080)
   --output, -o          Output directory (default: ./benchmark_results)
   --no-visualize        Disable auto visualization
   --quiet, -q           Suppress progress output
"""
    )


async def demo_9_mock_benchmark_run():
    """Demo 9: Run a mock benchmark (no actual Control Plane)."""
    print("\n" + "=" * 60)
    print("Demo 9: Mock Benchmark Run")
    print("=" * 60)

    from sage.benchmark.benchmark_control_plane import (
        LLMBenchmarkConfig,
        LLMBenchmarkRunner,
    )

    # Create a minimal config for demo
    config = LLMBenchmarkConfig(
        control_plane_url="http://localhost:8080",  # Won't actually connect
        num_requests=5,
        request_rate=10.0,
        warmup_requests=0,
        timeout_seconds=1.0,
        policies=["fifo"],
    )

    print("\nNote: This demo shows the runner structure.")
    print("In production, it would send requests to an actual Control Plane.")

    _runner = LLMBenchmarkRunner(config)  # noqa: F841
    print("\nRunner created:")
    print(f"  - Config: {config.num_requests} requests at {config.request_rate} req/s")
    print(f"  - Policies: {config.policies}")
    print(f"  - Output directory: {config.output_dir}")

    print("\nTo run an actual benchmark, start a Control Plane first:")
    print("  sage studio start")
    print("  # or")
    print("  sage apps llm start --port 8080")


def main():
    """Run all demos."""
    print("=" * 60)
    print("Control Plane Benchmark Framework Demo")
    print("=" * 60)

    # Configuration demos
    demo_1_llm_benchmark_config()
    demo_2_hybrid_benchmark_config()

    # Workload generation
    demo_3_workload_generation()

    # Strategy and monitoring
    demo_4_strategy_adapter()
    demo_5_gpu_monitor()

    # Metrics
    demo_6_metrics_collection()

    # Visualization
    demo_7_chart_generation()

    # CLI reference
    demo_8_cli_commands()

    # Mock run
    asyncio.run(demo_9_mock_benchmark_run())

    print("\n" + "=" * 60)
    print("Demo completed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
