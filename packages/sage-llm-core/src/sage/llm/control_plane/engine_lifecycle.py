# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Lifecycle management for vLLM engines managed by the control plane."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import aiohttp
import psutil

from sage.common.config.ports import SagePorts

if TYPE_CHECKING:
    from .manager import ControlPlaneManager

logger = logging.getLogger(__name__)


class EngineStatus(str, Enum):
    """Lifecycle states tracked for managed vLLM engines."""

    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class EngineRuntime(str, Enum):
    """Process runtime type managed by the lifecycle manager."""

    LLM = "llm"
    EMBEDDING = "embedding"


@dataclass
class EngineProcessInfo:
    """Bookkeeping structure for each managed engine instance."""

    engine_id: str
    model_id: str
    port: int
    gpu_ids: list[int]
    pid: int
    command: list[str]
    env_overrides: dict[str, str]
    runtime: EngineRuntime = EngineRuntime.LLM
    created_at: float = field(default_factory=time.time)
    status: EngineStatus = EngineStatus.STARTING
    stopped_at: float | None = None
    last_exit_code: int | None = None
    last_error: str | None = None


class EngineLifecycleManager:
    """Spawn, monitor, and stop vLLM engines for the control plane.

    This class manages the lifecycle of vLLM engine processes, including:
    - Spawning new engine processes
    - Health checking via HTTP endpoints
    - Graceful and forced shutdown
    - Optional registration with Control Plane for state tracking
    """

    # Maximum number of stopped/failed engines to keep in history
    MAX_STOPPED_ENGINES: int = 50

    def __init__(
        self,
        *,
        python_executable: str | None = None,
        host: str = "0.0.0.0",
        stop_timeout: float = 20.0,
        control_plane: ControlPlaneManager | None = None,
        max_stopped_engines: int | None = None,
    ) -> None:
        """Initialize the engine lifecycle manager.

        Args:
            python_executable: Path to Python executable for spawning engines.
            host: Default host address for engines.
            stop_timeout: Default timeout for stopping engines.
            control_plane: Optional reference to ControlPlaneManager for
                automatic engine registration and state updates.
            max_stopped_engines: Maximum number of stopped/failed engines to
                keep in history. Defaults to MAX_STOPPED_ENGINES (50).
        """
        self.python_executable = python_executable or sys.executable
        self.host = host
        self.stop_timeout = stop_timeout
        self._control_plane = control_plane
        self._max_stopped_engines = max_stopped_engines or self.MAX_STOPPED_ENGINES

        self._lock = threading.RLock()
        self._engines: dict[str, EngineProcessInfo] = {}
        self._reserved_ports: set[int] = set()

    @property
    def reserved_ports(self) -> set[int]:
        """Return a copy of currently reserved ports.

        This allows external components (like ControlPlaneManager) to check
        which ports are already reserved by the lifecycle manager when
        allocating new ports for engines.
        """
        with self._lock:
            return set(self._reserved_ports)

    def set_control_plane(self, control_plane: ControlPlaneManager | None) -> None:
        """Set the Control Plane reference for engine registration.

        Args:
            control_plane: The ControlPlaneManager to register engines with.
        """
        self._control_plane = control_plane

    # ------------------------------------------------------------------
    # Engine Discovery
    # ------------------------------------------------------------------
    def discover_running_engines(self) -> list[dict[str, Any]]:
        """Discover and register running vLLM/embedding engines on the system.

        Scans all running processes to find vLLM and embedding_server processes,
        extracts their configuration from command line arguments, and registers
        them with the lifecycle manager.

        Returns:
            List of discovered engine info dictionaries.
        """
        discovered: list[dict[str, Any]] = []

        # Get current user name for filtering (os.getlogin() can fail in some environments)
        current_user: str | None = None
        try:
            current_user = os.getlogin()
        except (OSError, FileNotFoundError):
            pass
        if not current_user:
            try:
                import pwd

                current_user = pwd.getpwuid(os.getuid()).pw_name
            except Exception:
                current_user = str(os.getuid())

        for proc in psutil.process_iter(["pid", "name", "cmdline", "username"]):
            try:
                # Filter by user ownership to avoid managing other users' processes
                proc_user = proc.info.get("username")
                if proc_user and current_user and proc_user != current_user:
                    continue

                cmdline = proc.info.get("cmdline") or []
                if not cmdline:
                    continue

                # Join cmdline for pattern matching
                cmd_str = " ".join(cmdline)

                # Check for vLLM engine
                if "vllm.entrypoints.openai.api_server" in cmd_str:
                    engine_info = self._parse_vllm_process(proc, cmdline)
                    if engine_info:
                        discovered.append(engine_info)

                # Check for embedding server
                elif "sage.common.components.sage_embedding.embedding_server" in cmd_str:
                    engine_info = self._parse_embedding_process(proc, cmdline)
                    if engine_info:
                        discovered.append(engine_info)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        logger.info("Discovered %d running engines", len(discovered))
        return discovered

    def _parse_vllm_process(
        self,
        proc: psutil.Process,
        cmdline: list[str],
    ) -> dict[str, Any] | None:
        """Parse a vLLM process and extract engine configuration."""
        try:
            model_id = self._extract_arg(cmdline, "--model")
            port_str = self._extract_arg(cmdline, "--port")
            host = self._extract_arg(cmdline, "--host") or "0.0.0.0"

            if not model_id or not port_str:
                return None

            port = int(port_str)
            pid = proc.pid
            username = proc.info.get("username", "unknown")

            # Check if already managed
            with self._lock:
                for info in self._engines.values():
                    if info.pid == pid:
                        logger.debug("Engine PID %d already managed", pid)
                        return None

            # Extract GPU info from environment
            env = proc.environ()
            cuda_devices = env.get("CUDA_VISIBLE_DEVICES", "")
            gpu_ids = [int(g) for g in cuda_devices.split(",") if g.strip().isdigit()]

            # Register the discovered engine
            engine_id = self._generate_engine_id(model_id)
            info = EngineProcessInfo(
                engine_id=engine_id,
                model_id=model_id,
                port=port,
                gpu_ids=gpu_ids,
                pid=pid,
                command=cmdline,
                env_overrides={"CUDA_VISIBLE_DEVICES": cuda_devices} if cuda_devices else {},
                runtime=EngineRuntime.LLM,
                status=EngineStatus.RUNNING,
            )

            with self._lock:
                self._engines[engine_id] = info
                self._reserved_ports.add(port)

            # Register with Control Plane
            if self._control_plane:
                try:
                    self._control_plane.register_engine(
                        engine_id=engine_id,
                        model_id=model_id,
                        host=host if host != "0.0.0.0" else "localhost",
                        port=port,
                        engine_kind="llm",
                        metadata={
                            "gpu_ids": gpu_ids,
                            "pid": pid,
                            "discovered": True,
                            "owner": username,
                        },
                    )
                except Exception as e:
                    logger.warning("Failed to register discovered engine %s: %s", engine_id, e)

            logger.info(
                "Discovered LLM engine: %s (model=%s, port=%d, pid=%d, owner=%s)",
                engine_id,
                model_id,
                port,
                pid,
                username,
            )

            return {
                "engine_id": engine_id,
                "model_id": model_id,
                "port": port,
                "pid": pid,
                "runtime": "llm",
                "gpu_ids": gpu_ids,
                "owner": username,
            }

        except Exception as e:
            logger.debug("Failed to parse vLLM process: %s", e)
            return None

    def _parse_embedding_process(
        self,
        proc: psutil.Process,
        cmdline: list[str],
    ) -> dict[str, Any] | None:
        """Parse an embedding server process and extract configuration."""
        try:
            model_id = self._extract_arg(cmdline, "--model")
            port_str = self._extract_arg(cmdline, "--port")
            host = self._extract_arg(cmdline, "--host") or "0.0.0.0"
            device = self._extract_arg(cmdline, "--device") or "cpu"

            if not model_id or not port_str:
                return None

            port = int(port_str)
            pid = proc.pid
            username = proc.info.get("username", "unknown")

            # Check if already managed
            with self._lock:
                for info in self._engines.values():
                    if info.pid == pid:
                        logger.debug("Engine PID %d already managed", pid)
                        return None

            # Determine GPU IDs
            gpu_ids: list[int] = []
            if device == "cuda":
                env = proc.environ()
                cuda_devices = env.get("CUDA_VISIBLE_DEVICES", "")
                gpu_ids = [int(g) for g in cuda_devices.split(",") if g.strip().isdigit()]

            # Register the discovered engine
            engine_id = self._generate_engine_id(model_id)
            info = EngineProcessInfo(
                engine_id=engine_id,
                model_id=model_id,
                port=port,
                gpu_ids=gpu_ids,
                pid=pid,
                command=cmdline,
                env_overrides={},
                runtime=EngineRuntime.EMBEDDING,
                status=EngineStatus.RUNNING,
            )

            with self._lock:
                self._engines[engine_id] = info
                self._reserved_ports.add(port)

            # Register with Control Plane
            if self._control_plane:
                try:
                    self._control_plane.register_engine(
                        engine_id=engine_id,
                        model_id=model_id,
                        host=host if host != "0.0.0.0" else "localhost",
                        port=port,
                        engine_kind="embedding",
                        metadata={
                            "gpu_ids": gpu_ids,
                            "pid": pid,
                            "device": device,
                            "discovered": True,
                            "owner": username,
                        },
                    )
                except Exception as e:
                    logger.warning("Failed to register discovered engine %s: %s", engine_id, e)

            logger.info(
                "Discovered embedding engine: %s (model=%s, port=%d, pid=%d, owner=%s)",
                engine_id,
                model_id,
                port,
                pid,
                username,
            )

            return {
                "engine_id": engine_id,
                "model_id": model_id,
                "port": port,
                "pid": pid,
                "runtime": "embedding",
                "gpu_ids": gpu_ids,
                "device": device,
                "owner": username,
            }

        except Exception as e:
            logger.debug("Failed to parse embedding process: %s", e)
            return None

    def _extract_arg(self, cmdline: list[str], arg_name: str) -> str | None:
        """Extract argument value from command line."""
        try:
            idx = cmdline.index(arg_name)
            if idx + 1 < len(cmdline):
                return cmdline[idx + 1]
        except ValueError:
            pass
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def spawn_engine(
        self,
        model_id: str,
        gpu_ids: list[int],
        port: int | None = None,
        *,
        tensor_parallel_size: int = 1,
        pipeline_parallel_size: int = 1,
        extra_args: list[str] | None = None,
        engine_kind: EngineRuntime = EngineRuntime.LLM,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Launch a vLLM OpenAI-compatible server and register it.

        Args:
            model_id: The model to load.
            gpu_ids: List of GPU device IDs to use.
            port: Optional specific port (auto-select if None).
            tensor_parallel_size: Tensor parallelism degree.
            pipeline_parallel_size: Pipeline parallelism degree.
            extra_args: Additional CLI arguments.
            engine_kind: Type of engine (LLM or EMBEDDING).
            metadata: Optional metadata for engine registration.

        Returns:
            The engine_id of the spawned engine.
        """

        extra_args = list(extra_args or [])
        with self._lock:
            resolved_port = self._reserve_port(port)
            engine_id = self._generate_engine_id(model_id)
            command = self._build_engine_command(
                engine_kind,
                model_id,
                resolved_port,
                tensor_parallel_size,
                pipeline_parallel_size,
                extra_args,
                gpu_ids=gpu_ids,
            )
            env = self._build_environment(gpu_ids)

            logger.info(
                "Spawning %s engine %s (model=%s, port=%s, gpus=%s)",
                engine_kind.value,
                engine_id,
                model_id,
                resolved_port,
                ",".join(str(gpu) for gpu in gpu_ids) or "CPU",
            )

            try:
                process = subprocess.Popen(
                    command,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    start_new_session=True,
                )
            except Exception:
                self._reserved_ports.discard(resolved_port)
                logger.exception("Failed to spawn vLLM engine for %s", model_id)
                raise

            info = EngineProcessInfo(
                engine_id=engine_id,
                model_id=model_id,
                port=resolved_port,
                gpu_ids=list(gpu_ids),
                pid=process.pid,
                command=command,
                env_overrides=self._extract_env_overrides(env),
                runtime=engine_kind,
            )
            self._engines[engine_id] = info
            self._reserved_ports.add(resolved_port)
            logger.debug("Engine %s registered with PID %d", engine_id, process.pid)

            # Auto-register with Control Plane if available
            if self._control_plane:
                try:
                    engine_metadata = dict(metadata) if metadata else {}
                    engine_metadata.update(
                        {
                            "gpu_ids": list(gpu_ids),
                            "tensor_parallel_size": tensor_parallel_size,
                            "pipeline_parallel_size": pipeline_parallel_size,
                            "pid": process.pid,
                        }
                    )
                    self._control_plane.register_engine(
                        engine_id=engine_id,
                        model_id=model_id,
                        host=self.host if self.host != "0.0.0.0" else "localhost",
                        port=resolved_port,
                        engine_kind=engine_kind.value,
                        metadata=engine_metadata,
                    )
                    logger.debug(
                        "Engine %s auto-registered with Control Plane",
                        engine_id,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to auto-register engine %s with Control Plane: %s",
                        engine_id,
                        e,
                    )

            return engine_id

    def stop_engine(
        self,
        engine_id: str,
        *,
        timeout: float | None = None,
        drain: bool = False,
    ) -> bool:
        """Stop a managed engine by sending SIGTERM followed by SIGKILL if needed.

        Args:
            engine_id: The ID of the engine to stop.
            timeout: Timeout for graceful shutdown. Defaults to stop_timeout.
            drain: If True and Control Plane is available, initiate graceful
                draining before stopping.

        Returns:
            True if engine was stopped successfully, False otherwise.
        """
        with self._lock:
            info = self._engines.get(engine_id)
            if info is None:
                logger.warning("Requested stop for unknown engine %s", engine_id)
                return False
            info.status = EngineStatus.STOPPING

        # Notify Control Plane of state change if drain requested
        if drain and self._control_plane:
            try:
                self._control_plane.start_engine_drain(engine_id)
            except Exception as e:
                logger.warning(
                    "Failed to start drain for engine %s: %s",
                    engine_id,
                    e,
                )

        process = self._get_process(info.pid)
        if process is None:
            logger.info("Engine %s already stopped", engine_id)
            self._finalize_engine(info, EngineStatus.STOPPED)
            self._notify_control_plane_stopped(engine_id)
            return True

        success = self._terminate_process(process, timeout or self.stop_timeout)
        with self._lock:
            new_status = EngineStatus.STOPPED if success else EngineStatus.FAILED
            self._finalize_engine(info, new_status)

        self._notify_control_plane_stopped(engine_id, success=success)
        return success

    def _notify_control_plane_stopped(
        self,
        engine_id: str,
        success: bool = True,
    ) -> None:
        """Notify Control Plane that an engine has stopped."""
        if not self._control_plane:
            return
        try:
            from .types import EngineState

            new_state = EngineState.STOPPED if success else EngineState.ERROR
            self._control_plane.update_engine_state(engine_id, new_state)
        except Exception as e:
            logger.debug(
                "Failed to notify Control Plane of engine %s stop: %s",
                engine_id,
                e,
            )

    def get_engine_status(self, engine_id: str) -> dict[str, Any]:
        """Return runtime metadata for the specified engine."""

        with self._lock:
            info = self._engines.get(engine_id)
            if info is None:
                raise KeyError(f"Engine '{engine_id}' not found")
            status = self._refresh_status(info)
            return self._serialize(info, status)

    def list_engines(self) -> list[dict[str, Any]]:
        """Return status objects for all tracked engines."""

        with self._lock:
            return [
                self._serialize(info, self._refresh_status(info)) for info in self._engines.values()
            ]

    # ------------------------------------------------------------------
    # Health Check API
    # ------------------------------------------------------------------
    async def health_check(
        self,
        engine_id: str,
        timeout: float = 5.0,
    ) -> bool:
        """HTTP check engine health status.

        For LLM engines: GET /health or /v1/models
        For Embedding engines: GET /health

        When Control Plane is configured, this method will automatically:
        - Record a heartbeat on successful health check
        - Record a failure on failed health check (triggers ERROR state
          after consecutive failures threshold)

        Note: STARTING engines are given a grace period (default 120s for LLM,
        60s for embedding) during which health check failures do not count
        towards the consecutive failures threshold.

        Args:
            engine_id: The engine identifier to check
            timeout: HTTP request timeout in seconds

        Returns:
            True if engine is healthy, False otherwise
        """
        with self._lock:
            info = self._engines.get(engine_id)
            if info is None:
                logger.warning("Health check for unknown engine %s", engine_id)
                return False

            # If engine is in terminal state, it's not healthy
            if info.status in {EngineStatus.STOPPED, EngineStatus.FAILED}:
                return False

            # First check if process is alive
            process = self._get_process(info.pid)
            if process is None or not process.is_running():
                logger.debug("Engine %s process not running", engine_id)
                self._notify_health_check_result(engine_id, is_healthy=False)
                return False

            port = info.port
            runtime = info.runtime
            engine_status = info.status
            engine_created_at = info.created_at

        # Perform HTTP health check
        is_healthy = await self._http_health_check(engine_id, port, runtime, timeout)

        # Determine if engine is still in startup grace period
        # LLM engines may take up to 120s to load, embedding up to 60s
        grace_period = 120.0 if runtime != EngineRuntime.EMBEDDING else 60.0
        time_since_start = time.time() - engine_created_at
        in_grace_period = time_since_start < grace_period

        # Notify Control Plane of health check result
        # BUT: if engine is in STARTING status and within grace period,
        # don't count failures towards the error threshold
        if is_healthy:
            self._notify_health_check_result(engine_id, is_healthy=True)
            # Transition from STARTING to RUNNING on first successful health check
            if engine_status == EngineStatus.STARTING:
                with self._lock:
                    if engine_id in self._engines:
                        self._engines[engine_id].status = EngineStatus.RUNNING
                        logger.info("Engine %s transitioned to RUNNING", engine_id)
        elif not in_grace_period:
            # Only record failure if outside grace period
            self._notify_health_check_result(engine_id, is_healthy=False)
        else:
            # In grace period and not healthy yet - just log, don't penalize
            logger.debug(
                "Engine %s not ready yet (%.1fs since start, grace period %.1fs)",
                engine_id,
                time_since_start,
                grace_period,
            )
            # IMPORTANT: Return True during grace period to prevent auto-restart
            # from triggering before the engine has a chance to start
            return True

        return is_healthy

    def _notify_health_check_result(
        self,
        engine_id: str,
        is_healthy: bool,
    ) -> None:
        """Notify Control Plane of health check result."""
        if not self._control_plane:
            return

        try:
            if is_healthy:
                self._control_plane.record_engine_heartbeat(engine_id)
            else:
                self._control_plane.record_engine_failure(engine_id)
        except Exception as e:
            logger.debug(
                "Failed to notify Control Plane of health check for %s: %s",
                engine_id,
                e,
            )

    async def _http_health_check(
        self,
        engine_id: str,
        port: int,
        runtime: EngineRuntime,
        timeout: float,
    ) -> bool:
        """Perform HTTP health check against an engine endpoint."""
        # Determine health check endpoints based on engine type
        if runtime == EngineRuntime.EMBEDDING:
            endpoints = ["/health"]
        else:
            # LLM: Try /health first, then /v1/models as fallback
            endpoints = ["/health", "/v1/models"]

        base_url = f"http://{self.host}:{port}"
        # Use localhost for health checks since we're checking from the same machine
        if self.host == "0.0.0.0":
            base_url = f"http://127.0.0.1:{port}"

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                for endpoint in endpoints:
                    url = f"{base_url}{endpoint}"
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                logger.debug(
                                    "Engine %s healthy (endpoint=%s)",
                                    engine_id,
                                    endpoint,
                                )
                                return True
                    except aiohttp.ClientError:
                        # Try next endpoint
                        continue

                logger.debug("Engine %s failed all health check endpoints", engine_id)
                return False

        except TimeoutError:
            logger.debug("Engine %s health check timed out", engine_id)
            return False
        except Exception as e:
            logger.debug("Engine %s health check error: %s", engine_id, e)
            return False

    async def health_check_all(self) -> dict[str, bool]:
        """Check health status of all managed engines.

        Only checks engines that are in RUNNING or STARTING state.
        Engines that are STOPPED or FAILED are skipped to avoid
        triggering unnecessary restart attempts.

        Returns:
            Dictionary mapping engine_id to health status (True/False)
        """
        with self._lock:
            # Only check engines that are expected to be running
            engine_ids = [
                eid
                for eid, info in self._engines.items()
                if info.status in {EngineStatus.RUNNING, EngineStatus.STARTING}
            ]

        if not engine_ids:
            return {}

        # Run health checks concurrently
        tasks = [self.health_check(engine_id) for engine_id in engine_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_status: dict[str, bool] = {}
        for engine_id, result in zip(engine_ids, results, strict=False):
            if isinstance(result, Exception):
                logger.error("Health check failed for engine %s: %s", engine_id, result)
                health_status[engine_id] = False
            elif isinstance(result, bool):
                health_status[engine_id] = result
            else:
                # Unexpected result type, treat as unhealthy
                health_status[engine_id] = False

        return health_status

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _generate_engine_id(self, model_id: str) -> str:
        suffix = uuid.uuid4().hex[:8]
        sanitized = model_id.split("/")[-1].replace(" ", "-").replace(".", "-")
        return f"engine-{sanitized.lower()}-{suffix}"

    def _build_engine_command(
        self,
        engine_kind: EngineRuntime,
        model_id: str,
        port: int,
        tensor_parallel_size: int,
        pipeline_parallel_size: int,
        extra_args: list[str],
        gpu_ids: list[int] | None = None,
    ) -> list[str]:
        if engine_kind == EngineRuntime.EMBEDDING:
            return self._build_embedding_command(model_id, port, extra_args, gpu_ids=gpu_ids)
        return self._build_llm_command(
            model_id,
            port,
            tensor_parallel_size,
            pipeline_parallel_size,
            extra_args,
            gpu_ids=gpu_ids,
        )

    def _build_llm_command(
        self,
        model_id: str,
        port: int,
        tensor_parallel_size: int,
        pipeline_parallel_size: int,
        extra_args: list[str],
        *,
        gpu_ids: list[int] | None = None,
    ) -> list[str]:
        command = [
            self.python_executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            model_id,
            "--host",
            self.host,
            "--port",
            str(port),
        ]
        command.extend(["--tensor-parallel-size", str(tensor_parallel_size)])
        command.extend(["--pipeline-parallel-size", str(pipeline_parallel_size)])

        # Auto-calculate gpu-memory-utilization based on available GPU memory
        if gpu_ids:
            gpu_mem_util = self._calculate_gpu_memory_utilization(gpu_ids)
            if gpu_mem_util is not None:
                command.extend(["--gpu-memory-utilization", str(gpu_mem_util)])

        command.extend(extra_args)
        return command

    def _calculate_gpu_memory_utilization(self, gpu_ids: list[int]) -> float | None:
        """Calculate safe GPU memory utilization based on available memory.

        vLLM calculates memory as: total_memory * gpu_memory_utilization
        We need to ensure this doesn't exceed available free memory.
        """
        try:
            import torch

            if not torch.cuda.is_available():
                return None

            min_free_ratio = 1.0
            for gpu_id in gpu_ids:
                if gpu_id >= torch.cuda.device_count():
                    continue
                props = torch.cuda.get_device_properties(gpu_id)
                total_mem = props.total_memory
                # Get free memory (this requires setting CUDA_VISIBLE_DEVICES first)
                # Use nvidia-smi instead for accurate free memory
                free_mem = self._get_gpu_free_memory(gpu_id)
                if free_mem is not None and total_mem > 0:
                    free_ratio = free_mem / total_mem
                    min_free_ratio = min(min_free_ratio, free_ratio)

            # Use 80% of available free memory to leave some headroom
            safe_utilization = min_free_ratio * 0.8
            # Clamp to reasonable range
            return max(0.05, min(0.95, safe_utilization))
        except Exception:
            return None

    def _get_gpu_free_memory(self, gpu_id: int) -> int | None:
        """Get free GPU memory in bytes using nvidia-smi."""
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.free",
                    "--format=csv,noheader,nounits",
                    f"--id={gpu_id}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                free_mib = int(result.stdout.strip())
                return free_mib * 1024 * 1024  # Convert MiB to bytes
        except Exception:
            pass
        return None

    def _build_embedding_command(
        self,
        model_id: str,
        port: int,
        extra_args: list[str],
        *,
        gpu_ids: list[int] | None = None,
    ) -> list[str]:
        command = [
            self.python_executable,
            "-m",
            "sage.common.components.sage_embedding.embedding_server",
            "--model",
            model_id,
            "--host",
            self.host,
            "--port",
            str(port),
        ]
        # Add device parameter based on GPU allocation
        if gpu_ids:
            command.extend(["--device", "cuda"])
        else:
            command.extend(["--device", "cpu"])
        command.extend(extra_args)
        return command

    def _build_environment(self, gpu_ids: list[int]) -> dict[str, str]:
        env = os.environ.copy()
        if gpu_ids:
            env["CUDA_VISIBLE_DEVICES"] = ",".join(str(gpu) for gpu in gpu_ids)
        else:
            env.pop("CUDA_VISIBLE_DEVICES", None)

        # Clear proxy environment variables to avoid SOCKS dependency issues
        # when loading models from HuggingFace mirror (which doesn't need proxy)
        for proxy_var in (
            "all_proxy",
            "ALL_PROXY",
            "http_proxy",
            "HTTP_PROXY",
            "https_proxy",
            "HTTPS_PROXY",
        ):
            env.pop(proxy_var, None)

        return env

    def _extract_env_overrides(self, env: dict[str, str]) -> dict[str, str]:
        overrides = {}
        for key in ("CUDA_VISIBLE_DEVICES",):
            if key in env:
                overrides[key] = env[key]
        return overrides

    def _reserve_port(self, requested: int | None) -> int:
        if requested is not None:
            self._validate_port(requested)
            return requested

        candidates = [SagePorts.get_recommended_llm_port(), *SagePorts.get_llm_ports()]
        seen: set[int] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            try:
                self._validate_port(candidate)
                return candidate
            except ValueError:
                continue

        fallback = SagePorts.find_available_port()
        if fallback is None:
            raise RuntimeError("No available port for spawning engine")
        return fallback

    def _validate_port(self, port: int) -> None:
        if port in self._reserved_ports:
            raise ValueError(f"Port {port} already reserved by control plane")
        if not SagePorts.is_available(port):
            raise ValueError(f"Port {port} is already in use")

    def _get_process(self, pid: int) -> psutil.Process | None:
        try:
            process = psutil.Process(pid)
        except psutil.Error:
            return None
        return process

    def _terminate_process(self, process: psutil.Process, timeout: float) -> bool:
        try:
            process.terminate()
            process.wait(timeout=timeout)
            logger.info("Engine PID %d stopped gracefully", process.pid)
            return True
        except psutil.TimeoutExpired:
            logger.warning(
                "Engine PID %d did not stop in %.1fs; force killing",
                process.pid,
                timeout,
            )
            try:
                process.kill()
                process.wait(timeout=5)
                return True
            except psutil.Error as exc:
                logger.error("Failed to kill engine PID %d: %s", process.pid, exc)
                return False
        except psutil.NoSuchProcess:
            return True
        except psutil.Error as exc:
            logger.error("Error while stopping engine PID %d: %s", process.pid, exc)
            return False

    def _refresh_status(self, info: EngineProcessInfo) -> EngineStatus:
        if info.status in {EngineStatus.STOPPED, EngineStatus.FAILED}:
            return info.status

        process = self._get_process(info.pid)
        if process is None:
            info.last_exit_code = info.last_exit_code or -1
            self._finalize_engine(info, EngineStatus.FAILED)
            return info.status

        if process.is_running():
            info.status = EngineStatus.RUNNING
            return info.status

        try:
            exit_code = process.wait(timeout=0)
        except (psutil.TimeoutExpired, psutil.Error):
            exit_code = None

        info.last_exit_code = exit_code
        final_status = EngineStatus.STOPPED if (exit_code or 0) == 0 else EngineStatus.FAILED
        self._finalize_engine(info, final_status)
        return info.status

    def _finalize_engine(self, info: EngineProcessInfo, status: EngineStatus) -> None:
        info.status = status
        if info.stopped_at is None and status in {EngineStatus.STOPPED, EngineStatus.FAILED}:
            info.stopped_at = time.time()
        self._reserved_ports.discard(info.port)
        # Clean up old stopped engines to prevent memory accumulation
        self._cleanup_old_engines()

    def _cleanup_old_engines(self) -> None:
        """Remove oldest stopped/failed engines if over the limit.

        This prevents unbounded memory growth when engines are restarted
        frequently. Only STOPPED and FAILED engines are candidates for
        cleanup; RUNNING/STARTING engines are never removed.
        """
        stopped_engines: list[tuple[str, float]] = []
        for eid, info in self._engines.items():
            if info.status in {EngineStatus.STOPPED, EngineStatus.FAILED}:
                # Use stopped_at time, or created_at if not set
                stop_time = info.stopped_at or info.created_at
                stopped_engines.append((eid, stop_time))

        # If under limit, nothing to do
        if len(stopped_engines) <= self._max_stopped_engines:
            return

        # Sort by stop time (oldest first) and remove excess
        stopped_engines.sort(key=lambda x: x[1])
        to_remove = len(stopped_engines) - self._max_stopped_engines
        for eid, _ in stopped_engines[:to_remove]:
            del self._engines[eid]
            logger.debug("Cleaned up old engine record: %s", eid)

    def prune_stopped_engines(self) -> int:
        """Remove all STOPPED/FAILED engine records from the registry.

        Unlike _cleanup_old_engines() which keeps a minimum number of stopped
        engines, this method removes ALL stopped/failed engines.

        Returns:
            Number of engine records removed.
        """
        to_remove = []
        with self._lock:
            for eid, info in self._engines.items():
                if info.status in {EngineStatus.STOPPED, EngineStatus.FAILED}:
                    to_remove.append(eid)
            for eid in to_remove:
                del self._engines[eid]
        if to_remove:
            logger.info("Pruned %d stopped/failed engine records", len(to_remove))
        return len(to_remove)

    def _serialize(self, info: EngineProcessInfo, status: EngineStatus) -> dict[str, Any]:
        uptime = (info.stopped_at or time.time()) - info.created_at
        return {
            "engine_id": info.engine_id,
            "model_id": info.model_id,
            "port": info.port,
            "gpu_ids": info.gpu_ids,
            "pid": info.pid,
            "status": status.value,
            "runtime": info.runtime.value,
            "uptime_seconds": max(uptime, 0.0),
            "command": info.command,
            "env": info.env_overrides,
            "last_exit_code": info.last_exit_code,
        }


__all__ = [
    "EngineLifecycleManager",
    "EngineProcessInfo",
    "EngineRuntime",
    "EngineStatus",
]
