"""Main-repo owned runtime environment entrypoints."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from sage.runtime import backend as runtime_backend

from .base_environment import BaseEnvironment
from .job_manager import JobManager
from .pipeline_compiler import PipelineCompiler

if TYPE_CHECKING:
    from .pipeline_compiler import CompiledActorGraph, _StreamingFlowHandle


class LocalEnvironment(BaseEnvironment):
    """Local execution environment."""

    def __init__(
        self,
        name: str = "localenvironment",
        config: dict | None = None,
        scheduler=None,
        enable_monitoring: bool = False,
    ):
        super().__init__(
            name,
            config,
            platform="local",
            scheduler=scheduler,
            enable_monitoring=enable_monitoring,
        )
        self._engine_client = None

    def submit(self, autostop: bool = False):
        env_uuid = self.jobmanager.submit_job(self, autostop=autostop)
        self.env_uuid = env_uuid
        return env_uuid

    def _wait_for_completion(self):
        if not self.env_uuid:
            self.logger.warning("No environment UUID found, cannot wait for completion")
            return

        self.logger.info("Waiting for batch processing to complete...")
        self.logger.info(
            "⏳ Strategy: Wait for all data to be processed (not just source completion)"
        )

        max_wait_time = 12000.0
        start_time = time.time()
        check_interval = 1.0

        try:
            while time.time() - start_time < max_wait_time:
                status = self.jobmanager.get_job_status(self.env_uuid)
                if status["status"] in ["stopped", "failed", "not_found"]:
                    self.logger.info(
                        f"✅ Batch processing completed with status: {status['status']}"
                    )
                    break

                time.sleep(check_interval)

            else:
                self.logger.warning(
                    f"Timeout waiting for batch processing to complete after {max_wait_time}s"
                )
                try:
                    self.stop()
                except Exception as stop_error:  # noqa: BLE001
                    self.logger.error(f"Error stopping timed out job: {stop_error}")

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, stopping batch processing...")
            self.stop()
        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"Error waiting for completion: {exc}")
            try:
                self.stop()
            except Exception as stop_error:  # noqa: BLE001
                self.logger.error(f"Error stopping job after wait error: {stop_error}")
        finally:
            self.is_running = False

    @property
    def jobmanager(self) -> JobManager:
        if self._jobmanager is None:
            self._jobmanager = JobManager()

        return self._jobmanager

    def stop(self):
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to stop")
            return

        self.logger.info("Stopping pipeline...")
        try:
            response = self.jobmanager.pause_job(self.env_uuid)
            if response.get("status") in {"success", "stopped"}:
                self.is_running = False
                self.logger.info("Pipeline stopped successfully")
            else:
                self.logger.warning(f"Failed to stop pipeline: {response.get('message')}")
        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"Error stopping pipeline: {exc}")

    def close(self):
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to close")
            return

        self.logger.info("Closing environment...")
        try:
            response = self.jobmanager.pause_job(self.env_uuid)
            if response.get("status") in {"success", "stopped"}:
                self.logger.info("Environment closed successfully")
            else:
                self.logger.warning(f"Failed to close environment: {response.get('message')}")
        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"Error closing environment: {exc}")
        finally:
            self.is_running = False
            self.env_uuid = None
            self.pipeline.clear()


class FluttyEnvironment(BaseEnvironment):
    """Optional distributed execution environment backed by Flutty."""

    def __init__(
        self,
        name: str = "flutty_environment",
        config: dict | None = None,
        scheduler=None,
        placement_policy: str | None = None,
        enable_monitoring: bool = False,
    ) -> None:
        super().__init__(
            name,
            config,
            platform="flutty",
            scheduler=scheduler,
            enable_monitoring=enable_monitoring,
        )
        self._placement_policy: str | None = placement_policy
        self._compiled_graph: CompiledActorGraph | None = None
        self._streaming_handle: _StreamingFlowHandle | None = None

    def submit(self, autostop: bool = False) -> Any:
        adapter = runtime_backend.get_runtime_backend()
        compiler = PipelineCompiler()

        self.logger.info(
            f"[FluttyEnvironment:{self.name}] Compiling pipeline with {len(self.pipeline)} stage(s)…"
        )
        self._compiled_graph = compiler.compile(self.pipeline, adapter)

        self.logger.info(
            f"[FluttyEnvironment:{self.name}] Submitting "
            f"({'batch/autostop' if autostop else 'streaming'})…"
        )
        result = self._compiled_graph.submit(autostop=autostop)

        if not autostop:
            self._streaming_handle = result

        return result

    def stop(self) -> None:
        if self._streaming_handle is not None:
            self.logger.info(f"[FluttyEnvironment:{self.name}] Stopping streaming pipeline…")
            self._streaming_handle.stop()
            self._streaming_handle = None
        else:
            self.logger.info(
                f"[FluttyEnvironment:{self.name}] stop() called but no active streaming handle found — nothing to stop."
            )

    def close(self) -> None:
        self.stop()
        self._compiled_graph = None
        self.logger.info(f"[FluttyEnvironment:{self.name}] Closed.")

    def health_check(self) -> list[dict[str, Any]]:
        try:
            adapter = runtime_backend.get_runtime_backend()
            return adapter.list_nodes()
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(f"[FluttyEnvironment:{self.name}] health_check failed: {exc}")
            return []

    @property
    def is_running(self) -> bool:
        if self._streaming_handle is None:
            return False
        return self._streaming_handle.is_running

    @property
    def placement_policy(self) -> str | None:
        return self._placement_policy

    @placement_policy.setter
    def placement_policy(self, value: str | None) -> None:
        self._placement_policy = value

    def __repr__(self) -> str:
        state = "running" if self.is_running else "idle"
        return (
            f"FluttyEnvironment(name={self.name!r}, stages={len(self.pipeline)}, state={state!r})"
        )

    def __enter__(self) -> FluttyEnvironment:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


__all__ = ["LocalEnvironment", "FluttyEnvironment"]
