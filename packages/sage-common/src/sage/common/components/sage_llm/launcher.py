"""Unified LLM Service Launcher for sageLLM.

This module provides a unified interface for launching LLM services,
consolidating common functionality used by both sage-cli and sage-studio.

Features:
- Model cache resolution (via vllm_registry)
- Fine-tuned model support
- Service info persistence for management
- Unified default configuration (port 8901)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from rich.console import Console

from sage.common.config import ensure_hf_mirror_configured
from sage.common.config.ports import SagePorts
from sage.common.utils.logging import get_logger

from .api_server import LLMAPIServer, LLMServerConfig

logger = get_logger(__name__)
console = Console()

# Unified service info storage
SAGE_DIR = Path.home() / ".sage"
LLM_PID_FILE = SAGE_DIR / "llm_service.pid"
LLM_CONFIG_FILE = SAGE_DIR / "llm_service_config.json"
LOG_DIR = SAGE_DIR / "logs"


class LLMLauncherResult:
    """Result of LLM service launch operation."""

    def __init__(
        self,
        success: bool,
        server: LLMAPIServer | None = None,
        pid: int | None = None,
        port: int | None = None,
        model: str | None = None,
        log_file: Path | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.server = server
        self.pid = pid
        self.port = port
        self.model = model
        self.log_file = log_file
        self.error = error


class LLMLauncher:
    """Unified LLM Service Launcher.

    Consolidates LLM service startup logic from sage-cli and sage-studio
    into a single, reusable component.

    Example:
        ```python
        from sage.common.components.sage_llm import LLMLauncher

        # Simple launch
        result = LLMLauncher.launch("Qwen/Qwen2.5-0.5B-Instruct")
        if result.success:
            print(f"LLM running at http://localhost:{result.port}/v1")

        # With fine-tuned model
        result = LLMLauncher.launch(use_finetuned=True)

        # Stop service
        LLMLauncher.stop()
        ```
    """

    @staticmethod
    def _ensure_dirs() -> None:
        """Ensure required directories exist."""
        SAGE_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def save_service_info(pid: int, config: dict[str, Any]) -> None:
        """Save service PID and config for later management.

        Args:
            pid: Process ID of the running service
            config: Service configuration dict
        """
        LLMLauncher._ensure_dirs()
        LLM_PID_FILE.write_text(str(pid))
        LLM_CONFIG_FILE.write_text(json.dumps(config, indent=2))

    @staticmethod
    def load_service_info() -> tuple[int | None, dict[str, Any] | None]:
        """Load saved service info.

        Returns:
            Tuple of (pid, config) or (None, None) if not found
        """
        pid = None
        config = None
        if LLM_PID_FILE.exists():
            try:
                pid = int(LLM_PID_FILE.read_text().strip())
            except (ValueError, OSError):
                pass
        if LLM_CONFIG_FILE.exists():
            try:
                config = json.loads(LLM_CONFIG_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return pid, config

    @staticmethod
    def clear_service_info() -> None:
        """Clear saved service info."""
        LLM_PID_FILE.unlink(missing_ok=True)
        LLM_CONFIG_FILE.unlink(missing_ok=True)

    @staticmethod
    def resolve_model_path(
        model: str,
        use_finetuned: bool = False,
        finetuned_models: list[dict[str, Any]] | None = None,
        verbose: bool = True,
    ) -> tuple[str, bool]:
        """Resolve model to local path if cached.

        Args:
            model: Model name or path
            use_finetuned: If True, try to use a fine-tuned model
            finetuned_models: List of available fine-tuned models (from finetune_manager)
            verbose: Print status messages

        Returns:
            Tuple of (resolved_model_path, is_local_path)
        """
        # Check if requesting fine-tuned model
        if use_finetuned and finetuned_models:
            # Use the most recent fine-tuned model
            latest = sorted(
                finetuned_models,
                key=lambda m: m.get("completed_at") or "",
                reverse=True,
            )[0]
            model = latest["path"]
            if verbose:
                console.print(f"[cyan]🎓 使用微调模型: {latest['name']}[/cyan]")
                console.print(f"   基础模型: {latest.get('base_model', 'unknown')}")
                console.print(f"   类型: {latest.get('type', 'unknown')}")

        # Check if this is already a local path
        is_local_path = Path(model).exists()

        if is_local_path:
            if verbose:
                console.print("   [green]✓[/green] 使用本地模型路径")
            return model, True

        # Try to resolve from vLLM cache
        try:
            from sage.common.model_registry import vllm_registry

            try:
                cached_path = vllm_registry.get_model_path(model)
                if verbose:
                    console.print(f"   [green]✓[/green] 使用本地缓存: {cached_path}")
                return str(cached_path), True
            except Exception:
                if verbose:
                    console.print("   [yellow]⚠️  模型未缓存，将从 HuggingFace 下载...[/yellow]")
                    console.print(f"   下载位置: ~/.sage/models/vllm/{model.replace('/', '__')}/")
                return model, False
        except ImportError:
            # Registry not available
            return model, False

    @classmethod
    def is_running(cls) -> tuple[bool, int | None]:
        """Check if LLM service is already running.

        Returns:
            Tuple of (is_running, pid)
        """
        import psutil

        pid, _ = cls.load_service_info()
        if pid and psutil.pid_exists(pid):
            return True, pid
        return False, None

    @classmethod
    def launch(
        cls,
        model: str = "Qwen/Qwen2.5-0.5B-Instruct",
        *,
        port: int | None = None,
        host: str = "0.0.0.0",
        gpu_memory: float = 0.7,
        max_model_len: int = 4096,
        tensor_parallel: int = 1,
        background: bool = True,
        use_finetuned: bool = False,
        finetuned_models: list[dict[str, Any]] | None = None,
        verbose: bool = True,
        check_existing: bool = True,
    ) -> LLMLauncherResult:
        """Launch LLM service with unified configuration.

        Args:
            model: Model name or path (default: Qwen/Qwen2.5-0.5B-Instruct)
            port: Server port (default: SagePorts.BENCHMARK_LLM = 8901)
            host: Server host (default: 0.0.0.0)
            gpu_memory: GPU memory utilization (default: 0.7 for consumer GPUs)
            max_model_len: Maximum sequence length (default: 4096)
            tensor_parallel: Number of GPUs for tensor parallelism
            background: Run in background (default: True)
            use_finetuned: Try to use a fine-tuned model
            finetuned_models: Available fine-tuned models list
            verbose: Print status messages
            check_existing: Check and reject if service already running

        Returns:
            LLMLauncherResult with success status and service details
        """
        # Use unified default port
        if port is None:
            port = SagePorts.BENCHMARK_LLM  # 8901

        # Auto-configure HuggingFace mirror
        ensure_hf_mirror_configured()
        cls._ensure_dirs()

        # Check if already running
        if check_existing:
            is_running, existing_pid = cls.is_running()
            if is_running:
                if verbose:
                    console.print(f"[yellow]⚠️  LLM 服务已在运行中 (PID: {existing_pid})[/yellow]")
                    console.print("使用 'sage llm stop' 停止现有服务")
                return LLMLauncherResult(
                    success=False,
                    error=f"Service already running (PID: {existing_pid})",
                )

        # Resolve model path (check cache, handle fine-tuned)
        resolved_model, is_local = cls.resolve_model_path(
            model,
            use_finetuned=use_finetuned,
            finetuned_models=finetuned_models,
            verbose=verbose,
        )

        if verbose:
            console.print("[blue]🚀 启动 LLM 服务 (sageLLM)[/blue]")
            console.print(f"   模型: {resolved_model}")
            console.print(f"   端口: {port}")
            console.print(f"   GPU 内存: {gpu_memory:.0%}")
            console.print(f"   模式: {'后台' if background else '前台'}")

        # Create server config
        config = LLMServerConfig(
            model=resolved_model,
            backend="vllm",
            host=host,
            port=port,
            gpu_memory_utilization=gpu_memory,
            max_model_len=max_model_len,
            tensor_parallel_size=tensor_parallel,
        )

        # Create and start server
        server = LLMAPIServer(config)
        log_file = LOG_DIR / f"llm_api_server_{port}.log"

        try:
            success = server.start(background=background, log_file=log_file)

            if success and background:
                # Save service info for management
                cls.save_service_info(
                    server.pid,
                    {
                        "model": resolved_model,
                        "port": port,
                        "host": host,
                        "gpu_memory": gpu_memory,
                        "log_file": str(log_file),
                    },
                )

                # Set environment variables for client auto-detection
                os.environ["SAGE_CHAT_BASE_URL"] = f"http://127.0.0.1:{port}/v1"
                os.environ["SAGE_CHAT_MODEL"] = resolved_model

                if verbose:
                    console.print("\n[green]✅ LLM 服务已启动[/green]")
                    console.print(f"   PID: {server.pid}")
                    console.print(f"   API: http://localhost:{port}/v1")
                    console.print(f"   日志: {log_file}")

                return LLMLauncherResult(
                    success=True,
                    server=server,
                    pid=server.pid,
                    port=port,
                    model=resolved_model,
                    log_file=log_file,
                )
            elif success:
                # Foreground mode (blocking)
                return LLMLauncherResult(
                    success=True,
                    server=server,
                    port=port,
                    model=resolved_model,
                )
            else:
                if verbose:
                    console.print("[red]❌ LLM 服务启动失败[/red]")
                return LLMLauncherResult(
                    success=False,
                    error="Server start() returned False",
                )

        except Exception as exc:
            if verbose:
                console.print(f"[red]❌ 启动 LLM 服务失败: {exc}[/red]")
            return LLMLauncherResult(success=False, error=str(exc))

    @classmethod
    def stop(cls, verbose: bool = True) -> bool:
        """Stop running LLM service.

        Args:
            verbose: Print status messages

        Returns:
            True if stopped successfully
        """
        import psutil

        pid, config = cls.load_service_info()

        if not pid:
            if verbose:
                console.print("[yellow]ℹ️  没有找到运行中的 LLM 服务[/yellow]")
            return True

        if not psutil.pid_exists(pid):
            if verbose:
                console.print("[yellow]ℹ️  LLM 服务已不存在，清理记录[/yellow]")
            cls.clear_service_info()
            return True

        try:
            if verbose:
                console.print(f"[blue]🛑 停止 LLM 服务 (PID: {pid})...[/blue]")

            proc = psutil.Process(pid)
            proc.terminate()

            try:
                proc.wait(timeout=10)
                if verbose:
                    console.print("[green]✅ LLM 服务已停止[/green]")
            except psutil.TimeoutExpired:
                if verbose:
                    console.print("[yellow]⚠️  强制终止...[/yellow]")
                proc.kill()
                proc.wait()
                if verbose:
                    console.print("[green]✅ LLM 服务已强制停止[/green]")

            cls.clear_service_info()
            return True

        except Exception as exc:
            if verbose:
                console.print(f"[red]❌ 停止失败: {exc}[/red]")
            return False

    @classmethod
    def status(cls, verbose: bool = True) -> dict[str, Any] | None:
        """Get status of LLM service.

        Args:
            verbose: Print status messages

        Returns:
            Status dict or None if not running
        """
        import psutil

        pid, config = cls.load_service_info()

        if not pid:
            if verbose:
                console.print("[yellow]ℹ️  LLM 服务未运行[/yellow]")
            return None

        if not psutil.pid_exists(pid):
            if verbose:
                console.print("[yellow]ℹ️  LLM 服务已停止（进程不存在）[/yellow]")
            cls.clear_service_info()
            return None

        # Service is running
        status = {
            "running": True,
            "pid": pid,
            **(config or {}),
        }

        if verbose:
            console.print("[green]✅ LLM 服务运行中[/green]")
            console.print(f"   PID: {pid}")
            if config:
                console.print(f"   模型: {config.get('model', 'unknown')}")
                console.print(f"   端口: {config.get('port', 'unknown')}")
                console.print(f"   API: http://localhost:{config.get('port', 8901)}/v1")
                if config.get("log_file"):
                    console.print(f"   日志: {config['log_file']}")

        return status
