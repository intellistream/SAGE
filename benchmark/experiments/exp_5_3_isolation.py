import asyncio
import time

from sage.benchmark.benchmark_sage.experiments.base_experiment import BaseExperiment
from sage.benchmark.benchmark_sage.experiments.common import BenchmarkClient, WorkloadGenerator


class IsolationExperiment(BaseExperiment):
    """
    Experiment for Multi-tenant Isolation and Fairness.

    Simulates a "noisy neighbor" scenario where a high-throughput batch workload
    competes with a latency-sensitive interactive workload.
    """

    def _setup_impl(self) -> None:
        # Generator for "Interactive" user (Latency sensitive)
        self.interactive_gen = WorkloadGenerator(llm_ratio=1.0, seed=42)
        # Generator for "Batch" user (Throughput focused)
        self.batch_gen = WorkloadGenerator(llm_ratio=0.5, seed=99)

    def _run_impl(self) -> None:
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        config = self.config

        # Scenario:
        # User A (Interactive): Low rate (e.g., 5 req/s), expects low latency.
        # User B (Batch): High rate (e.g., 50 req/s), floods the system.

        interactive_rate = 5.0
        batch_rate = config.workload.request_rate  # Main rate controls the noise level

        duration = 30  # seconds

        async with BenchmarkClient(config.gateway_url) as client:
            tasks = []

            # Launch Interactive User Loop
            tasks.append(
                asyncio.create_task(
                    self._run_user_loop(
                        client, "interactive", interactive_rate, duration, self.interactive_gen
                    )
                )
            )

            # Launch Batch User Loop
            tasks.append(
                asyncio.create_task(
                    self._run_user_loop(client, "batch", batch_rate, duration, self.batch_gen)
                )
            )

            results_list = await asyncio.gather(*tasks)

            self.results = []
            for user_results in results_list:
                self.results.extend(user_results)

    async def _run_user_loop(self, client, user_id, rate, duration, generator):
        results = []
        start_time = time.perf_counter()
        req_idx = 0

        while time.perf_counter() - start_time < duration:
            # Poisson arrival
            await asyncio.sleep(1.0 / rate)  # Simple constant rate for now to ensure pressure

            req_type, params = generator.generate_request(f"{user_id}-{req_idx}")

            # Add metadata to track which user this was
            # Note: In a real system, we'd pass a user-id header.

            if req_type == "llm":
                res = await client.send_llm_request(
                    f"{user_id}-{req_idx}", params["prompt"], self.config.llm_model.name
                )
            else:
                res = await client.send_embedding_request(
                    f"{user_id}-{req_idx}", params["texts"], self.config.embedding_model.name
                )

            # Tag result with user_id for analysis
            res.metadata["user_id"] = user_id
            results.append(res)
            req_idx += 1

        return results

    def _teardown_impl(self) -> None:
        pass
