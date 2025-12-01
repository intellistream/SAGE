"""OpenAI-compatible API Server Service for sageLLM

Provides a managed LLM API server that can be started, stopped,
and monitored programmatically.

Supports multiple backends:
- vLLM (default, high performance)
- Ollama (future)
- LMDeploy (future)
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Literal

import psutil
import requests

from sage.common.config.ports import SagePorts
from sage.common.utils.logging import get_logger

logger = get_logger(__name__)


class LLMServerConfig:
    """Configuration for LLM API Server

    Supports multiple backends through a unified interface.
    Backend-specific options can be passed via extra_args.
    """

    def __init__(
        self,
        model: str,
        backend: Literal["vllm", "ollama", "lmdeploy"] = "vllm",
        host: str = "0.0.0.0",
        port: int | None = None,
        gpu_memory_utilization: float = 0.7,
        max_model_len: int = 4096,
        tensor_parallel_size: int = 1,
        disable_log_stats: bool = True,
        **kwargs: Any,
    ):
        """Initialize LLM server configuration

        Args:
            model: Model name or path
            backend: Inference backend ("vllm", "ollama", "lmdeploy")
            host: Server host
            port: Server port (default: SagePorts.BENCHMARK_LLM = 8901)
            gpu_memory_utilization: GPU memory utilization (default 0.7 for consumer GPUs)
            max_model_len: Maximum model sequence length
            tensor_parallel_size: Number of GPUs for tensor parallelism
            disable_log_stats: Disable logging statistics (vLLM specific)
            **kwargs: Backend-specific arguments
        """
        self.model = model
        self.backend = backend
        self.host = host
        self.port = port if port is not None else SagePorts.BENCHMARK_LLM
        self.gpu_memory_utilization = gpu_memory_utilization
        self.max_model_len = max_model_len
        self.tensor_parallel_size = tensor_parallel_size
        self.disable_log_stats = disable_log_stats
        self.extra_args = kwargs


class LLMAPIServer:
    """Managed LLM API Server with OpenAI-compatible interface

    Provides lifecycle management for LLM inference servers.
    Supports multiple backends (vLLM, Ollama, LMDeploy) through a unified interface.

    Example:
        ```python
        from sage.common.components.sage_llm import LLMAPIServer, LLMServerConfig

        # vLLM backend (default)
        config = LLMServerConfig(
            model="Qwen/Qwen2.5-0.5B-Instruct",
            backend="vllm",
            # port defaults to SagePorts.LLM_DEFAULT (8001)
            gpu_memory_utilization=0.9,
        )

        server = LLMAPIServer(config)
        server.start()  # Blocks until server is ready

        # Server is now running at http://localhost:8001
        # OpenAI API at http://localhost:8001/v1/completions

        server.stop()
        ```
    """

    def __init__(self, config: LLMServerConfig):
        self.config = config
        self.process: subprocess.Popen | None = None
        self.pid: int | None = None
        self.log_file: Path | None = None

    def start(self, background: bool = True, log_file: Path | None = None) -> bool:
        """Start the LLM API server

        Args:
            background: If True, run in background (daemon mode)
            log_file: Path to log file (default: ~/.sage/logs/llm_api_server_{port}.log)

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running():
            logger.warning(f"LLM API server already running on port {self.config.port}")
            return True

        # Prepare log file
        if log_file is None:
            log_dir = Path.home() / ".sage" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"llm_api_server_{self.config.port}.log"
        self.log_file = log_file

        # Build command based on backend
        cmd = self._build_command()
        if cmd is None:
            logger.error(f"Unsupported backend: {self.config.backend}")
            return False

        logger.info(f"Starting LLM API server ({self.config.backend}): {' '.join(cmd)}")

        try:
            # Start process
            if background:
                # Background mode - redirect output to log file
                log_handle = open(self.log_file, "w")
                self.process = subprocess.Popen(
                    cmd,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid if os.name != "nt" else None,
                )
                self.pid = self.process.pid
                logger.info(f"LLM API server started in background (PID: {self.pid})")
                logger.info(f"Logs: {self.log_file}")

                # Wait for server to be ready
                return self._wait_for_ready(timeout=120)
            else:
                # Foreground mode - blocking
                self.process = subprocess.Popen(cmd)
                self.pid = self.process.pid
                logger.info(f"LLM API server started in foreground (PID: {self.pid})")
                self.process.wait()
                return True

        except Exception as exc:
            logger.error(f"Failed to start LLM API server: {exc}")
            return False

    def _build_command(self) -> list[str] | None:
        """Build command for specific backend

        Returns:
            Command list, or None if backend not supported
        """
        if self.config.backend == "vllm":
            return self._build_vllm_command()
        elif self.config.backend == "ollama":
            # TODO: Implement Ollama backend
            logger.warning("Ollama backend not yet implemented")
            return None
        elif self.config.backend == "lmdeploy":
            # TODO: Implement LMDeploy backend
            logger.warning("LMDeploy backend not yet implemented")
            return None
        else:
            return None

    def _build_vllm_command(self) -> list[str]:
        """Build command for vLLM backend"""
        cmd = [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            self.config.model,
            "--host",
            self.config.host,
            "--port",
            str(self.config.port),
            "--gpu-memory-utilization",
            str(self.config.gpu_memory_utilization),
            "--max-model-len",
            str(self.config.max_model_len),
        ]

        # Add tensor parallel if > 1
        if self.config.tensor_parallel_size > 1:
            cmd.extend(["--tensor-parallel-size", str(self.config.tensor_parallel_size)])

        # Add disable log stats flag
        if self.config.disable_log_stats:
            cmd.append("--disable-log-stats")

        # For local vLLM server, we do NOT pass --api-key to disable authentication
        # vLLM docs: "If provided, the server will require this key" (i.e., no key = no auth)
        # Users can enable auth by setting VLLM_API_KEY environment variable
        api_key = os.getenv("VLLM_API_KEY")
        if api_key:
            cmd.extend(["--api-key", api_key])
            logger.info("🔐 启用 vLLM 认证 (API key from VLLM_API_KEY)")
        else:
            logger.info("🔓 禁用 vLLM 认证 (no --api-key parameter)")

        # Add extra args
        for key, value in self.config.extra_args.items():
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key.replace('_', '-')}")
            else:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        return cmd

    def stop(self, timeout: int = 10) -> bool:
        """Stop the LLM API server

        Args:
            timeout: Seconds to wait for graceful shutdown before force kill

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running():
            logger.warning("LLM API server is not running")
            return True

        logger.info(f"Stopping LLM API server (PID: {self.pid})...")

        try:
            if self.process:
                # Try graceful shutdown first
                self.process.terminate()
                try:
                    self.process.wait(timeout=timeout)
                    logger.info("LLM API server stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if timeout
                    logger.warning("Graceful shutdown timeout, force killing...")
                    self.process.kill()
                    self.process.wait()
                    logger.info("LLM API server force killed")

                self.process = None
                self.pid = None
                return True
            elif self.pid:
                # Process handle not available, use psutil
                try:
                    proc = psutil.Process(self.pid)
                    proc.terminate()
                    proc.wait(timeout=timeout)
                    logger.info("LLM API server stopped gracefully")
                except psutil.TimeoutExpired:
                    proc.kill()
                    logger.info("LLM API server force killed")

                self.pid = None
                return True
            else:
                return True

        except Exception as exc:
            logger.error(f"Failed to stop LLM API server: {exc}")
            return False

    def restart(self, background: bool = True) -> bool:
        """Restart the LLM API server

        Returns:
            True if restarted successfully, False otherwise
        """
        logger.info("Restarting LLM API server...")
        self.stop()
        time.sleep(2)  # Wait a bit before restart
        return self.start(background=background)

    def is_running(self) -> bool:
        """Check if the LLM API server is running

        Returns:
            True if running, False otherwise
        """
        # Check process
        if self.process and self.process.poll() is None:
            return True

        # Check PID
        if self.pid and psutil.pid_exists(self.pid):
            try:
                proc = psutil.Process(self.pid)
                return proc.is_running()
            except psutil.NoSuchProcess:
                return False

        # Check port
        return self._check_port_open()

    def is_healthy(self) -> bool:
        """Check if the LLM API server is healthy

        Returns:
            True if healthy (responding to health check), False otherwise
        """
        if not self.is_running():
            return False

        try:
            url = f"http://{self.config.host}:{self.config.port}/health"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        """Get detailed status of the LLM API server

        Returns:
            Dictionary with status information
        """
        return {
            "running": self.is_running(),
            "healthy": self.is_healthy(),
            "backend": self.config.backend,
            "pid": self.pid,
            "port": self.config.port,
            "host": self.config.host,
            "model": self.config.model,
            "log_file": str(self.log_file) if self.log_file else None,
            "base_url": f"http://{self.config.host}:{self.config.port}",
            "api_url": f"http://{self.config.host}:{self.config.port}/v1",
        }

    def _wait_for_ready(self, timeout: int = 120) -> bool:
        """Wait for server to be ready

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if server is ready, False if timeout
        """
        logger.info(f"Waiting for LLM API server to be ready (timeout: {timeout}s)...")
        logger.info(f"Health check URL: http://127.0.0.1:{self.config.port}/health")
        logger.info(f"Log file: {self.log_file}")

        url = f"http://127.0.0.1:{self.config.port}/health"
        start_time = time.time()
        attempt = 0

        while time.time() - start_time < timeout:
            attempt += 1
            elapsed = time.time() - start_time

            # Check if process is still alive
            if not self.is_running():
                logger.error("LLM API server process died during startup")
                logger.error("Check the log file for details:")
                self._tail_log_file(lines=50)
                return False

            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    # Clear progress bar and print success
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                    logger.info(
                        f"✅ LLM API server is ready! (took {elapsed:.1f}s, {attempt} attempts)"
                    )
                    return True
                else:
                    logger.debug(f"Attempt {attempt}: Got status {response.status_code}")
            except requests.ConnectionError:
                # Show animated progress bar (update every attempt)
                progress = min(elapsed / timeout, 1.0)  # 0.0 to 1.0
                bar_width = 40
                filled = int(bar_width * progress)
                bar = "█" * filled + "░" * (bar_width - filled)
                percent = int(progress * 100)
                print(f"\r⏳ 启动中 [{bar}] {percent}% ({elapsed:.0f}s)", end="", flush=True)
            except requests.Timeout:
                logger.debug(f"Attempt {attempt}: Request timeout")
            except Exception as e:
                logger.debug(f"Attempt {attempt}: {type(e).__name__}: {e}")

            time.sleep(1)

        # Clear progress line before showing error
        print("\r" + " " * 80 + "\r", end="", flush=True)
        logger.error(f"❌ LLM API server failed to start within {timeout} seconds")
        logger.error("Last 50 lines of log:")
        self._tail_log_file(lines=50)
        return False

    def _tail_log_file(self, lines: int = 50) -> None:
        """Print last N lines of log file"""
        if not self.log_file or not self.log_file.exists():
            logger.warning("Log file not available")
            return

        try:
            with open(self.log_file) as f:
                all_lines = f.readlines()
                tail_lines = all_lines[-lines:]
                logger.info("=" * 70)
                for line in tail_lines:
                    print(line.rstrip())
                logger.info("=" * 70)
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")

    def _check_port_open(self) -> bool:
        """Check if the port is open"""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(("127.0.0.1", self.config.port))
            return result == 0

    def __enter__(self):
        """Context manager support"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.stop()
        return False


# Backward compatibility aliases
VLLMAPIServerConfig = LLMServerConfig
VLLMAPIServer = LLMAPIServer
