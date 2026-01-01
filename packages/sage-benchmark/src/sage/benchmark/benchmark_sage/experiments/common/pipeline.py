"""
Distributed Scheduling Benchmark - Pipeline Factory
====================================================

Provides pipeline factories for distributed scheduling benchmarks:
- Compute pipeline (pure CPU scheduling test)
- LLM pipeline (LLM inference)
- RAG pipeline (fine-grained: Retriever -> Reranker -> Promptor -> Generator)
- Mixed pipeline (Compute + RAG stages)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.kernel.api.remote_environment import RemoteEnvironment

try:
    from .models import BenchmarkConfig, BenchmarkMetrics
    from .operators import (
        ComputeOperator,
        LLMOperator,
        MetricsSink,
        TaskSource,
    )
except ImportError:
    from models import BenchmarkConfig, BenchmarkMetrics
    from operators import (
        ComputeOperator,
        LLMOperator,
        MetricsSink,
        TaskSource,
    )


class SchedulingBenchmarkPipeline:
    """
    Pipeline factory for distributed scheduling benchmarks.

    Supports multiple pipeline types:
    - compute: Pure CPU computation for scheduling overhead testing
    - llm: Single-stage LLM inference
    - rag: Fine-grained RAG with Retriever -> Reranker -> Promptor -> Generator
    - rag_full: Full RAG with Retriever -> Reranker -> Refiner -> Promptor -> Generator
    - mixed: Compute + RAG stages
    """

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.env = None
        self.scheduler = None
        self.metrics = BenchmarkMetrics(config=config)

    def _create_scheduler(self):
        """Create scheduler based on config."""
        from sage.kernel.scheduler.impl import get_scheduler

        scheduler_type = self.config.scheduler_type
        platform = "remote" if self.config.use_remote else "local"

        scheduler_kwargs: dict[str, Any] = {"platform": platform}

        # Only add max_concurrent for schedulers that support it (FIFO doesn't support it)
        if scheduler_type in ["load_aware", "priority", "round_robin"]:
            scheduler_kwargs["max_concurrent"] = self.config.parallelism * 100

        # Add strategy for LoadAwareScheduler
        if scheduler_type == "load_aware":
            scheduler_kwargs["strategy"] = self.config.scheduler_strategy

        return get_scheduler(scheduler_type, **scheduler_kwargs)

    def _create_environment(self, name: str) -> LocalEnvironment | RemoteEnvironment:
        """Create execution environment (local or remote)."""
        if self.config.use_remote:
            from pathlib import Path

            from sage.kernel.api.remote_environment import RemoteEnvironment

            # Get the experiments directory path for Ray runtime_env
            experiments_dir = Path(__file__).resolve().parent.parent

            # Create config with runtime_env for Ray to find our modules
            config = {
                "runtime_env": {
                    "env_vars": {"PYTHONPATH": str(experiments_dir)},
                    "working_dir": str(experiments_dir),
                }
            }

            self.scheduler = self._create_scheduler()
            self.env = RemoteEnvironment(
                name=name,
                scheduler=self.scheduler,
                host=self.config.head_node,
                config=config,
                extra_python_paths=[str(experiments_dir)],
            )
        else:
            from sage.kernel.api.local_environment import LocalEnvironment

            self.env = LocalEnvironment(name)

        return self.env

    def _get_retriever_config(self) -> dict[str, Any]:
        """Get retriever configuration."""
        return {
            "dimension": 1024,
            "top_k": getattr(self.config, "retriever_top_k", 10),
            "embedding": {
                "method": "default",
                "model": self.config.embedding_model,
            },
            "chroma": {
                "collection_name": "benchmark_knowledge",
                "persist_directory": None,
            },
        }

    def _get_reranker_config(self) -> dict[str, Any]:
        """Get reranker configuration."""
        return {
            "model_name": "BAAI/bge-reranker-v2-m3",
            "top_k": getattr(self.config, "reranker_top_k", 5),
        }

    def _get_promptor_config(self) -> dict[str, Any]:
        """Get promptor configuration."""
        return {
            "use_short_answer": False,
        }

    def _get_generator_config(self) -> dict[str, Any]:
        """Get generator configuration."""
        return {
            "method": "openai",
            "model_name": self.config.llm_model,
            "base_url": self.config.llm_base_url,
            "api_key": "EMPTY",
            "max_tokens": self.config.max_tokens,
        }

    def _get_refiner_config(self) -> dict[str, Any]:
        """Get refiner configuration."""
        return {
            "algorithm": "simple",
            "budget": 2048,
            "enable_cache": True,
        }

    # =========================================================================
    # Pipeline Builders
    # =========================================================================

    def build_compute_pipeline(
        self, name: str = "compute_benchmark"
    ) -> SchedulingBenchmarkPipeline:
        """
        Build compute-only pipeline for testing scheduling overhead.

        Pipeline: TaskSource -> ComputeOperator (x N stages) -> MetricsSink
        """
        env = self._create_environment(name)

        pipeline = env.from_source(
            TaskSource,
            num_tasks=self.config.num_tasks,
            task_complexity=self.config.task_complexity,
        )

        for stage in range(1, self.config.pipeline_stages + 1):
            pipeline = pipeline.map(
                ComputeOperator,
                parallelism=self.config.parallelism,
                complexity=self.config.task_complexity,
                stage=stage,
            )

        pipeline.sink(
            MetricsSink,
            metrics_collector=self.metrics,
            verbose=not self.config.test_mode,
        )

        return self

    def build_llm_pipeline(self, name: str = "llm_benchmark") -> SchedulingBenchmarkPipeline:
        """
        Build single-stage LLM inference pipeline.

        Pipeline: TaskSource -> LLMOperator -> MetricsSink
        """
        env = self._create_environment(name)

        (
            env.from_source(
                TaskSource,
                num_tasks=self.config.num_tasks,
                task_complexity=self.config.task_complexity,
            )
            .map(
                LLMOperator,
                parallelism=self.config.parallelism,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                max_tokens=self.config.max_tokens,
                stage=1,
            )
            .sink(
                MetricsSink,
                metrics_collector=self.metrics,
                verbose=not self.config.test_mode,
            )
        )

        return self

    def build_rag_pipeline(self, name: str = "rag_benchmark") -> SchedulingBenchmarkPipeline:
        """
        Build fine-grained RAG pipeline using sage-middleware operators.

        Pipeline: TaskSource -> SimpleRetriever -> SimpleReranker -> SimplePromptor -> SimpleGenerator -> MetricsSink

        Each stage runs with configurable parallelism for distributed scheduling.
        """
        from .operators import (
            SimpleGenerator,
            SimplePromptor,
            SimpleReranker,
            SimpleRetriever,
        )

        env = self._create_environment(name)

        (
            env.from_source(
                TaskSource,
                num_tasks=self.config.num_tasks,
                task_complexity=self.config.task_complexity,
            )
            .map(
                SimpleRetriever,
                parallelism=self.config.parallelism,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                top_k=10,
                stage=1,
            )
            .map(
                SimpleReranker,
                parallelism=self.config.parallelism,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                top_k=5,
                stage=2,
            )
            .map(
                SimplePromptor,
                parallelism=self.config.parallelism,
                stage=3,
            )
            .map(
                SimpleGenerator,
                parallelism=self.config.parallelism,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                max_tokens=self.config.max_tokens,
                output_file=self.config.llm_output_file,
                stage=4,
            )
            .sink(
                MetricsSink,
                metrics_collector=self.metrics,
                verbose=not self.config.test_mode,
            )
        )

        return self

    def build_rag_full_pipeline(
        self, name: str = "rag_full_benchmark"
    ) -> SchedulingBenchmarkPipeline:
        """
        Build full RAG pipeline with refiner.

        Pipeline: TaskSource -> SimpleRetriever -> SimpleReranker -> RefinerOperator
                  -> SimplePromptor -> SimpleGenerator -> MetricsSink
        """
        from sage.middleware.operators.rag import RefinerOperator

        from .operators import (
            SimpleGenerator,
            SimplePromptor,
            SimpleReranker,
            SimpleRetriever,
        )

        env = self._create_environment(name)

        (
            env.from_source(
                TaskSource,
                num_tasks=self.config.num_tasks,
                task_complexity=self.config.task_complexity,
            )
            .map(
                SimpleRetriever,
                parallelism=self.config.parallelism,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                top_k=10,
                stage=1,
            )
            .map(
                SimpleReranker,
                parallelism=self.config.parallelism,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                top_k=5,
                stage=2,
            )
            .map(
                RefinerOperator,
                parallelism=self.config.parallelism,
                config=self._get_refiner_config(),
            )
            .map(
                SimplePromptor,
                parallelism=self.config.parallelism,
                stage=3,
            )
            .map(
                SimpleGenerator,
                parallelism=self.config.parallelism,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                max_tokens=self.config.max_tokens,
                output_file=self.config.llm_output_file,
                stage=4,
            )
            .sink(
                MetricsSink,
                metrics_collector=self.metrics,
                verbose=not self.config.test_mode,
            )
        )

        return self

    def build_mixed_pipeline(self, name: str = "mixed_benchmark") -> SchedulingBenchmarkPipeline:
        """
        Build mixed pipeline: Compute -> RAG stages -> Compute

        Pipeline: TaskSource -> ComputeOperator -> SimpleRetriever -> SimpleReranker
                  -> SimplePromptor -> SimpleGenerator -> ComputeOperator -> MetricsSink
        """
        from .operators import (
            SimpleGenerator,
            SimplePromptor,
            SimpleReranker,
            SimpleRetriever,
        )

        env = self._create_environment(name)

        (
            env.from_source(
                TaskSource,
                num_tasks=self.config.num_tasks,
                task_complexity=self.config.task_complexity,
            )
            .map(
                ComputeOperator,
                parallelism=self.config.parallelism,
                complexity="light",
                stage=1,
            )
            .map(
                SimpleRetriever,
                parallelism=self.config.parallelism,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                top_k=10,
                stage=2,
            )
            .map(
                SimpleReranker,
                parallelism=self.config.parallelism,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                top_k=5,
                stage=3,
            )
            .map(
                SimplePromptor,
                parallelism=self.config.parallelism,
                stage=4,
            )
            .map(
                SimpleGenerator,
                parallelism=self.config.parallelism,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                max_tokens=self.config.max_tokens,
                output_file=self.config.llm_output_file,
                stage=5,
            )
            .map(
                ComputeOperator,
                parallelism=self.config.parallelism,
                complexity="light",
                stage=6,
            )
            .sink(
                MetricsSink,
                metrics_collector=self.metrics,
                verbose=not self.config.test_mode,
            )
        )

        return self

    def build_custom_pipeline(
        self,
        name: str,
        stages: list[tuple[type, dict[str, Any]]],
    ) -> SchedulingBenchmarkPipeline:
        """
        Build custom pipeline with arbitrary stages.

        Args:
            name: Pipeline name
            stages: List of (OperatorClass, kwargs) tuples
        """
        env = self._create_environment(name)

        pipeline = env.from_source(
            TaskSource,
            num_tasks=self.config.num_tasks,
            task_complexity=self.config.task_complexity,
        )

        for operator_cls, kwargs in stages:
            kwargs.setdefault("parallelism", self.config.parallelism)
            pipeline = pipeline.map(operator_cls, **kwargs)

        pipeline.sink(
            MetricsSink,
            metrics_collector=self.metrics,
            verbose=not self.config.test_mode,
        )

        return self

    # =========================================================================
    # Pipeline Execution
    # =========================================================================

    def run(self) -> BenchmarkMetrics:
        """Run the pipeline and collect metrics."""
        if self.env is None:
            raise RuntimeError("Pipeline not built. Call build_*() first.")

        print(f"\n{'=' * 70}")
        print(f"Running Benchmark: {self.config.experiment_name}")
        print(f"{'=' * 70}")
        print(f"  Tasks:       {self.config.num_tasks}")
        print(f"  Parallelism: {self.config.parallelism}")
        print(f"  Nodes:       {self.config.num_nodes}")
        print(f"  Scheduler:   {self.config.scheduler_type}")
        print(f"  Environment: {'Remote' if self.config.use_remote else 'Local'}")
        print(f"{'=' * 70}\n")

        self.metrics.total_tasks = self.config.num_tasks
        self.metrics.start_time = time.time()
        run_start_timestamp = int(time.time() * 1000)  # For finding metrics file

        try:
            self.env.submit(autostop=True)

            if self.config.use_remote:
                self.env._wait_for_completion()

            self.metrics.end_time = time.time()
            self.metrics.total_duration = self.metrics.end_time - self.metrics.start_time

            # In Remote mode, read metrics from MetricsSink output files
            if self.config.use_remote:
                self._collect_metrics_from_files(run_start_timestamp)

        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback

            traceback.print_exc()
            self.metrics.end_time = time.time()
            self.metrics.total_duration = self.metrics.end_time - self.metrics.start_time

        finally:
            try:
                self.env.close()
            except Exception:
                pass

        return self.metrics

    def _collect_metrics_from_files(self, run_start_timestamp: int) -> None:
        """
        Collect metrics from MetricsSink output files in Remote mode.

        In Remote mode, MetricsSink writes results to /tmp/sage_metrics/ on the worker nodes.
        This method reads those files and aggregates the results into self.metrics.
        """
        import json
        from pathlib import Path

        metrics_dir = Path("/tmp/sage_metrics")
        if not metrics_dir.exists():
            print("[Warning] Metrics directory not found: /tmp/sage_metrics")
            return

        # Find metrics files created after run_start_timestamp
        metrics_files = []
        for f in metrics_dir.glob("metrics_*.jsonl"):
            try:
                # Extract timestamp from filename: metrics_{hostname}_{pid}_{timestamp}.jsonl
                parts = f.stem.split("_")
                if len(parts) >= 4:
                    file_timestamp = int(parts[-1])
                    if file_timestamp >= run_start_timestamp:
                        metrics_files.append(f)
            except (ValueError, IndexError):
                continue

        if not metrics_files:
            print(f"[Warning] No metrics files found after timestamp {run_start_timestamp}")
            return

        print(f"[Metrics] Found {len(metrics_files)} metrics file(s)")

        # Aggregate results from all files
        total_success = 0
        total_fail = 0
        all_latencies = []
        node_distribution = {}

        for metrics_file in metrics_files:
            try:
                with open(metrics_file) as f:
                    for line in f:
                        data = json.loads(line.strip())
                        record_type = data.get("type", "task")

                        if record_type == "task":
                            if data.get("success"):
                                total_success += 1
                            else:
                                total_fail += 1

                            latency = data.get("total_latency_ms", 0)
                            if latency > 0:
                                all_latencies.append(latency)

                            node_id = data.get("node_id", "unknown")
                            node_distribution[node_id] = node_distribution.get(node_id, 0) + 1

                        elif record_type == "summary":
                            # Can use summary for verification
                            pass
            except Exception as e:
                print(f"[Warning] Error reading metrics file {metrics_file}: {e}")

        # Update self.metrics
        self.metrics.successful_tasks = total_success
        self.metrics.failed_tasks = total_fail
        self.metrics.node_distribution = node_distribution
        self.metrics.total_latencies = all_latencies

        # Calculate aggregate stats
        if all_latencies:
            pass  # scheduling_latencies not available in remote mode

        print(
            f"[Metrics] Aggregated: {total_success} success, {total_fail} failed, "
            f"nodes: {list(node_distribution.keys())}"
        )

    def build_simple_rag_pipeline(
        self, name: str = "simple_rag_benchmark"
    ) -> SchedulingBenchmarkPipeline:
        """
        Build simple RAG pipeline using remote embedding service.

        Pipeline: TaskSource -> SimpleRetriever -> SimpleReranker -> SimplePromptor -> SimpleGenerator -> MetricsSink

        Uses remote embedding service (http://LLM_HOST:8090/v1) instead of local models.
        """
        from .operators import (
            SimpleGenerator,
            SimplePromptor,
            SimpleReranker,
            SimpleRetriever,
        )

        env = self._create_environment(name)

        (
            env.from_source(
                TaskSource,
                num_tasks=self.config.num_tasks,
                task_complexity=self.config.task_complexity,
            )
            .map(
                SimpleRetriever,
                parallelism=self.config.parallelism,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                top_k=10,
                stage=1,
            )
            .map(
                SimpleReranker,
                parallelism=self.config.parallelism,
                embedding_base_url=self.config.embedding_base_url,
                embedding_model=self.config.embedding_model,
                top_k=5,
                stage=2,
            )
            .map(
                SimplePromptor,
                parallelism=self.config.parallelism,
                stage=3,
            )
            .map(
                SimpleGenerator,
                parallelism=self.config.parallelism,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                max_tokens=self.config.max_tokens,
                output_file=self.config.llm_output_file,
                stage=4,
            )
            .sink(
                MetricsSink,
                metrics_collector=self.metrics,
                verbose=not self.config.test_mode,
            )
        )

        return self
