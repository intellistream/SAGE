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

from .api_server import LLMAPIServer, LLMServerConfig, get_served_model_name

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
    def _get_pid_file(port: int) -> Path:
        return SAGE_DIR / f"llm_service_{port}.pid"

    @staticmethod
    def _get_config_file(port: int) -> Path:
        return SAGE_DIR / f"llm_service_config_{port}.json"

    @staticmethod
    def _resolve_client_host(host: str | None) -> str:
        """Translate bind-all hosts to a concrete endpoint for clients."""
        if not host or host in {"0.0.0.0", "::", "", "*"}:
            return "127.0.0.1"
        return host

    @classmethod
    def build_base_url(cls, host: str | None, port: int) -> str:
        """Format an HTTP base URL, handling IPv6 literals when necessary."""
        resolved_host = cls._resolve_client_host(host)
        if ":" in resolved_host and not resolved_host.startswith("["):
            resolved_host = f"[{resolved_host}]"
        return f"http://{resolved_host}:{port}/v1"

    @classmethod
    def discover_running_services(cls) -> list[dict[str, Any]]:
        """List services recorded in llm_service_config files."""
        services: list[dict[str, Any]] = []
        if not SAGE_DIR.exists():
            return services

        for config_file in SAGE_DIR.glob("llm_service_config_*.json"):
            try:
                config = json.loads(config_file.read_text())
                port_value = config.get("port")
                if port_value is None:
                    continue
                port = int(port_value)
                host = config.get("host")
                base_url = cls.build_base_url(host, port)
                services.append(
                    {
                        "base_url": base_url,
                        "host": host,
                        "port": port,
                        "served_model_name": config.get("served_model_name"),
                        "model": config.get("model"),
                        "config": config,
                    }
                )
            except Exception:
                continue

        return services

    @staticmethod
    def save_service_info(pid: int, config: dict[str, Any], port: int | None = None) -> None:
        """Save service PID and config for later management.

        Args:
            pid: Process ID of the running service
            config: Service configuration dict
            port: Service port (optional, for multi-instance support)
        """
        LLMLauncher._ensure_dirs()

        # If port is provided, use port-specific file
        if port is not None:
            LLMLauncher._get_pid_file(port).write_text(str(pid))
            LLMLauncher._get_config_file(port).write_text(json.dumps(config, indent=2))

        # Also update default file if it's the default port or port is None
        # This maintains backward compatibility for tools expecting the default file
        if port is None or port == SagePorts.BENCHMARK_LLM:
            LLM_PID_FILE.write_text(str(pid))
            LLM_CONFIG_FILE.write_text(json.dumps(config, indent=2))

    @staticmethod
    def load_service_info(port: int | None = None) -> tuple[int | None, dict[str, Any] | None]:
        """Load saved service info.

        Args:
            port: Service port (optional)

        Returns:
            Tuple of (pid, config) or (None, None) if not found
        """
        pid = None
        config = None

        # Determine which file to read
        if port is not None:
            pid_file = LLMLauncher._get_pid_file(port)
            config_file = LLMLauncher._get_config_file(port)
            # Fallback to default file if port-specific not found and port is default
            if not pid_file.exists() and port == SagePorts.BENCHMARK_LLM:
                pid_file = LLM_PID_FILE
                config_file = LLM_CONFIG_FILE
        else:
            pid_file = LLM_PID_FILE
            config_file = LLM_CONFIG_FILE

        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
            except (ValueError, OSError):
                pass
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return pid, config

    @staticmethod
    def clear_service_info(port: int | None = None) -> None:
        """Clear saved service info.

        Args:
            port: Service port (optional)
        """
        if port is not None:
            LLMLauncher._get_pid_file(port).unlink(missing_ok=True)
            LLMLauncher._get_config_file(port).unlink(missing_ok=True)

        # Also clear default if it matches
        if port is None or port == SagePorts.BENCHMARK_LLM:
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

        # Try to resolve from SAGE vLLM cache first
        try:
            from sage.common.model_registry import vllm_registry

            try:
                cached_path = vllm_registry.get_model_path(model)
                if verbose:
                    console.print(f"   [green]✓[/green] 使用本地缓存: {cached_path}")
                return str(cached_path), True
            except Exception:
                pass  # Not in SAGE cache, check HuggingFace cache below
        except ImportError:
            pass  # Registry not available

        # Check HuggingFace Hub cache (vLLM uses this by default)
        try:
            from huggingface_hub import try_to_load_from_cache
            from huggingface_hub.constants import HF_HUB_CACHE

            # Check if model config exists in HF cache (indicates model is cached)
            cached_config = try_to_load_from_cache(model, "config.json")
            if cached_config is not None:
                if verbose:
                    console.print(f"   [green]✓[/green] 使用 HuggingFace 缓存: {HF_HUB_CACHE}")
                return model, True
        except Exception:
            pass  # HF cache check failed, assume not cached

        # Model not found in any cache
        if verbose:
            console.print("   [yellow]⚠️  模型未缓存，将从 HuggingFace 下载...[/yellow]")
            console.print("   下载位置: ~/.cache/huggingface/hub/")
        return model, False

    @classmethod
    def is_running(cls, port: int | None = None) -> tuple[bool, int | None]:
        """Check if LLM service is already running.

        Args:
            port: Service port (optional)

        Returns:
            Tuple of (is_running, pid)
        """
        import psutil

        pid, _ = cls.load_service_info(port)
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
        speculative_model: str | None = None,
        speculative_config: dict[str, Any] | None = None,
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
            speculative_model: Draft model for speculative decoding (optional)
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
            is_running, existing_pid = cls.is_running(port)
            if is_running:
                if verbose:
                    console.print(
                        f"[yellow]⚠️  LLM 服务已在运行中 (PID: {existing_pid}, 端口: {port})[/yellow]"
                    )
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

        # Resolve speculative model path if provided
        resolved_speculative_model = None
        if speculative_model:
            resolved_speculative_model, _ = cls.resolve_model_path(
                speculative_model,
                verbose=verbose,
            )

        if verbose:
            console.print("[blue]🚀 启动 LLM 服务 (sageLLM)[/blue]")
            console.print(f"   模型: {resolved_model}")
            if resolved_speculative_model:
                console.print(f"   投机模型: {resolved_speculative_model}")
            console.print(f"   端口: {port}")
            console.print(f"   GPU 内存: {gpu_memory:.0%}")
            console.print(f"   模式: {'后台' if background else '前台'}")

        # Create server config
        # Note: speculative_model is passed via kwargs to LLMServerConfig -> extra_args
        server_kwargs = {}
        if resolved_speculative_model:
            server_kwargs["speculative_model"] = resolved_speculative_model
            # Auto-set num_speculative_tokens if not provided (vLLM default is usually 5)
            server_kwargs["num_speculative_tokens"] = 5

        if speculative_config:
            server_kwargs["speculative_config"] = json.dumps(speculative_config)

        config = LLMServerConfig(
            model=resolved_model,
            backend="vllm",
            host=host,
            port=port,
            gpu_memory_utilization=gpu_memory,
            max_model_len=max_model_len,
            tensor_parallel_size=tensor_parallel,
            **server_kwargs,
        )

        # Create and start server
        server = LLMAPIServer(config)
        log_file = LOG_DIR / f"llm_api_server_{port}.log"

        try:
            success = server.start(background=background, log_file=log_file)

            if success and background:
                # Get the friendly model name for API clients
                # e.g., /home/user/.sage/models/vllm/Qwen__X -> Qwen/X
                served_model_name = get_served_model_name(resolved_model)

                # Save service info for management
                cls.save_service_info(
                    server.pid,
                    {
                        "model": resolved_model,
                        "served_model_name": served_model_name,
                        "port": port,
                        "host": host,
                        "gpu_memory": gpu_memory,
                        "log_file": str(log_file),
                    },
                    port=port,
                )

                # Set environment variables for client auto-detection
                # Use the friendly model name so clients can call the API correctly
                os.environ["SAGE_CHAT_BASE_URL"] = cls.build_base_url(host, port)
                os.environ["SAGE_CHAT_MODEL"] = served_model_name

                if verbose:
                    console.print("\n[green]✅ LLM 服务已启动[/green]")
                    console.print(f"   PID: {server.pid}")
                    console.print(f"   API: {cls.build_base_url(host, port)}")
                    console.print(f"   模型: {served_model_name}")
                    console.print(f"   日志: {log_file}")

                return LLMLauncherResult(
                    success=True,
                    server=server,
                    pid=server.pid,
                    port=port,
                    model=served_model_name,
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
    def stop(cls, verbose: bool = True, force: bool = False, port: int | None = None) -> bool:
        """Stop running LLM service.

        Args:
            verbose: Print status messages
            force: If True, attempt to find and stop services on default ports even if PID file is missing.
            port: Specific port to stop. If None, stops default or all found.

        Returns:
            True if stopped successfully
        """
        import psutil

        # Helper to kill process by PID
        def _kill_pid(target_pid: int, name: str) -> bool:
            if not psutil.pid_exists(target_pid):
                return False
            try:
                if verbose:
                    console.print(f"[blue]🛑 停止 {name} (PID: {target_pid})...[/blue]")
                proc = psutil.Process(target_pid)
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except psutil.TimeoutExpired:
                    if verbose:
                        console.print("[yellow]⚠️  强制终止...[/yellow]")
                    proc.kill()
                    proc.wait()
                return True
            except Exception as e:
                if verbose:
                    console.print(f"[yellow]⚠️  停止 {name} 失败: {e}[/yellow]")
                return False

        stopped_any = False

        # Find PIDs to stop
        pids_to_stop = []

        if port is not None:
            # Stop specific port
            pid, config = cls.load_service_info(port)
            if pid:
                pids_to_stop.append((pid, config, port))
        else:
            # Stop default port
            pid, config = cls.load_service_info(None)
            if pid:
                pids_to_stop.append((pid, config, None))

            # Also scan for other pid files
            for pid_file in SAGE_DIR.glob("llm_service_*.pid"):
                try:
                    # Extract port from filename llm_service_8902.pid
                    fname = pid_file.name
                    if fname == "llm_service.pid":
                        continue  # Already handled
                    p_str = fname.replace("llm_service_", "").replace(".pid", "")
                    if p_str.isdigit():
                        p = int(p_str)
                        pid_val = int(pid_file.read_text().strip())
                        # Load config if exists
                        cfg_file = LLMLauncher._get_config_file(p)
                        cfg = None
                        if cfg_file.exists():
                            cfg = json.loads(cfg_file.read_text())
                        pids_to_stop.append((pid_val, cfg, p))
                except Exception:
                    pass

        # Execute stop
        for pid, config, p in pids_to_stop:
            if psutil.pid_exists(pid):
                # Stop Embedding service if recorded
                if config and "embedding_pid" in config:
                    _kill_pid(config["embedding_pid"], "Embedding 服务")

                if _kill_pid(pid, f"LLM 服务 (端口 {p or 'default'})"):
                    stopped_any = True
                    if verbose:
                        console.print(f"[green]✅ LLM 服务已停止 (端口 {p or 'default'})[/green]")
            else:
                if verbose:
                    console.print(f"[yellow]ℹ️  记录的 LLM 服务 (PID: {pid}) 已不存在[/yellow]")

            cls.clear_service_info(p)

        # 2. If force is True, check default ports for orphan services
        if force:
            ports_to_check = [
                SagePorts.LLM_DEFAULT,
                SagePorts.BENCHMARK_LLM,
                SagePorts.EMBEDDING_DEFAULT,
            ]
            if port:
                ports_to_check = [port]

            # Get all listening connections
            try:
                connections = psutil.net_connections(kind="inet")
                for conn in connections:
                    if conn.status == "LISTEN" and conn.laddr.port in ports_to_check:
                        orphan_pid = conn.pid
                        # Skip if it's the one we just killed (though pid check handles it)
                        # or if it's None (permission denied)
                        if orphan_pid and orphan_pid != pid:
                            if verbose:
                                console.print(
                                    f"[yellow]⚠️  发现端口 {conn.laddr.port} 上的孤儿服务 (PID: {orphan_pid})[/yellow]"
                                )

                            if _kill_pid(orphan_pid, f"孤儿服务 (Port {conn.laddr.port})"):
                                stopped_any = True
                                if verbose:
                                    console.print(
                                        f"[green]✅ 孤儿服务 (Port {conn.laddr.port}) 已停止[/green]"
                                    )
            except Exception as e:
                if verbose:
                    console.print(f"[yellow]⚠️  扫描孤儿服务失败: {e}[/yellow]")

        if not pid and not stopped_any:
            if verbose:
                console.print("[yellow]ℹ️  没有找到运行中的 LLM 服务[/yellow]")
            return True

        return True

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
                console.print("[yellow]ℹ️  没有找到运行中的 LLM 服务[/yellow]")
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
                api_port = int(config.get("port", SagePorts.BENCHMARK_LLM))
                console.print(f"   API: {cls.build_base_url(config.get('host'), api_port)}")
                if config.get("log_file"):
                    console.print(f"   日志: {config['log_file']}")

        return status
