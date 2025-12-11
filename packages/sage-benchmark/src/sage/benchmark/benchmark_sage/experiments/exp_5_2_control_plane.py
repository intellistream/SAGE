import asyncio
import time

from sage.benchmark.benchmark_sage.experiments.base_experiment import BaseExperiment
from sage.benchmark.benchmark_sage.experiments.common import (
    BenchmarkClient,
    WorkloadGenerator,
)


class ControlPlaneExperiment(BaseExperiment):
    """
    Experiment for Control Plane Effectiveness.

    Evaluates the performance of the unified control plane under mixed workloads.
    """

    def _setup_impl(self) -> None:
        """Setup experiment."""
        self.workload_generator = WorkloadGenerator(
            llm_ratio=self.config.workload.llm_ratio, seed=self.config.workload.seed
        )

    def _run_impl(self) -> None:
        """Run the experiment workload."""
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        """Run async workload."""
        config = self.config
        workload = self.workload_generator

        # Generate requests
        requests_data = []
        for i in range(config.workload.total_requests):
            req_type, params = workload.generate_request(f"req-{i}")
            requests_data.append((req_type, params))

        # Generate arrival times
        arrival_times = workload.generate_arrival_times(
            config.workload.total_requests,
            config.workload.request_rate,
            config.workload.arrival_pattern,
        )

        async with BenchmarkClient(config.gateway_url) as client:
            tasks = []
            start_time = time.perf_counter()

            for i, (req_type, params) in enumerate(requests_data):
                # Wait for arrival time
                target_time = start_time + arrival_times[i]
                now = time.perf_counter()
                if target_time > now:
                    await asyncio.sleep(target_time - now)

                # Send request
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

            # Wait for all tasks
            self.results = await asyncio.gather(*tasks)

    def _run_warmup(self) -> None:
        """Run warmup requests."""
        asyncio.run(self._run_warmup_async())

    async def _run_warmup_async(self) -> None:
        """Run async warmup."""
        config = self.config
        workload = self.workload_generator

        async with BenchmarkClient(config.gateway_url) as client:
            tasks = []
            for i in range(config.workload.warmup_requests):
                req_type, params = workload.generate_request(f"warmup-{i}")
                if req_type == "llm":
                    tasks.append(
                        client.send_llm_request(
                            f"warmup-{i}", params["prompt"], config.llm_model.name
                        )
                    )
                else:
                    tasks.append(
                        client.send_embedding_request(
                            f"warmup-{i}", params["texts"], config.embedding_model.name
                        )
                    )

            await asyncio.gather(*tasks)

    def _teardown_impl(self) -> None:
        pass
