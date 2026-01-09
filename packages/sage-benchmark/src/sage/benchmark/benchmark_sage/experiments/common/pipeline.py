"""
Distributed Scheduling Benchmark - Pipeline Factory
====================================================

Provides pipeline factories for distributed scheduling benchmarks:
- Compute pipeline (pure CPU scheduling test)
- LLM pipeline (LLM inference)
- RAG pipeline (fine-grained: Retriever -> Reranker -> Promptor -> Generator)
- Mixed pipeline (Compute + RAG stages)

Service Registration:
- embedding_service: Remote embedding service for vectorization
- vector_db: SageDBService for knowledge base retrieval
- llm_service: LLM service for generation
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
        SAMPLE_KNOWLEDGE_BASE,
    )
except ImportError:
    from models import BenchmarkConfig, BenchmarkMetrics
    from operators import (
        ComputeOperator,
        LLMOperator,
        MetricsSink,
        TaskSource,
        SAMPLE_KNOWLEDGE_BASE,
    )


# =============================================================================
# Service Registration Helpers
# =============================================================================


def register_embedding_service(
    env: LocalEnvironment | RemoteEnvironment,
    base_url: str,
    model: str,
) -> bool:
    """
    Register embedding service for vectorization.

    Uses remote embedding API (OpenAI-compatible).
    All operators access via self.call_service("embedding").

    Args:
        env: Environment to register service
        base_url: Embedding service URL (e.g., http://host:8090/v1)
        model: Embedding model name

    Returns:
        True if registered successfully
    """
    try:
        class EmbeddingService:
            """Remote embedding service wrapper (lazy init to avoid SSLContext serialization)"""

            def __init__(self, base_url: str, model: str):
                self.base_url = base_url.rstrip("/")
                self.model = model
                self._client = None  # Lazy init

            def _get_client(self):
                """Lazy create httpx client (avoids SSLContext pickle issues)"""
                if self._client is None:
                    import httpx
                    self._client = httpx.Client(timeout=60.0)
                return self._client

            def embed(self, texts: list[str]) -> list[list[float]]:
                """Get embeddings for texts"""
                try:
                    response = self._get_client().post(
                        f"{self.base_url}/embeddings",
                        json={"input": texts, "model": self.model},
                    )
                    response.raise_for_status()
                    result = response.json()
                    return [item["embedding"] for item in result["data"]]
                except Exception as e:
                    print(f"[EmbeddingService] Error: {e}")
                    return []

            def process(self, texts: list[str]) -> list[list[float]]:
                """Default RPC method - alias for embed"""
                return self.embed(texts)

            def close(self):
                if self._client is not None:
                    self._client.close()
                    self._client = None

        # Register service class with kwargs (NOT a lambda)
        # ServiceFactory will instantiate the class with context injection
        env.register_service("embedding", EmbeddingService, base_url=base_url, model=model)
        print(f"[Pipeline] Registered embedding service: {model} @ {base_url}")
        return True

    except Exception as e:
        print(f"[Pipeline] Failed to register embedding service: {e}")
        return False


def register_vector_db_service(
    env: LocalEnvironment | RemoteEnvironment,
    embedding_base_url: str,
    embedding_model: str,
    knowledge_base: list[dict[str, Any]] | None = None,
    dimension: int | None = None,
) -> bool:
    """
    Register SageDBService for vector search (RAG).

    Uses lazy initialization to avoid serialization issues with C++ extensions.
    All operators access via self.call_service("vector_db").

    Args:
        env: Environment to register service
        embedding_base_url: Embedding service URL
        embedding_model: Embedding model name
        knowledge_base: Documents to pre-load (uses SAMPLE_KNOWLEDGE_BASE if None)
        dimension: Vector dimension (auto-detected if None)

    Returns:
        True if registered successfully
    """
    try:
        kb = knowledge_base or SAMPLE_KNOWLEDGE_BASE

        # Lazy-init wrapper that creates SageDB on first use
        class LazyVectorDBService:
            """Lazy-initialized vector DB service (avoids C++ pickle issues)"""

            def __init__(
                self,
                embedding_url: str,
                embedding_model_name: str,
                initial_data: list[dict],
                dim: int | None,
            ):
                self._embedding_url = embedding_url
                self._embedding_model = embedding_model_name
                self._initial_data = initial_data
                self._dim = dim
                self._db = None  # Lazy init

            def _get_embeddings(self, texts: list[str]) -> list[list[float]] | None:
                """Get embeddings from remote service"""
                try:
                    import httpx
                    with httpx.Client(timeout=60.0) as client:
                        response = client.post(
                            f"{self._embedding_url.rstrip('/')}/embeddings",
                            json={"input": texts, "model": self._embedding_model},
                        )
                        response.raise_for_status()
                        result = response.json()
                        return [item["embedding"] for item in result["data"]]
                except Exception as e:
                    print(f"[VectorDB] Embedding error: {e}")
                return None

            def _ensure_initialized(self):
                """Initialize SageDB on first use"""
                if self._db is not None:
                    return

                import numpy as np
                from sage.middleware.components.sage_db.python.micro_service.sage_db_service import (
                    SageDBService,
                )

                # Get dimension
                dim = self._dim
                if dim is None:
                    sample_text = self._initial_data[0].get("content", "test")
                    embeddings = self._get_embeddings([sample_text])
                    if embeddings:
                        dim = len(embeddings[0])
                        print(f"[VectorDB] Auto-detected dimension: {dim}")
                    else:
                        dim = 1024
                        print(f"[VectorDB] Using default dimension: {dim}")

                # Create SageDB
                self._db = SageDBService(dimension=dim, index_type="AUTO")

                # Get embeddings for all documents
                texts = [
                    item.get("content", item.get("text", ""))
                    for item in self._initial_data
                ]
                embeddings = self._get_embeddings(texts)

                if embeddings is not None:
                    vectors = np.array(embeddings, dtype=np.float32)
                    print(f"[VectorDB] Using real embeddings (dim={dim})")
                else:
                    # Fallback: hash-based mock embeddings
                    print(f"[VectorDB] Using mock embeddings (dim={dim})")
                    vectors = []
                    for text in texts:
                        vec = np.zeros(dim, dtype=np.float32)
                        for i, char in enumerate(text[:dim]):
                            vec[i % dim] += ord(char) / 1000.0
                        vec = vec / (np.linalg.norm(vec) + 1e-8)
                        vectors.append(vec)
                    vectors = np.array(vectors, dtype=np.float32)

                # Build metadata
                metadata_list = [
                    {
                        "id": item.get("id", str(i)),
                        "title": item.get("title", ""),
                        "content": item.get("content", item.get("text", "")),
                    }
                    for i, item in enumerate(self._initial_data)
                ]

                # Add to database
                self._db.add_batch(vectors, metadata_list)
                self._db._db.build_index()
                print(f"[VectorDB] Loaded {len(vectors)} documents")

            def search(self, query_vec, k: int = 5) -> list[tuple[float, dict]]:
                """Search for similar documents"""
                self._ensure_initialized()
                return self._db.search(query_vec, k=k)

            def process(self, query_vec, k: int = 5) -> list[tuple[float, dict]]:
                """Default RPC method - alias for search"""
                return self.search(query_vec, k=k)

            def add_batch(self, vectors, metadata_list):
                """Add documents to the database"""
                self._ensure_initialized()
                return self._db.add_batch(vectors, metadata_list)

        # Register service class with kwargs (NOT a lambda)
        # ServiceFactory will instantiate the class with context injection
        env.register_service(
            "vector_db",
            LazyVectorDBService,
            embedding_url=embedding_base_url,
            embedding_model_name=embedding_model,
            initial_data=kb,
            dim=dimension,
        )
        print("[Pipeline] Registered vector_db (LazyVectorDBService)")
        return True

    except Exception as e:
        print(f"[Pipeline] Failed to register vector_db: {e}")
        import traceback
        traceback.print_exc()
        return False

def register_llm_service(
    env: LocalEnvironment | RemoteEnvironment,
    base_url: str,
    model: str,
    max_tokens: int = 256,
) -> bool:
    """
    Register LLM service for generation.

    Uses remote LLM API (OpenAI-compatible).
    All operators access via self.call_service("llm").

    Args:
        env: Environment to register service
        base_url: LLM service URL (e.g., http://host:8903/v1)
        model: LLM model name
        max_tokens: Default max tokens for generation

    Returns:
        True if registered successfully
    """
    try:
        import httpx

        class LLMService:
            """Remote LLM service wrapper"""

            def __init__(self, base_url: str, model: str, max_tokens: int):
                self.base_url = base_url.rstrip("/")
                self.model = model
                self.max_tokens = max_tokens
                self._client = None  # Lazy init

            def _get_client(self):
                """Lazy create httpx client (avoids SSLContext pickle issues)"""
                if self._client is None:
                    import httpx
                    self._client = httpx.Client(timeout=120.0)
                return self._client

            def chat(
                self,
                messages: list[dict[str, str]],
                max_tokens: int | None = None,
                temperature: float = 0.7,
            ) -> str:
                """Chat completion"""
                try:
                    response = self._get_client().post(
                        f"{self.base_url}/chat/completions",
                        json={
                            "model": self.model,
                            "messages": messages,
                            "max_tokens": max_tokens or self.max_tokens,
                            "temperature": temperature,
                        },
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                except Exception as e:
                    return f"[LLM Error] {e}"

            def process(
                self,
                messages: list[dict[str, str]],
                max_tokens: int | None = None,
                temperature: float = 0.7,
            ) -> str:
                """Default RPC method - alias for chat"""
                return self.chat(messages, max_tokens=max_tokens, temperature=temperature)

            def close(self):
                if self._client is not None:
                    self._client.close()
                    self._client = None

        # Register service class with kwargs (NOT a lambda)
        # ServiceFactory will instantiate the class with context injection
        env.register_service("llm", LLMService, base_url=base_url, model=model, max_tokens=max_tokens)
        print(f"[Pipeline] Registered llm service: {model} @ {base_url}")
        return True

    except Exception as e:
        print(f"[Pipeline] Failed to register llm service: {e}")
        return False


def register_all_services(
    env: LocalEnvironment | RemoteEnvironment,
    config: BenchmarkConfig,
    knowledge_base: list[dict[str, Any]] | None = None,
) -> dict[str, bool]:
    """
    Register all RAG services for the pipeline.

    Args:
        env: Environment to register services
        config: Benchmark configuration
        knowledge_base: Optional custom knowledge base

    Returns:
        Dict mapping service name to registration success
    """
    results = {}

    results["embedding"] = register_embedding_service(
        env,
        base_url=config.embedding_base_url,
        model=config.embedding_model,
    )

    results["vector_db"] = register_vector_db_service(
        env,
        embedding_base_url=config.embedding_base_url,
        embedding_model=config.embedding_model,
        knowledge_base=knowledge_base,
    )

    results["llm"] = register_llm_service(
        env,
        base_url=config.llm_base_url,
        model=config.llm_model,
        max_tokens=config.max_tokens,
    )

    return results


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
            import os
            from pathlib import Path

            from sage.kernel.api.remote_environment import RemoteEnvironment

            # Get the experiments directory path for Ray runtime_env
            experiments_dir = Path(__file__).resolve().parent.parent
            
            # Get sage-benchmark/src for proper module resolution
            # Path: common/pipeline.py -> experiments -> benchmark_sage -> benchmark -> sage -> src
            # This ensures workers can import sage.benchmark.benchmark_sage.experiments.common.operators
            sage_benchmark_src = Path(__file__).resolve().parent.parent.parent.parent.parent.parent

            # CRITICAL: Set PYTHONPATH environment variable BEFORE creating RemoteEnvironment
            # This ensures RayQueueManager (created during environment setup) can find common module
            pythonpath_value = f"{sage_benchmark_src}:{experiments_dir}"
            existing_pythonpath = os.environ.get("PYTHONPATH", "")
            if existing_pythonpath:
                pythonpath_value = f"{pythonpath_value}:{existing_pythonpath}"
            os.environ["PYTHONPATH"] = pythonpath_value
            print(f"[Pipeline] Set PYTHONPATH: {pythonpath_value}")

            # Create config with runtime_env for Ray to find our modules
            config = {
                "runtime_env": {
                    "env_vars": {
                        "PYTHONPATH": pythonpath_value
                    },
                    "working_dir": str(experiments_dir),
                }
            }

            self.scheduler = self._create_scheduler()
            self.env = RemoteEnvironment(
                name=name,
                scheduler=self.scheduler,
                host=self.config.head_node,
                config=config,
                extra_python_paths=[str(sage_benchmark_src), str(experiments_dir)],
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
            "api_key": "EMPTY",  # pragma: allowlist secret
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

    def build_rag_service_pipeline(
        self, name: str = "rag_service_benchmark"
    ) -> SchedulingBenchmarkPipeline:
        """
        Build RAG pipeline using service-based operators.

        Uses register_service() pattern to avoid distributed access issues.
        Services are registered once on Head node, accessed via self.call_service().

        Pipeline: TaskSource -> ServiceRetriever -> ServiceReranker
                  -> ServicePromptor -> ServiceGenerator -> MetricsSink

        Advantages over SimpleXxx operators:
        - No duplicate embedding/index loading across workers
        - Shared vector_db service for all retrieval operations
        - Better resource utilization in distributed mode
        """
        from .operators import (
            ServiceGenerator,
            ServicePromptor,
            ServiceReranker,
            ServiceRetriever,
        )

        env = self._create_environment(name)

        # Register all services (embedding, vector_db, llm)
        print("\n[Pipeline] Registering services for RAG pipeline...")
        service_results = register_all_services(env, self.config)
        for svc_name, success in service_results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {svc_name}")
        print()

        (
            env.from_source(
                TaskSource,
                num_tasks=self.config.num_tasks,
                task_complexity=self.config.task_complexity,
            )
            .map(
                ServiceRetriever,
                parallelism=self.config.parallelism,
                top_k=10,
                stage=1,
            )
            .map(
                ServiceReranker,
                parallelism=self.config.parallelism,
                top_k=5,
                stage=2,
            )
            .map(
                ServicePromptor,
                parallelism=self.config.parallelism,
                stage=3,
            )
            .map(
                ServiceGenerator,
                parallelism=self.config.parallelism,
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

    def _gather_remote_metrics(self) -> None:
        """Gather metrics files from remote worker nodes."""
        import subprocess
        from pathlib import Path

        metrics_dir = Path("/tmp/sage_metrics")
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Use hardcoded worker node hostnames directly
        # (Ray returns IPs like 172.20.0.x instead of hostnames)
        worker_nodes = ["sage-node-2", "sage-node-3", "sage-node-4"]

        print(f"[Metrics] Gathering metrics from remote nodes: {worker_nodes}")
        for node in worker_nodes:
            try:
                cmd = f"scp -o StrictHostKeyChecking=no {node}:/tmp/sage_metrics/*.jsonl /tmp/sage_metrics/ 2>/dev/null"
                subprocess.run(cmd, shell=True, timeout=10)
            except Exception as e:
                print(f"[Metrics] Warning: Could not gather from {node}: {e}")

    def _collect_metrics_from_files(self, run_start_timestamp: int) -> None:
        """
        Collect metrics from MetricsSink output files in Remote mode.

        In Remote mode, MetricsSink writes results to /tmp/sage_metrics/ on the worker nodes.
        This method first gathers files from remote nodes, then aggregates the results.
        """
        import json
        from pathlib import Path

        # First gather metrics from remote nodes
        self._gather_remote_metrics()

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

    def build_adaptive_rag_pipeline(
        self,
        name: str = "adaptive_rag_benchmark",
        queries: list[str] | None = None,
        max_iterations: int = 3,
    ) -> SchedulingBenchmarkPipeline:
        """
        Build Adaptive-RAG pipeline with multi-branch routing.

        Pipeline Architecture:
        ```
                              ┌─ filter(ZERO) ─> NoRetrieval ─> Sink
        Source ─> Classifier ─┼─ filter(SINGLE) ─> SingleRetrieval ─> Sink
                              └─ filter(MULTI) ─> [Retrieve -> Reason] x N ─> Synthesize ─> Sink
        ```

        Each query is routed to the appropriate strategy based on complexity.
        """
        from .operators import (
            AdaptiveRAGQuerySource,
            AdaptiveRAGResultSink,
            FinalSynthesizer,
            IterativeReasoner,
            IterativeRetrievalInit,
            IterativeRetriever,
            MultiComplexityFilter,
            NoRetrievalStrategy,
            QueryClassifier,
            SingleComplexityFilter,
            SingleRetrievalStrategy,
            ZeroComplexityFilter,
        )

        # Default queries if not provided
        if queries is None:
            queries = [
                "What is machine learning?",
                "How does BERT work for NLP tasks?",
                "Compare Japan and Germany economic policies",
            ]

        env = self._create_environment(name)
        AdaptiveRAGResultSink.clear_results()

        # Register services for vector retrieval (embedding + vector_db + llm)
        print("\n[Pipeline] Registering services for Adaptive-RAG...")
        service_results = register_all_services(env, self.config)
        for svc_name, success in service_results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {svc_name}")
        print()

        # Source -> Classifier (use LLM for classification)
        classified_stream = (
            env.from_source(AdaptiveRAGQuerySource, queries=queries, delay=0.1)
            .map(
                QueryClassifier,
                parallelism=self.config.parallelism,
                classifier_type="llm",
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
            )
        )

        # Branch A: ZERO complexity - direct generation
        (
            classified_stream
            .filter(ZeroComplexityFilter)
            .map(
                NoRetrievalStrategy,
                parallelism=self.config.parallelism,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
            )
            .sink(AdaptiveRAGResultSink, branch_name="ZERO", parallelism=1)
        )

        # Branch B: SINGLE complexity - single retrieval
        (
            classified_stream
            .filter(SingleComplexityFilter)
            .map(
                SingleRetrievalStrategy,
                parallelism=self.config.parallelism,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
            )
            .sink(AdaptiveRAGResultSink, branch_name="SINGLE", parallelism=1)
        )

        # Branch C: MULTI complexity - iterative retrieval (loop unrolling)
        multi_stream = (
            classified_stream
            .filter(MultiComplexityFilter)
            .map(IterativeRetrievalInit, parallelism=self.config.parallelism)
        )

        # Unroll the loop: [Retrieve -> Reason] x max_iterations
        for _ in range(max_iterations):
            multi_stream = (
                multi_stream
                .map(IterativeRetriever, parallelism=self.config.parallelism, top_k=3)
                .map(
                    IterativeReasoner,
                    parallelism=self.config.parallelism,
                    llm_base_url=self.config.llm_base_url,
                    llm_model=self.config.llm_model,
                    max_iterations=max_iterations,
                )
            )

        # Final synthesis
        (
            multi_stream
            .map(
                FinalSynthesizer,
                parallelism=self.config.parallelism,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
            )
            .sink(AdaptiveRAGResultSink, branch_name="MULTI", parallelism=1)
        )

        return self