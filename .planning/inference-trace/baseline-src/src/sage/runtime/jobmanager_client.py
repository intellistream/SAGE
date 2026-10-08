from __future__ import annotations

import base64
import time
import uuid
from typing import Any

from .base_tcp_client import BaseTcpClient


class JobManagerClient(BaseTcpClient):
    """Runtime-local JobManager client for serialized job submission."""

    def __init__(self, host: str = "127.0.0.1", port: int = 19001, timeout: float = 600.0):
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
        if timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {timeout}")

        super().__init__(host, port, timeout, "JobManagerClient")

    def _build_health_check_request(self) -> dict[str, Any]:
        return {"action": "health_check", "request_id": str(uuid.uuid4())}

    def _build_server_info_request(self) -> dict[str, Any]:
        return {"action": "get_server_info", "request_id": str(uuid.uuid4())}

    def submit_job(
        self,
        serialized_data: bytes,
        autostop: bool = False,
        extra_python_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        if serialized_data is None:
            raise ValueError("Serialized data cannot be None")
        if isinstance(serialized_data, bytes) and len(serialized_data) == 0:
            raise ValueError("Serialized data cannot be empty")

        request = {
            "action": "submit_job",
            "request_id": str(uuid.uuid4()),
            "serialized_data": base64.b64encode(serialized_data).decode("utf-8"),
            "autostop": autostop,
            "extra_python_paths": extra_python_paths or [],
        }
        return self.send_request(request)

    def pause_job(self, job_uuid: str) -> dict[str, Any]:
        if job_uuid is None:
            raise ValueError("Job UUID cannot be None")
        if job_uuid == "":
            raise ValueError("Job UUID cannot be empty")
        return self.send_request(
            {"action": "pause_job", "request_id": str(uuid.uuid4()), "job_uuid": job_uuid}
        )

    def get_job_status(self, job_uuid: str) -> dict[str, Any]:
        return self.send_request(
            {"action": "get_job_status", "request_id": str(uuid.uuid4()), "job_uuid": job_uuid}
        )

    def health_check(self) -> dict[str, Any]:
        return self.send_request(self._build_health_check_request())

    def get_server_info(self) -> dict[str, Any]:
        return self.send_request(self._build_server_info_request())

    def list_jobs(self) -> dict[str, Any]:
        return self.send_request({"action": "list_jobs", "request_id": str(uuid.uuid4())})

    def continue_job(self, job_uuid: str) -> dict[str, Any]:
        return self.send_request(
            {"action": "continue_job", "request_id": str(uuid.uuid4()), "job_uuid": job_uuid}
        )

    def delete_job(self, job_uuid: str, force: bool = False) -> dict[str, Any]:
        return self.send_request(
            {
                "action": "delete_job",
                "request_id": str(uuid.uuid4()),
                "job_uuid": job_uuid,
                "force": force,
            }
        )

    def receive_node_stop_signal(self, job_uuid: str, node_name: str) -> dict[str, Any]:
        return self.send_request(
            {
                "action": "receive_node_stop_signal",
                "request_id": str(uuid.uuid4()),
                "job_uuid": job_uuid,
                "node_name": node_name,
            }
        )

    def cleanup_all_jobs(self) -> dict[str, Any]:
        return self.send_request({"action": "cleanup_all_jobs", "request_id": str(uuid.uuid4())})

    def _retry_request(self, request: dict[str, Any], max_retries: int = 3) -> dict[str, Any]:
        last_exception = None
        for attempt in range(max_retries):
            try:
                return self.send_request(request)
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise last_exception  # noqa: B904
        raise last_exception if last_exception else RuntimeError("Retry failed")
