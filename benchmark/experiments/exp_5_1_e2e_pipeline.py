import asyncio
import random
import time

from sage.benchmark.benchmark_sage.experiments.base_experiment import (
    BaseExperiment,
)
from sage.benchmark.benchmark_sage.experiments.common import (
    BenchmarkClient,
    RequestResult,
)


class E2EPipelineExperiment(BaseExperiment):
    """
    Experiment for End-to-End Pipeline Performance.

    Simulates a RAG pipeline workload (Embed -> Retrieve -> Generate) to evaluate
    system performance under complex, multi-stage traffic patterns.
    """

    def _setup_impl(self) -> None:
        """Setup experiment."""
        pass

    def _run_impl(self) -> None:
        """Run the experiment workload."""
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        """Run async workload."""
        config = self.config

        # Simulate RAG Pipeline: Query -> Embed -> Retrieve (simulated) -> Generate
        # We simulate N concurrent users running this pipeline loop.

        async with BenchmarkClient(config.gateway_url) as client:
            tasks = []
            start_time = time.perf_counter()

            # Launch concurrent pipeline users
            # We use 'request_rate' to determine how many pipelines start per second

            arrival_times = self._generate_arrival_times(
                config.workload.total_requests, config.workload.request_rate
            )

            for i, arrival_time in enumerate(arrival_times):
                # Wait for arrival
                target_time = start_time + arrival_time
                now = time.perf_counter()
                if target_time > now:
                    await asyncio.sleep(target_time - now)

                # Start pipeline task
                task = asyncio.create_task(self._run_single_pipeline(client, f"pipe-{i}"))
                tasks.append(task)

            # Wait for all pipelines to complete
            results_list = await asyncio.gather(*tasks)

            # Flatten results (each pipeline returns multiple RequestResults)
            self.results = []
            for pipeline_results in results_list:
                self.results.extend(pipeline_results)

    async def _run_single_pipeline(
        self, client: BenchmarkClient, pipeline_id: str
    ) -> list[RequestResult]:
        """
        Run a single simulated RAG pipeline.

        Flow:
        1. Embedding Request (Query)
        2. Simulated Vector DB Retrieval (Sleep)
        3. LLM Request (Generation)
        """
        results = []

        # Step 1: Embedding
        emb_start = time.perf_counter()
        emb_res = await client.send_embedding_request(
            f"{pipeline_id}-step1-emb",
            ["Simulated user query for RAG pipeline"],
            self.config.embedding_model.name,
        )
        results.append(emb_res)

        if not emb_res.success:
            return results  # Stop if step 1 fails

        # Step 2: Simulated Retrieval (e.g., 50ms - 200ms latency)
        # We don't record a RequestResult for this internal step, but it affects timing
        retrieve_delay = random.uniform(0.05, 0.2)
        await asyncio.sleep(retrieve_delay)

        # Step 3: LLM Generation
        # Context is "retrieved" chunks + query
        prompt = "Context: ...retrieved data...\nQuery: Simulated query\nAnswer:"
        llm_res = await client.send_llm_request(
            f"{pipeline_id}-step3-llm", prompt, self.config.llm_model.name
        )
        results.append(llm_res)

        # Record End-to-End Pipeline Metric (as a special RequestResult)
        e2e_latency = (time.perf_counter() - emb_start) * 1000
        e2e_res = RequestResult(
            request_id=f"{pipeline_id}-e2e",
            request_type="pipeline_e2e",
            start_time=emb_start,
            end_time=time.perf_counter(),
            latency_ms=e2e_latency,
            success=llm_res.success,
            tokens_in=emb_res.tokens_in + llm_res.tokens_in,
            tokens_out=llm_res.tokens_out,
        )
        results.append(e2e_res)

        return results

    def _generate_arrival_times(self, n: int, rate: float) -> list[float]:
        import numpy as np

        # Poisson arrival
        intervals = np.random.exponential(1.0 / rate, n)
        return list(np.cumsum(intervals))

    def _run_warmup(self) -> None:
        pass  # Skip warmup for now or implement similar logic

    def _teardown_impl(self) -> None:
        pass
