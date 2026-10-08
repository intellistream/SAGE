from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sage.foundation import CustomLogger

from .local_backend import get_local_runtime_backend
from .pipeline_compiler import CompiledActorGraph, PipelineCompiler, _StreamingFlowHandle


@dataclass
class JobRecord:
    uuid: str
    env_name: str
    pipeline_size: int
    autostop: bool
    compiled_graph: CompiledActorGraph
    status: str = "created"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    handle: _StreamingFlowHandle | None = None
    error: str | None = None
    node_stop_signals: list[str] = field(default_factory=list)

    def mark_running(self, handle: _StreamingFlowHandle | None = None) -> None:
        self.started_at = time.time()
        self.handle = handle
        self.status = "running" if handle is not None else "stopped"
        if handle is None:
            self.completed_at = self.started_at

    def mark_stopped(self) -> None:
        self.status = "stopped"
        self.completed_at = time.time()

    def mark_failed(self, error: Exception | str) -> None:
        self.status = "failed"
        self.error = str(error)
        self.completed_at = time.time()

    def get_status(self) -> dict[str, Any]:
        return {
            "success": self.status != "failed",
            "uuid": self.uuid,
            "status": self.status,
            "env_name": self.env_name,
            "pipeline_size": self.pipeline_size,
            "autostop": self.autostop,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "running": bool(self.handle.is_running) if self.handle is not None else False,
            "node_stop_signals": list(self.node_stop_signals),
        }


class JobManager:
    """Main-repo owned lightweight local job orchestrator."""

    instance: JobManager | None = None
    instance_lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            with cls.instance_lock:
                if cls.instance is None:
                    cls.instance = super().__new__(cls)
                    cls.instance._initialized = False
        return cls.instance

    def __init__(self) -> None:
        with self.instance_lock:
            if self._initialized:
                return
            self._initialized = True
            self.jobs: dict[str, JobRecord] = {}
            self.deleted_jobs: dict[str, dict[str, Any]] = {}
            self.logger = CustomLogger(name="JobManager")

    def submit_job(self, env: Any, autostop: bool = False) -> str:
        job_uuid = str(uuid.uuid4())
        env.uuid = job_uuid
        env.env_uuid = job_uuid
        env.jobmanager_host = "local"
        env.jobmanager_port = 0

        compiler = PipelineCompiler()
        adapter = get_local_runtime_backend()
        compiled_graph = compiler.compile(env.pipeline, adapter)
        record = JobRecord(
            uuid=job_uuid,
            env_name=env.name,
            pipeline_size=len(env.pipeline),
            autostop=autostop,
            compiled_graph=compiled_graph,
        )
        self.jobs[job_uuid] = record

        try:
            result = compiled_graph.submit(autostop=autostop)
            if autostop:
                record.mark_running(None)
            else:
                record.mark_running(result)
            return job_uuid
        except Exception as exc:
            record.mark_failed(exc)
            raise

    def pause_job(self, env_uuid: str) -> dict[str, Any]:
        record = self.jobs.get(env_uuid)
        if record is None:
            return {
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found",
            }

        if record.handle is not None and record.handle.is_running:
            record.handle.stop()
        record.mark_stopped()
        return {
            "uuid": env_uuid,
            "status": "stopped",
            "message": "Job stopped successfully",
        }

    def get_job_status(self, env_uuid: str) -> dict[str, Any]:
        record = self.jobs.get(env_uuid)
        if record is None:
            return {
                "success": False,
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found",
            }
        if (
            record.handle is not None
            and not record.handle.is_running
            and record.status == "running"
        ):
            record.mark_stopped()
        return record.get_status()

    def receive_node_stop_signal(self, env_uuid: str, node_name: str) -> dict[str, Any]:
        record = self.jobs.get(env_uuid)
        if record is None:
            return {
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found",
            }
        record.node_stop_signals.append(node_name)
        return {
            "uuid": env_uuid,
            "status": "success",
            "message": f"Node stop signal received for {node_name}",
        }

    def list_jobs(self) -> list[dict[str, Any]]:
        return [record.get_status() for record in self.jobs.values()]

    def delete_job(self, env_uuid: str, force: bool = False) -> dict[str, Any]:
        record = self.jobs.get(env_uuid)
        if record is None:
            return {
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found",
            }
        if record.handle is not None and record.handle.is_running:
            if not force:
                return {
                    "uuid": env_uuid,
                    "status": "running",
                    "message": "Job is still running. Pass force=True to stop and delete it.",
                }
            record.handle.stop()
        record.mark_stopped()
        self.deleted_jobs[env_uuid] = record.get_status()
        del self.jobs[env_uuid]
        return {
            "uuid": env_uuid,
            "status": "deleted",
            "message": "Job deleted successfully",
        }

    def continue_job(self, env_uuid: str) -> dict[str, Any]:
        return {
            "uuid": env_uuid,
            "status": "unsupported",
            "message": "Lightweight in-process jobs cannot be resumed once stopped.",
        }

    def resume_job(self, env_uuid: str) -> dict[str, Any]:
        return self.continue_job(env_uuid)

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "jobs_count": len(self.jobs),
            "mode": "in-process",
        }

    def cleanup_all_jobs(self) -> dict[str, Any]:
        for env_uuid in list(self.jobs):
            self.delete_job(env_uuid, force=True)
        return {"status": "success", "message": "All jobs cleaned up"}

    def shutdown(self) -> None:
        self.cleanup_all_jobs()
        JobManager.instance = None

    @property
    def handle(self) -> JobManager:
        return self
