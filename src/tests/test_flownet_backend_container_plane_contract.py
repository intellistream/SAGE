from __future__ import annotations

from itertools import count
from typing import Any

from sage.runtime.flownet import (
    V1NodeRuntimeService,
    bootstrap_runtime,
    build_runtime_inspector,
)


class FakeBackendContainer:
    def __init__(
        self,
        backend_id: str,
        *,
        queue_capacity: int = 4,
        epoch: int = 7,
    ) -> None:
        self.backend_id = backend_id
        self._queue_capacity = int(queue_capacity)
        self._epoch = int(epoch)
        self._job_counter = count(1)
        self._jobs: dict[str, dict[str, Any]] = {}
        self.submitted_requests: list[dict[str, Any]] = []
        self.cancelled_jobs: dict[str, str] = {}
        self.acked_job_ids: list[str] = []

    def metrics(self) -> dict[str, Any]:
        active_jobs = len(self._jobs)
        return {
            "healthy": True,
            "schedulable": active_jobs < self._queue_capacity,
            "queue_depth": active_jobs,
            "queue_capacity": self._queue_capacity,
            "inflight": active_jobs,
            "epoch": self._epoch,
        }

    def heartbeat(self) -> dict[str, Any]:
        return self.metrics()

    def submit(self, request: dict[str, Any]) -> dict[str, Any]:
        job_id = f"{self.backend_id}-job-{next(self._job_counter)}"
        request_payload = dict(request)
        self.submitted_requests.append(request_payload)
        self._jobs[job_id] = {
            "request": request_payload,
            "status": "queued",
        }
        return {
            "job_id": job_id,
            "accepted": True,
        }

    def poll(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        job["status"] = "completed"
        return {
            "job_id": job_id,
            "status": "completed",
            "result": {
                "backend_id": self.backend_id,
                "request": dict(job["request"]),
            },
        }

    def cancel(self, job_id: str, *, reason: str = "") -> bool:
        if job_id not in self._jobs:
            return False
        self.cancelled_jobs[job_id] = str(reason or "")
        self._jobs.pop(job_id, None)
        return True

    def ack(self, job_id: str) -> bool:
        if job_id not in self._jobs:
            return False
        self._jobs.pop(job_id, None)
        self.acked_job_ids.append(job_id)
        return True


def _build_node_runtime(bootstrap):
    return V1NodeRuntimeService(
        runtime_host=bootstrap.runtime_host,
        node_id="node-backend-plane",
        node_address="127.0.0.1:18892",
    )


def test_backend_container_plane_supports_capability_selection_and_submit_poll_cancel() -> None:
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19461")
    try:
        runtime_host = bootstrap.runtime_host
        cpu_backend = FakeBackendContainer("fake-cpu-backend", queue_capacity=2, epoch=3)
        gpu_backend = FakeBackendContainer("fake-gpu-backend", queue_capacity=4, epoch=7)

        runtime_host.register_backend_container(
            cpu_backend,
            tags={"accelerator": "cpu", "zone": "az-a"},
            capabilities={
                "tasks": ["embed"],
                "models": ["embed-small"],
                "precision": "fp32",
            },
            metadata={"backend_type": "fake"},
        )
        runtime_host.register_backend_container(
            gpu_backend,
            tags={"accelerator": "gpu", "zone": "az-b"},
            capabilities={
                "tasks": ["chat", "embed"],
                "models": ["chat-large", "embed-small"],
                "precision": "fp16",
            },
            metadata={"backend_type": "fake"},
        )

        capability_selection = runtime_host.select_backend_container(
            required_capabilities={"tasks": "chat"},
        )
        assert capability_selection["backend_id"] == "fake-gpu-backend"

        tag_selection = runtime_host.select_backend_container(
            required_tags={"zone": "az-a"},
        )
        assert tag_selection["backend_id"] == "fake-cpu-backend"

        node_runtime = _build_node_runtime(bootstrap)
        inspector = build_runtime_inspector(
            runtime_host=runtime_host,
            node_control_call=node_runtime.node_control_call,
            default_node_address=node_runtime.node_address,
        )

        filtered_rows = inspector.list_runtime_backend_containers(
            required_capabilities={"models": "chat-large"},
        )
        assert [row["backend_id"] for row in filtered_rows] == ["fake-gpu-backend"]

        submit_response = inspector.submit_runtime_backend_job(
            request={"prompt": "hello backend plane", "request_epoch": 7},
            required_capabilities={"models": "chat-large"},
        )

        assert submit_response["backend_id"] == "fake-gpu-backend"
        assert gpu_backend.submitted_requests[-1]["prompt"] == "hello backend plane"
        assert gpu_backend.submitted_requests[-1]["backend_selection"]["required_capabilities"] == {
            "models": "chat-large"
        }

        telemetry = node_runtime.cluster_scheduler_metrics()
        assert telemetry["node"]["backend_count"] == 2
        assert telemetry["backends"]["queue_depth"] == 1
        assert telemetry["backends"]["inflight"] == 1
        assert telemetry["backends"]["inventory"]["capability_keys"] == [
            "models",
            "precision",
            "tasks",
        ]
        backend_row = next(
            row for row in telemetry["backends"]["records"] if row["backend_id"] == "fake-gpu-backend"
        )
        assert backend_row["capabilities"]["models"] == ["chat-large", "embed-small"]

        poll_response = inspector.poll_runtime_backend_job(
            submit_response["job_token"],
            auto_ack=True,
        )
        assert poll_response is not None
        assert poll_response["status"] == "completed"
        assert poll_response["result"]["backend_id"] == "fake-gpu-backend"
        assert gpu_backend.acked_job_ids == [submit_response["job_id"]]

        cancel_response = inspector.submit_runtime_backend_job(
            request={"prompt": "cancel me", "request_epoch": 3},
            required_tags={"zone": "az-a"},
        )
        assert inspector.cancel_runtime_backend_job(
            cancel_response["job_token"],
            reason="test-cancel",
        ) is True
        assert cpu_backend.cancelled_jobs[cancel_response["job_id"]] == "test-cancel"
    finally:
        bootstrap.shutdown()


def test_runtime_host_submit_backend_job_auto_polls_selected_backend() -> None:
    bootstrap = bootstrap_runtime(local_address="127.0.0.1:19462")
    try:
        runtime_host = bootstrap.runtime_host
        backend = FakeBackendContainer("fake-runtime-backend", queue_capacity=3, epoch=11)
        runtime_host.register_backend_container(
            backend,
            tags={"accelerator": "gpu", "zone": "az-c"},
            capabilities={
                "tasks": ["chat"],
                "models": ["chat-runtime"],
                "precision": "fp16",
            },
            metadata={"backend_type": "fake"},
        )

        future = runtime_host.submit_backend_job(
            request={"prompt": "runtime host path", "request_epoch": 11},
            required_capabilities={"tasks": "chat"},
        )
        result = future.result(timeout=5.0)

        assert result["status"] == "completed"
        assert result["result"]["backend_id"] == "fake-runtime-backend"
        assert backend.submitted_requests[-1]["backend_selection"]["selection_reason"] == "request_epoch_match"
        assert backend.acked_job_ids == [result["job_id"]]
    finally:
        bootstrap.shutdown()