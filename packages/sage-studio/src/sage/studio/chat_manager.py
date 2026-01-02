"""Chat Mode Manager - Studio Manager with integrated LLM support"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import requests
from rich.console import Console
from rich.table import Table

from sage.common.config import find_sage_project_root
from sage.common.config.ports import SagePorts
from sage.common.config.user_paths import get_user_paths

from .studio_manager import StudioManager
from .utils.gpu_check import is_gpu_available

console = Console()


class ChatModeManager(StudioManager):
    """Studio Manager with integrated local LLM support.

    Extends StudioManager to add sageLLM integration for local LLM services.
    This is now the default manager - no need for backward compatibility.
    """

    def __init__(self):
        super().__init__()

        # Local LLM service management (via sageLLM)
        self.llm_service = None  # Will be VLLMService or other sageLLM service
        # Default to enabling LLM with a small model
        self.llm_enabled = os.getenv("SAGE_STUDIO_LLM", "true").lower() in ("true", "1", "yes")
        # Use Qwen2.5-0.5B as default - lightweight for local development
        self.llm_model = os.getenv("SAGE_STUDIO_LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
        self.llm_port = SagePorts.BENCHMARK_LLM  # Unified default port (8901)

    # ------------------------------------------------------------------
    # Fine-tuned Model Discovery
    # ------------------------------------------------------------------
    def list_finetuned_models(self) -> list[dict]:
        """List available fine-tuned models from Studio's finetune manager.

        Returns:
            List of fine-tuned model info dictionaries
        """
        try:
            from sage.libs.finetune import finetune_manager

            models = []
            for task in finetune_manager.tasks.values():
                if task.status.value == "completed":
                    # Check for merged model (preferred) or LoRA checkpoint
                    output_path = Path(task.output_dir)
                    merged_path = output_path / "merged_model"
                    lora_path = output_path / "lora"

                    model_path = None
                    model_type = None

                    if merged_path.exists():
                        model_path = str(merged_path)
                        model_type = "merged"
                    elif lora_path.exists():
                        model_path = str(lora_path)
                        model_type = "lora"

                    if model_path:
                        models.append(
                            {
                                "path": model_path,
                                "name": task.task_id,
                                "base_model": task.model_name,
                                "type": model_type,
                                "completed_at": task.completed_at,
                            }
                        )

            return models
        except ImportError:
            console.print("[yellow]⚠️  FinetuneManager not available[/yellow]")
            return []

    def get_finetuned_model_path(self, model_name: str) -> str | None:
        """Get path of a fine-tuned model by name.

        Args:
            model_name: Task ID or model name

        Returns:
            Path to the fine-tuned model, or None if not found
        """
        models = self.list_finetuned_models()
        for model in models:
            if model["name"] == model_name or model_name in model["path"]:
                return model["path"]
        return None

    def apply_finetuned_model(self, model_path: str) -> dict[str, Any]:
        """Apply a finetuned model to the running LLM service (hot-swap).

        This will restart the local LLM service with the new model.
        Gateway will automatically detect the new model.

        **Architecture Note**: This method belongs in sage-studio (L6) because it
        directly depends on ChatModeManager and Studio-specific infrastructure.
        It was moved from sage-libs (L3) to fix architecture layering violations.

        Args:
            model_path: Path to the finetuned model (local path or HF model name)

        Returns:
            Dict with status and message
        """
        try:
            # Check if LLM service is running
            if not self.llm_service or not self.llm_service.is_running():
                return {
                    "success": False,
                    "message": "本地 LLM 服务未运行。请先启动 Studio 的 LLM 服务。",
                }

            print(f"🔄 正在切换到微调模型: {model_path}")

            # Stop current LLM service
            print("   停止当前 LLM 服务...")
            self.llm_service.stop()

            # Update config with new model
            import time

            time.sleep(2)  # Wait for cleanup

            from sage.common.config.ports import SagePorts
            from sage.llm import LLMAPIServer, LLMServerConfig

            config = LLMServerConfig(
                model=model_path,
                backend="vllm",
                host="0.0.0.0",
                port=SagePorts.LLM_DEFAULT,
                gpu_memory_utilization=float(os.getenv("SAGE_STUDIO_LLM_GPU_MEMORY", "0.9")),
                max_model_len=4096,
                disable_log_stats=True,
            )

            # Start new service with finetuned model
            print(f"   启动新模型: {model_path}")
            self.llm_service = LLMAPIServer(config)
            success = self.llm_service.start(background=True)

            if success:
                # Update FinetuneManager's current_model for UI display
                try:
                    from sage.libs.finetune import finetune_manager

                    finetune_manager.current_model = model_path
                    finetune_manager._save_tasks()
                except Exception as e:
                    print(f"⚠️  无法更新 FinetuneManager: {e}")

                print("✅ 模型切换成功！")
                print(f"   当前模型: {model_path}")
                print("   Gateway 会自动检测到新模型")

                return {
                    "success": True,
                    "message": f"成功切换到模型: {model_path}",
                    "model": model_path,
                }
            else:
                return {
                    "success": False,
                    "message": "LLM 服务启动失败，请查看日志",
                }

        except Exception as e:
            import traceback

            print(f"❌ 模型切换失败: {e}")
            print(traceback.format_exc())
            return {
                "success": False,
                "message": f"切换失败: {str(e)}",
            }

    # ------------------------------------------------------------------
    # Service Detection helpers
    # ------------------------------------------------------------------
    def _normalize_base_url(self, url: str | None) -> str | None:
        return url.rstrip("/") if url else url

    def _probe_llm_endpoint(self, base_url: str | None) -> bool:
        """Return True if the provided endpoint responds to /models."""
        if not base_url:
            return False
        normalized = self._normalize_base_url(base_url)
        if not normalized:
            return False
        try:
            resp = requests.get(f"{normalized}/models", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _detect_existing_llm_service(self) -> tuple[bool, str | None]:
        """Detect if LLM service is already running at known ports.

        Checks common LLM ports (8901, 8001, 8000) for existing service.

        Returns:
            Tuple of (is_running, base_url) - base_url is set if service found
        """
        candidates: list[str] = []
        seen: set[str] = set()

        def _add_candidate(url: str | None) -> None:
            normalized = self._normalize_base_url(url)
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            candidates.append(normalized)

        launcher_cls = None
        try:
            from sage.llm import LLMLauncher

            launcher_cls = LLMLauncher
            for service in LLMLauncher.discover_running_services():
                _add_candidate(service.get("base_url"))
        except ImportError:
            launcher_cls = None

        # Ports to check in order of preference
        llm_ports = [
            self.llm_port,
            SagePorts.get_recommended_llm_port(),
            SagePorts.LLM_DEFAULT,
            SagePorts.BENCHMARK_LLM,
        ]

        for port in llm_ports:
            if launcher_cls:
                candidate = launcher_cls.build_base_url(None, port)
            else:
                candidate = f"http://127.0.0.1:{port}/v1"
            _add_candidate(candidate)

        for candidate in candidates:
            if self._probe_llm_endpoint(candidate):
                return True, candidate

        # Fallback: honor explicit env only if it is reachable AND loopback, to avoid
        # blocking auto-start when a cloud endpoint is configured.
        env_base_url = os.environ.get("SAGE_CHAT_BASE_URL") or os.environ.get(
            "SAGE_UNIFIED_BASE_URL"
        )
        if env_base_url and self._probe_llm_endpoint(env_base_url):
            try:
                parsed = requests.utils.urlparse(env_base_url)
                host = parsed.hostname
                if host and host in {"127.0.0.1", "localhost", "::1"}:
                    return True, env_base_url
            except Exception:
                pass

        return (False, None)

    def _detect_existing_embedding_service(
        self, port: int | None = None
    ) -> tuple[bool, str | None]:
        """Detect if Embedding service is already running.

        Args:
            port: Specific port to check, or None to check common ports

        Returns:
            Tuple of (is_running, base_url) - base_url is set if service found
        """
        # Check environment variables first (align with UnifiedInferenceClient)
        env_base_url = os.environ.get("SAGE_EMBEDDING_BASE_URL") or os.environ.get(
            "SAGE_UNIFIED_BASE_URL"
        )
        if env_base_url and self._probe_llm_endpoint(env_base_url):
            return (True, env_base_url)

        ports_to_check = (
            [port] if port else [SagePorts.EMBEDDING_DEFAULT, SagePorts.BENCHMARK_EMBEDDING]
        )

        for p in ports_to_check:
            if p is None:
                continue
            try:
                resp = requests.get(f"http://127.0.0.1:{p}/v1/models", timeout=2)
                if resp.status_code == 200:
                    return (True, f"http://127.0.0.1:{p}/v1")
            except Exception:
                continue

        return (False, None)

    # ------------------------------------------------------------------
    # Local LLM Service helpers (via sageLLM LLMLauncher)
    # ------------------------------------------------------------------
    def _start_llm_service(self, model: str | None = None, use_finetuned: bool = False) -> bool:
        """Start local LLM service via sageLLM.

        Uses sageLLM's unified LLMLauncher to start a local LLM HTTP server.
        The server provides OpenAI-compatible API at http://127.0.0.1:{port}/v1

        If an LLM service is already running at known ports, it will be reused
        instead of starting a new one.

        Args:
            model: Model name/path to load (can be HF model or local path)
            use_finetuned: If True, try to use a fine-tuned model

        Returns:
            True if started successfully or existing service found, False otherwise
        """
        # First, check if LLM service is already running
        is_running, existing_url = self._detect_existing_llm_service()
        if is_running:
            console.print(f"[green]✅ 发现已运行的 LLM 服务: {existing_url}[/green]")
            console.print("[dim]   跳过启动新服务，将复用现有服务[/dim]")
            return True

        try:
            from sage.llm import LLMLauncher
        except ImportError:
            console.print(
                "[yellow]⚠️  sageLLM LLMLauncher 不可用，跳过本地 LLM 启动[/yellow]\n"
                "提示：确保已安装 sage-common 包"
            )
            return False

        # Determine which model to use
        model_name = model or self.llm_model

        # Get finetuned models list if needed
        finetuned_models = None
        if use_finetuned and not model:
            finetuned_models = self.list_finetuned_models()
            if not finetuned_models:
                console.print("[yellow]⚠️  未找到可用的微调模型，使用默认模型[/yellow]")

        # Use unified launcher
        result = LLMLauncher.launch(
            model=model_name,
            port=self.llm_port,
            gpu_memory=float(os.getenv("SAGE_STUDIO_LLM_GPU_MEMORY", "0.9")),
            tensor_parallel=int(os.getenv("SAGE_STUDIO_LLM_TENSOR_PARALLEL", "1")),
            background=True,
            use_finetuned=use_finetuned,
            finetuned_models=finetuned_models,
            verbose=True,
            check_existing=True,  # Let LLMLauncher also check for duplicates
        )

        if result.success:
            self.llm_service = result.server
            return True
        else:
            console.print("[yellow]💡 提示：安装推理引擎后可使用本地服务[/yellow]")
            console.print("   示例：pip install vllm  # 安装 vLLM 引擎")
            return False

    def _stop_llm_service(self, force: bool = False) -> bool:
        """Stop local LLM service.

        Args:
            force: If True, aggressively scan and stop services on related ports.
        """
        try:
            from sage.llm import LLMLauncher
        except ImportError:
            return True

        # First, try to stop via self.llm_service if it exists
        if self.llm_service is not None:
            console.print("[blue]🛑 停止本地 LLM 服务...[/blue]")
            try:
                self.llm_service.stop()
                self.llm_service = None
                LLMLauncher.clear_service_info()
                console.print("[green]✅ 本地 LLM 服务已停止[/green]")
                return True
            except Exception as exc:
                console.print(f"[red]❌ 停止 LLM 服务失败: {exc}[/red]")
                return False

        # Use LLMLauncher to stop any running service
        stopped = LLMLauncher.stop(verbose=True, force=force)

        # If force is enabled, also scan the benchmark range (8901-8910)
        if force:
            for port in range(8901, 8911):
                # Skip if already checked by LLMLauncher (8901 is in BENCHMARK_LLM)
                if port == SagePorts.BENCHMARK_LLM:
                    continue

                try:
                    for conn in psutil.net_connections(kind="inet"):
                        if conn.status == "LISTEN" and conn.laddr.port == port:
                            pid = conn.pid
                            if pid:
                                console.print(
                                    f"[blue]🛑 发现端口 {port} 上的残留服务 (PID: {pid})...[/blue]"
                                )
                                try:
                                    proc = psutil.Process(pid)
                                    proc.terminate()
                                    try:
                                        proc.wait(timeout=5)
                                    except psutil.TimeoutExpired:
                                        proc.kill()
                                    console.print(f"[green]✅ 服务已停止 (端口 {port})[/green]")
                                    stopped = True
                                except Exception as e:
                                    console.print(f"[yellow]⚠️ 停止失败: {e}[/yellow]")
                                    try:
                                        os.kill(pid, signal.SIGKILL)
                                    except Exception:
                                        pass
                except Exception:
                    pass

        return stopped

    # ------------------------------------------------------------------
    # Embedding Service helpers
    # ------------------------------------------------------------------
    def _load_models_config(self) -> list[dict[str, object]]:
        try:
            project_root = find_sage_project_root()
        except Exception:
            project_root = None

        if not project_root:
            project_root = Path.cwd()

        config_path = project_root / "config" / "models.json"
        if not config_path.exists():
            return []

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)

            # Expand environment variables in api_key
            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict):
                        api_key = entry.get("api_key")
                        if (
                            isinstance(api_key, str)
                            and api_key.startswith("${")
                            and api_key.endswith("}")
                        ):
                            env_var = api_key[2:-1]
                            entry["api_key"] = os.getenv(env_var, "")

            return data if isinstance(data, list) else []
        except Exception as exc:
            console.print(f"[yellow]⚠️ 读取模型配置失败: {exc}[/yellow]")
            return []

    def _select_embedding_model_from_config(self) -> str | None:
        candidates = [
            entry
            for entry in self._load_models_config()
            if entry.get("engine_kind") == "embedding" and not entry.get("base_url")
        ]
        if not candidates:
            return None
        preferred = next((entry for entry in candidates if entry.get("default")), candidates[0])
        return preferred.get("name")

    def _start_embedding_service(self, model: str | None = None, port: int | None = None) -> bool:
        """Start Embedding service as a background process.

        If an Embedding service is already running at known ports, it will be reused
        instead of starting a new one.

        Args:
            model: Embedding model name (default: config/models.json embedding or BAAI/bge-m3)
            port: Server port (default: SagePorts.EMBEDDING_DEFAULT = 8090)

        Returns:
            True if started successfully or existing service found
        """
        if port is None:
            port = SagePorts.EMBEDDING_DEFAULT  # 8090

        selected_model = model or self._select_embedding_model_from_config()
        model_name = selected_model or "BAAI/bge-m3"

        # Check if already running (use the new detection method for consistent output)
        is_running, existing_url = self._detect_existing_embedding_service(port)
        if is_running:
            console.print(f"[green]✅ 发现已运行的 Embedding 服务: {existing_url}[/green]")
            console.print("[dim]   跳过启动新服务，将复用现有服务[/dim]")
            return True

        if selected_model:
            console.print(
                f"[blue]🎯 根据 config/models.json 启动 Embedding 模型: {model_name}[/blue]"
            )
        console.print(f"[blue]🎯 启动 Embedding 服务 (模型: {model_name}, 端口: {port})[/blue]")

        # Ensure log directory exists
        log_dir = get_user_paths().logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        embedding_log = log_dir / "embedding.log"

        embedding_cmd = [
            sys.executable,
            "-m",
            "sage.common.components.sage_embedding.embedding_server",
            "--model",
            model_name,
            "--port",
            str(port),
        ]

        try:
            log_handle = open(embedding_log, "w")
            proc = subprocess.Popen(
                embedding_cmd,
                stdin=subprocess.DEVNULL,  # 阻止子进程读取 stdin
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            # 注意：不关闭 log_handle，让子进程继承并管理它

            # Save PID for later cleanup
            embedding_pid_file = log_dir / "embedding.pid"
            embedding_pid_file.write_text(str(proc.pid))

            console.print(f"   [green]✓[/green] Embedding 服务已启动 (PID: {proc.pid})")
            console.print(f"   日志: {embedding_log}")

            # Wait for service to be ready (up to 180 seconds for model download)
            console.print("   [dim]等待服务就绪 (首次可能需要下载模型)...[/dim]")
            for i in range(180):
                try:
                    resp = requests.get(f"http://127.0.0.1:{port}/v1/models", timeout=1)
                    if resp.status_code == 200:
                        console.print("   [green]✓[/green] Embedding 服务已就绪")
                        return True
                except Exception:
                    pass
                time.sleep(1)

            console.print("[yellow]⚠️  Embedding 服务启动超时，但进程仍在运行[/yellow]")
            return True  # Process started, might just be slow to load model

        except Exception as e:
            console.print(f"[red]❌ 启动 Embedding 服务失败: {e}[/red]")
            return False

    def _stop_embedding_service(self, force: bool = False) -> bool:
        """Stop Embedding service if running.

        Args:
            force: If True, kill process on embedding port even if PID file is missing.

        NOTE: Only stops the service if it was started by Studio (has PID file).
        Does NOT kill orphan processes to allow reuse of manually started services,
        unless force=True is specified.
        """
        log_dir = Path.home() / ".sage" / "logs"
        embedding_pid_file = log_dir / "embedding.pid"

        stopped = False

        # Try to stop via PID file first
        if embedding_pid_file.exists():
            try:
                pid = int(embedding_pid_file.read_text().strip())
                if psutil.pid_exists(pid):
                    console.print(f"[blue]🛑 停止 Embedding 服务 (PID: {pid})...[/blue]")
                    os.kill(pid, signal.SIGTERM)
                    # Wait for graceful shutdown
                    for _ in range(5):
                        if not psutil.pid_exists(pid):
                            break
                        time.sleep(0.5)
                    # Force kill if still running
                    if psutil.pid_exists(pid):
                        os.kill(pid, signal.SIGKILL)
                    console.print("[green]✅ Embedding 服务已停止[/green]")
                    stopped = True
                embedding_pid_file.unlink()
            except Exception as e:
                console.print(f"[yellow]⚠️  清理 Embedding PID 文件失败: {e}[/yellow]")

        if force and not stopped:
            # Check default embedding port
            port = SagePorts.EMBEDDING_DEFAULT  # 8090
            try:
                for conn in psutil.net_connections(kind="inet"):
                    if conn.status == "LISTEN" and conn.laddr.port == port:
                        pid = conn.pid
                        if pid:
                            console.print(
                                f"[blue]🛑 发现 Embedding 端口 {port} 上的残留服务 (PID: {pid})...[/blue]"
                            )
                            try:
                                proc = psutil.Process(pid)
                                proc.terminate()
                                try:
                                    proc.wait(timeout=5)
                                except psutil.TimeoutExpired:
                                    proc.kill()
                                console.print(
                                    f"[green]✅ Embedding 服务已停止 (端口 {port})[/green]"
                                )
                                stopped = True
                            except Exception as e:
                                console.print(f"[yellow]⚠️ 停止失败: {e}[/yellow]")
                                try:
                                    os.kill(pid, signal.SIGKILL)
                                except Exception:
                                    pass
            except Exception:
                pass

        return stopped

    # ------------------------------------------------------------------
    # Gateway helpers
    # ------------------------------------------------------------------
    def _is_gateway_running(self) -> int | None:
        """Detect a running gateway process and align internal state.

        Looks at the PID file first, then scans candidate ports (current, default,
        fallback, and env override) for a process whose cmdline includes
        ``sage.llm.gateway.server``/``sage-llm-gateway``. When found, updates
        ``self.gateway_port`` and rewrites the PID file so subsequent stop/restart
        flows can clean it up.
        """

        candidate_ports: set[int] = {
            self.gateway_port,
            SagePorts.GATEWAY_DEFAULT,
            SagePorts.EDGE_DEFAULT,
        }

        env_port = os.environ.get("SAGE_GATEWAY_PORT")
        if env_port:
            try:
                candidate_ports.add(int(env_port))
            except ValueError:
                pass

        # 1) PID file check
        if self.gateway_pid_file.exists():
            try:
                pid = int(self.gateway_pid_file.read_text().strip())
                if psutil.pid_exists(pid):
                    return pid
            except Exception:
                pass

            # Clean up invalid PID file
            try:
                self.gateway_pid_file.unlink()
            except OSError:
                pass

        # 2) Scan known ports for our gateway process (handles orphaned starts)
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    for conn in proc.connections(kind="inet"):
                        if conn.status != psutil.CONN_LISTEN:
                            continue
                        if conn.laddr.port not in candidate_ports:
                            continue

                        try:
                            cmdline = " ".join(proc.cmdline())
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            cmdline = ""

                        if (
                            "sage.llm.gateway.server" not in cmdline
                            and "sage-llm-gateway" not in cmdline
                        ):
                            continue

                        # Align internal state to the discovered process
                        try:
                            self.gateway_port = conn.laddr.port
                        except Exception:
                            pass
                        try:
                            self.gateway_pid_file.write_text(str(proc.pid))
                        except Exception:
                            pass
                        return proc.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

        return None

    def _start_gateway(self, port: int | None = None) -> bool:
        if self._is_gateway_running():
            console.print("[green]✅ sage-gateway 已运行[/green]")
            return True

        # Skip slow import check - just try to start directly
        # If gateway is not installed, subprocess will fail anyway
        gateway_port = port or self.gateway_port

        # Detect user override; only auto-fallback when using built-in default
        explicit_port = (port is not None) or ("SAGE_GATEWAY_PORT" in os.environ)

        # Check if port is in use
        if self._is_port_in_use(gateway_port):
            console.print(f"[yellow]⚠️  端口 {gateway_port} 已被占用[/yellow]")
            try:
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        for conn in proc.connections(kind="inet"):
                            if conn.laddr.port == gateway_port:
                                console.print(
                                    f"[yellow]   占用进程: {proc.pid} ({proc.name()})[/yellow]"
                                )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except Exception:
                pass

            if (not explicit_port) and gateway_port == SagePorts.GATEWAY_DEFAULT:
                fallback_port = SagePorts.EDGE_DEFAULT
                console.print(
                    f"[cyan]💡 端口 {gateway_port} 被占用，自动切换 Gateway 到 {fallback_port}[/cyan]"
                )
                gateway_port = fallback_port
                self.gateway_port = fallback_port
            else:
                console.print(
                    "[yellow]继续尝试当前端口，若失败请手动指定 --gateway-port 或设置 SAGE_GATEWAY_PORT[/yellow]"
                )

        env = os.environ.copy()
        env.setdefault("SAGE_GATEWAY_PORT", str(gateway_port))

        console.print(f"[blue]🚀 启动 sage-llm-gateway (端口: {gateway_port})...[/blue]")
        try:
            log_handle = open(self.gateway_log_file, "w")
            process = subprocess.Popen(
                [sys.executable, "-m", "sage.llm.gateway.server"],
                stdin=subprocess.DEVNULL,  # 阻止子进程读取 stdin
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if os.name != "nt" else None,
                env=env,
            )
            self.gateway_pid_file.write_text(str(process.pid))
        except Exception as exc:
            console.print(f"[red]❌ 启动 gateway 失败: {exc}")
            console.print(
                "[yellow]提示: 请确保已安装 sage-llm-gateway: "
                "pip install -e packages/sage-llm-gateway[/yellow]"
            )
            return False

        # 等待服务就绪 - Gateway 需要加载 MemoryManager 和 FAISS 索引，需要更长时间
        url = f"http://127.0.0.1:{gateway_port}/health"
        max_attempts = 120  # 最多等待 60 秒 (120 * 0.5)
        console.print("[blue]   等待 Gateway 服务就绪...[/blue]")
        for i in range(max_attempts):
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    console.print(f"[green]✅ Gateway 已就绪 (耗时 {(i + 1) * 0.5:.1f}秒)[/green]")
                    return True
            except requests.RequestException:
                pass
            # 每 10 秒输出一次状态
            if (i + 1) % 20 == 0:
                console.print(
                    f"[blue]   等待 Gateway 响应... ({(i + 1) * 0.5:.0f}/{max_attempts * 0.5:.0f}秒)[/blue]"
                )
                # 检查进程是否还在
                if self.gateway_pid_file.exists():
                    try:
                        pid = int(self.gateway_pid_file.read_text().strip())
                        if not psutil.pid_exists(pid):
                            console.print("[red]❌ Gateway 进程已退出[/red]")
                            # 输出日志帮助调试
                            if self.gateway_log_file.exists():
                                console.print("[yellow]Gateway 日志（最后 20 行）:[/yellow]")
                                try:
                                    lines = self.gateway_log_file.read_text().splitlines()
                                    for line in lines[-20:]:
                                        console.print(f"[dim]  {line}[/dim]")
                                except Exception:
                                    pass
                            return False
                    except Exception:
                        pass
            time.sleep(0.5)

        # 超时，检查进程状态
        console.print("[yellow]⚠️ Gateway 启动超时[/yellow]")
        if self.gateway_pid_file.exists():
            try:
                pid = int(self.gateway_pid_file.read_text().strip())
                if psutil.pid_exists(pid):
                    console.print(f"[yellow]   进程仍在运行 (PID: {pid})，可能仍在初始化[/yellow]")
                    # 输出日志帮助调试
                    if self.gateway_log_file.exists():
                        console.print("[yellow]   Gateway 日志（最后 30 行）:[/yellow]")
                        try:
                            lines = self.gateway_log_file.read_text().splitlines()
                            for line in lines[-30:]:
                                console.print(f"[dim]  {line}[/dim]")
                        except Exception:
                            pass
                    return True  # 进程还在，可能只是启动慢
                else:
                    console.print("[red]❌ Gateway 进程已退出[/red]")
                    return False
            except Exception:
                pass
        return False

    def _stop_gateway(self) -> bool:
        pid = self._is_gateway_running()
        if not pid:
            console.print("[yellow]gateway 未运行[/yellow]")
            return True

        console.print(f"[blue]🛑 停止 sage-gateway (PID: {pid})...[/blue]")
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
            else:
                # Try to kill process group first
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGTERM)
                except (ProcessLookupError, OSError):
                    # Fallback to killing PID directly
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass

                # Wait for process to exit
                for _ in range(10):
                    if not psutil.pid_exists(pid):
                        break
                    time.sleep(0.5)

                if psutil.pid_exists(pid):
                    console.print("[yellow]⚠️  Gateway 未响应 SIGTERM，尝试强制停止...[/yellow]")
                    try:
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            pass

            # Double check port release
            import socket

            port_free = False
            for _ in range(10):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(("localhost", self.gateway_port)) != 0:
                        port_free = True
                        break
                time.sleep(0.5)

            # If port is still in use, check if another process took it (or zombie/orphan)
            if not port_free:
                console.print(
                    f"[yellow]⚠️  端口 {self.gateway_port} 仍被占用，检查残留进程...[/yellow]"
                )
                try:
                    for proc in psutil.process_iter(["pid", "name"]):
                        try:
                            for conn in proc.connections(kind="inet"):
                                if conn.laddr.port == self.gateway_port:
                                    console.print(
                                        f"[yellow]⚠️  发现残留进程 {proc.pid} ({proc.name()}) 占用端口，强制清理...[/yellow]"
                                    )
                                    proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception:
                    pass

            self.gateway_pid_file.unlink(missing_ok=True)
            console.print("[green]✅ gateway 已停止[/green]")
            return True
        except Exception as exc:
            console.print(f"[red]❌ 停止 gateway 失败: {exc}")
            return False

    # ------------------------------------------------------------------
    # Auto-Scaling Logic
    # ------------------------------------------------------------------
    def _get_gpu_memory(self) -> list[dict[str, int]]:
        """Get GPU memory info for all GPUs.

        Returns:
            List of dicts: [{'index': 0, 'total': 81920, 'free': 81920}, ...]
        """
        try:
            # Check if nvidia-smi exists
            if shutil.which("nvidia-smi") is None:
                return []

            # Get info for all GPUs
            output = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=index,memory.total,memory.free",
                    "--format=csv,noheader,nounits",
                ],
                encoding="utf-8",
            )

            gpus = []
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(",")
                if len(parts) >= 3:
                    gpus.append(
                        {
                            "index": int(parts[0].strip()),
                            "total": int(parts[1].strip()),
                            "free": int(parts[2].strip()),
                        }
                    )

            return gpus
        except Exception:
            return []

    def _get_used_llm_ports(self) -> set[int]:
        ports: set[int] = set()
        try:
            from sage.llm import LLMLauncher

            for service in LLMLauncher.discover_running_services():
                service_port = service.get("port")
                if service_port is not None:
                    ports.add(int(service_port))
        except ImportError:
            pass
        return ports

    def _find_free_llm_port(self, start_port: int, used_ports: set[int]) -> int | None:
        """Return the next available TCP port for LLM services (clamped to 8901-8910)."""
        from sage.common.config.ports import SagePorts

        port = max(start_port, SagePorts.BENCHMARK_LLM)
        max_port = SagePorts.BENCHMARK_LLM + 9  # 8901-8910 inclusive
        while port <= max_port:
            if port not in used_ports and not self._is_port_in_use(port):
                return port
            port += 1
        return None

    def _auto_start_llms(self, start_port: int | None = None) -> bool:
        """Automatically start multiple LLMs to fill GPU memory."""
        gpus = self._get_gpu_memory()
        if not gpus:
            return False

        total_system_mem = sum(g["total"] for g in gpus)
        free_system_mem = sum(g["free"] for g in gpus)

        console.print(
            f"[blue]🧠 检测到 {len(gpus)} 个 GPU: 总计 {total_system_mem} MB, 可用 {free_system_mem} MB[/blue]"
        )
        for gpu in gpus:
            console.print(
                f"[dim]   GPU {gpu['index']}: {gpu['free']} MB free / {gpu['total']} MB total[/dim]"
            )

        console.print("[blue]🚀 正在根据显存自动调度模型 (Auto-Scaling)...[/blue]")

        # Candidates: Name, Approx Memory (MB) (BF16 + Cache overhead)
        # 32B ~ 65GB, 14B ~ 30GB, 7B ~ 16GB, 1.5B ~ 4GB, 0.5B ~ 2GB
        candidates = [
            ("Qwen/Qwen2.5-32B-Instruct", 65000),
            ("Qwen/Qwen2.5-14B-Instruct", 30000),
            ("Qwen/Qwen2.5-7B-Instruct", 16000),
            ("Qwen/Qwen2.5-1.5B-Instruct", 4000),
            ("Qwen/Qwen2.5-0.5B-Instruct", 2000),
        ]

        started_count = 0
        current_port = start_port or self.llm_port  # 8901 default
        used_ports = self._get_used_llm_ports()

        try:
            from sage.llm import LLMLauncher
        except ImportError:
            console.print("[yellow]⚠️  sageLLM 不可用，跳过自动调度[/yellow]")
            return False

        for model_name, required_mem in candidates:
            # Sort GPUs by free memory descending (to match api_server.py selection logic)
            gpus.sort(key=lambda x: x["free"], reverse=True)

            # Try to find a GPU that fits the model
            target_gpu = None
            for gpu in gpus:
                # Check if we have enough remaining memory (leave 2GB buffer)
                if gpu["free"] > (required_mem + 2000):
                    target_gpu = gpu
                    break

            if target_gpu:
                # vLLM gpu_memory_utilization is based on TOTAL memory of the specific GPU
                # Add 4GB buffer to utilization to ensure enough space for KV cache + overhead
                utilization = (required_mem + 4000) / target_gpu["total"]
                # Cap at 0.95 to be safe (vLLM default is 0.9)
                if utilization > 0.95:
                    utilization = 0.95
                # Min utilization 0.1
                if utilization < 0.1:
                    utilization = 0.1

                next_port = self._find_free_llm_port(current_port, used_ports)
                if next_port is None:
                    console.print("[yellow]⚠️  没有可用端口用于新的 LLM 服务，停止自动调度[/yellow]")
                    break

                console.print(
                    f"[blue]   尝试启动 {model_name} (端口 {next_port}, 显存 {utilization:.1%})...[/blue]"
                )

                try:
                    result = LLMLauncher.launch(
                        model=model_name,
                        port=next_port,
                        gpu_memory=utilization,
                        background=True,
                        verbose=True,
                        check_existing=True,
                    )

                    if result.success:
                        console.print(f"[green]✅ {model_name} 启动成功[/green]")
                        # Update virtual free memory for the target GPU
                        target_gpu["free"] -= required_mem
                        used_ports.add(next_port)
                        started_count += 1
                        current_port = next_port + 1  # Increment port for next model

                        # If this was the first one, set it as self.llm_service
                        if self.llm_service is None:
                            self.llm_service = result.server
                    else:
                        console.print(f"[yellow]⚠️ {model_name} 启动失败，尝试下一个...[/yellow]")

                except Exception as e:
                    console.print(f"[red]❌ 启动 {model_name} 出错: {e}[/red]")

        if started_count > 0:
            console.print(f"[green]✨ 自动调度完成，共启动 {started_count} 个模型[/green]")
            return True

        console.print("[yellow]⚠️ 自动调度未启动任何模型 (可能是显存不足)[/yellow]")
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(
        self,
        frontend_port: int | None = None,
        backend_port: int | None = None,
        gateway_port: int | None = None,
        host: str = "localhost",
        dev: bool = True,
        llm: bool | None = None,
        llm_model: str | None = None,
        use_finetuned: bool = False,
        skip_confirm: bool = False,
        no_embedding: bool = False,
    ) -> bool:
        """Start Studio Chat Mode services.

        Args:
            frontend_port: Studio frontend port
            backend_port: Studio backend port
            gateway_port: Gateway API port (default: 8000)
            host: Host to bind to
            dev: Run in development mode
            llm: Enable local LLM service via sageLLM (default: from SAGE_STUDIO_LLM env)
            llm_model: Model to load (default: from SAGE_STUDIO_LLM_MODEL env)
            use_finetuned: Use latest fine-tuned model (overrides llm_model if True)
            skip_confirm: Skip all interactive confirmations (for CI/CD)
            no_embedding: Disable Embedding service (for CI/CD without GPU)

        Returns:
            True if all services started successfully
        """
        if gateway_port:
            self.gateway_port = gateway_port

        # Determine if local LLM should be started
        start_llm = llm if llm is not None else self.llm_enabled

        # DEBUG
        console.print(
            f"[dim]DEBUG: llm arg={llm}, llm_enabled={self.llm_enabled}, start_llm={start_llm}[/dim]"
        )

        # Force disable LLM if no GPU is detected (vLLM requires GPU)
        if start_llm and not is_gpu_available():
            console.print("[yellow]⚠️  未检测到 NVIDIA GPU，自动禁用本地 LLM 服务[/yellow]")
            console.print("[dim]   提示：vLLM 需要 NVIDIA GPU 支持[/dim]")
            start_llm = False

        # Start local LLM service first (if enabled)
        if start_llm:
            llm_started = False

            # Check if user requested specific model or finetuned
            is_specific_request = (llm_model is not None) or use_finetuned

            # Try Auto-Scaling if:
            # 1. No specific model requested
            # 2. GPU is available
            # 3. No existing service running (to avoid conflicts)
            if not is_specific_request and is_gpu_available():
                is_running, existing_url = self._detect_existing_llm_service()
                should_auto_scale = False
                if not is_running:
                    should_auto_scale = True
                else:
                    prompt_msg = (
                        f"[cyan]检测到已有 LLM 服务 ({existing_url}). 仍要继续自动扩容更多模型吗？[/cyan]"
                        if existing_url
                        else "[cyan]检测到已有 LLM 服务。仍要继续自动扩容更多模型吗？[/cyan]"
                    )
                    if skip_confirm:
                        should_auto_scale = True
                    else:
                        try:
                            from rich.prompt import Confirm

                            should_auto_scale = Confirm.ask(prompt_msg, default=False)
                        except ImportError:
                            should_auto_scale = False

                if should_auto_scale:
                    starting_port = self._find_free_llm_port(
                        self.llm_port, self._get_used_llm_ports()
                    )
                    llm_started = self._auto_start_llms(start_port=starting_port or self.llm_port)

            # Fallback / Standard Mode
            # If auto-scaling skipped or failed, use standard start logic
            if not llm_started:
                model = llm_model or self.llm_model if not use_finetuned else None
                llm_started = self._start_llm_service(model=model, use_finetuned=use_finetuned)

            if llm_started:
                console.print(
                    "[green]💡 Gateway 将自动使用本地 LLM 服务（通过 UnifiedInferenceClient 自动检测）[/green]"
                )
            else:
                console.print(
                    "[yellow]⚠️  本地 LLM 未启动，Gateway 将使用云端 API（如已配置）[/yellow]"
                )

        # Start Embedding service (needed for knowledge indexing, independent of LLM)
        if not no_embedding:
            self._start_embedding_service()
        else:
            console.print("[yellow]⚠️  Embedding 服务已禁用 (--no-embedding)[/yellow]")

        # Start Gateway
        if not self._start_gateway(port=self.gateway_port):
            return False

        # Start Studio UI (use parent class method)
        console.print("[blue]⚙️ 启动 Studio 服务...[/blue]")
        success = super().start(
            port=frontend_port,
            host=host,
            dev=dev,
            backend_port=backend_port,
            auto_gateway=False,  # We manage gateway ourselves
            skip_confirm=skip_confirm,  # Pass through for auto-confirm in CI/CD
        )

        if success:
            console.print("\n" + "=" * 70)
            console.print("[green]🎉 Chat 模式就绪！[/green]")
            if start_llm and self.llm_service:
                console.print("[green]🤖 本地 LLM: 由 sageLLM 管理[/green]")
            console.print(f"[green]🌐 Gateway API: http://localhost:{self.gateway_port}[/green]")
            console.print("[green]💬 打开顶部 Chat 标签即可体验[/green]")
            console.print("=" * 70)

        return success

    def stop(self, stop_infrastructure: bool = False) -> bool:
        """Stop Studio Chat Mode services.

        Args:
            stop_infrastructure: If True, also stop LLM and Embedding services.
                               If False (default), leave them running.
        """
        frontend_backend = super().stop(stop_gateway=False)  # Don't stop gateway via parent
        gateway = self._stop_gateway()

        llm = True
        embedding = True

        if stop_infrastructure:
            llm = self._stop_llm_service(force=True)
            embedding = self._stop_embedding_service(force=True)
        else:
            # Inform user that infrastructure is preserved
            console.print("[dim]ℹ️  保留 LLM/Embedding 服务运行 (使用 --all 停止所有)[/dim]")

        return frontend_backend and gateway and llm and embedding

    def status(self):
        """Display status of all Studio Chat Mode services."""
        super().status()  # Show Studio status first

        # Local LLM Service status - check via HTTP instead of self.llm_service
        llm_table = Table(title="本地 LLM 服务状态（sageLLM）")
        llm_table.add_column("属性", style="cyan", width=14)
        llm_table.add_column("值", style="white")

        # Scan for running LLMs on ports 8901-8910
        found_llms = []
        for port in range(8901, 8911):
            try:
                resp = requests.get(f"http://127.0.0.1:{port}/v1/models", timeout=0.5)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    if models:
                        model_name = models[0].get("id", "unknown")
                        found_llms.append({"port": port, "model": model_name})
            except Exception:
                pass

        if found_llms:
            for i, llm in enumerate(found_llms):
                if i > 0:
                    llm_table.add_section()
                llm_table.add_row("状态", "[green]运行中[/green]")
                llm_table.add_row("端口", str(llm["port"]))
                llm_table.add_row("模型", llm["model"])
                if i == 0:
                    llm_table.add_row("说明", "由 UnifiedInferenceClient 自动检测使用")
        else:
            llm_table.add_row("状态", "[red]未运行[/red]")
            llm_table.add_row("端口", str(SagePorts.BENCHMARK_LLM))
            llm_table.add_row("提示", "默认启动本地服务 (除非指定 --no-llm)")

        console.print(llm_table)

        # Embedding Service status
        embedding_table = Table(title="Embedding 服务状态")
        embedding_table.add_column("属性", style="cyan", width=14)
        embedding_table.add_column("值", style="white")

        embedding_port = SagePorts.EMBEDDING_DEFAULT
        try:
            resp = requests.get(f"http://127.0.0.1:{embedding_port}/v1/models", timeout=2)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                model_name = models[0].get("id", "unknown") if models else "unknown"
                embedding_table.add_row("状态", "[green]运行中[/green]")
                embedding_table.add_row("端口", str(embedding_port))
                embedding_table.add_row("模型", model_name)
            else:
                embedding_table.add_row("状态", "[red]未运行[/red]")
                embedding_table.add_row("端口", str(embedding_port))
        except Exception:
            embedding_table.add_row("状态", "[red]未运行[/red]")
            embedding_table.add_row("端口", str(embedding_port))
            embedding_table.add_row("提示", "将随 LLM 服务自动启动")

        console.print(embedding_table)

        # Gateway status
        table = Table(title="sage-gateway 状态")
        table.add_column("属性", style="cyan", width=14)
        table.add_column("值", style="white")

        pid = self._is_gateway_running()
        if pid:
            table.add_row("状态", "[green]运行中[/green]")
            table.add_row("PID", str(pid))
            url = f"http://127.0.0.1:{self.gateway_port}/health"
            try:
                response = requests.get(url, timeout=1)
                status = response.json().get("status", "unknown")
                table.add_row("健康检查", status)
            except requests.RequestException:
                table.add_row("健康检查", "[red]不可达[/red]")
            table.add_row("端口", str(self.gateway_port))
            table.add_row("日志", str(self.gateway_log_file))
        else:
            table.add_row("状态", "[red]未运行[/red]")
            table.add_row("端口", str(self.gateway_port))
            table.add_row("日志", str(self.gateway_log_file))

        console.print(table)

    def logs(self, follow: bool = False, gateway: bool = False, backend: bool = False):
        """Display logs from Studio services.

        Args:
            follow: Follow log output (like tail -f)
            gateway: Show Gateway logs
            backend: Show Studio backend logs
        """
        if gateway:
            log_file = self.gateway_log_file
            name = "gateway"
        elif backend:
            log_file = self.backend_log_file
            name = "Studio Backend"
        else:
            log_file = self.log_file
            name = "Studio Frontend"

        if not log_file.exists():
            console.print(f"[yellow]{name} 日志不存在: {log_file}[/yellow]")
            return

        if follow:
            console.print(f"[blue]跟踪 {name} 日志 (Ctrl+C 退出)...[/blue]")
            try:
                subprocess.run(["tail", "-f", str(log_file)])
            except KeyboardInterrupt:
                console.print("\n[blue]停止日志跟踪[/blue]")
        else:
            console.print(f"[blue]显示 {name} 日志: {log_file}[/blue]")
            try:
                with open(log_file) as handle:
                    for line in handle.readlines()[-50:]:
                        print(line.rstrip())
            except OSError as exc:
                console.print(f"[red]读取日志失败: {exc}")
