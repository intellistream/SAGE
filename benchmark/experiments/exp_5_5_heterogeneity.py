import asyncio
import time

from sage.benchmark.benchmark_sage.experiments.base_experiment import BaseExperiment
from sage.benchmark.benchmark_sage.experiments.common import (
    BenchmarkClient,
    WorkloadGenerator,
)


class HeterogeneityExperiment(BaseExperiment):
    """
    Experiment for Heterogeneous Hardware Support.

    Demonstrates the system's ability to utilize CPU nodes for specific tasks
    (e.g., Embeddings) to offload GPUs for LLM tasks.
    """

    def _setup_impl(self) -> None:
        self.workload_generator = WorkloadGenerator(
            llm_ratio=self.config.workload.llm_ratio, seed=self.config.workload.seed
        )

    def _run_impl(self) -> None:
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        config = self.config
        workload = self.workload_generator

        # In a real run, this would target a specific gateway configuration.
        # Here we run the workload and the user is expected to have configured
        # the backend with CPU offloading enabled for Embeddings.

        requests_data = []
        for i in range(config.workload.total_requests):
            req_type, params = workload.generate_request(f"req-{i}")
            requests_data.append((req_type, params))

        arrival_times = workload.generate_arrival_times(
            config.workload.total_requests,
            config.workload.request_rate,
            config.workload.arrival_pattern,
        )

        async with BenchmarkClient(config.gateway_url) as client:
            tasks = []
            start_time = time.perf_counter()

            for i, (req_type, params) in enumerate(requests_data):
                target_time = start_time + arrival_times[i]
                now = time.perf_counter()
                if target_time > now:
                    await asyncio.sleep(target_time - now)

                req_id = f"req-{i}"
                if req_type == "llm":
                    task = asyncio.create_task(
                        client.send_llm_request(req_id, params["prompt"], config.llm_model.name)
                    )
                else:
                    task = asyncio.create_task(
                        client.send_embedding_request(
                            req_id, params["texts"], config.embedding_model.name
                        )
                    )
                tasks.append(task)

            self.results = await asyncio.gather(*tasks)

    def _teardown_impl(self) -> None:
        pass
