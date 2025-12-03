"""Chat Mode Manager - Studio Manager with integrated LLM support"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from sage.common.config.ports import SagePorts

from .studio_manager import StudioManager
from .utils.gpu_check import is_gpu_available

console = Console()


def is_ci_environment() -> bool:
    """Check if running in a CI environment."""
    return bool(
        os.getenv("CI")
        or os.getenv("GITHUB_ACTIONS")
        or os.getenv("GITLAB_CI")
        or os.getenv("JENKINS_URL")
        or os.getenv("TRAVIS")
        or os.getenv("CIRCLECI")
    )


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
        # Use Qwen2.5-0.5B as default - very small and fast
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
            from sage.studio.services.finetune_manager import finetune_manager

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

    # ------------------------------------------------------------------
    # Local LLM Service helpers (via Control Plane or fallback to LLMLauncher)
    # ------------------------------------------------------------------
    def _is_control_plane_running(self, port: int | None = None) -> bool:
        """Check if Control Plane Gateway is running."""
        gateway_port = port or SagePorts.GATEWAY_DEFAULT
        try:
            resp = requests.get(f"http://localhost:{gateway_port}/health", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _start_llm_via_control_plane(
        self,
        model: str,
        gateway_port: int | None = None,
        llm_port: int | None = None,
    ) -> bool:
        """Start LLM engine via Control Plane API.

        Args:
            model: Model name to load
            gateway_port: Gateway port (default: SagePorts.GATEWAY_DEFAULT)
            llm_port: LLM engine port (default: self.llm_port)

        Returns:
            True if started successfully
        """
        gateway_port = gateway_port or SagePorts.GATEWAY_DEFAULT
        llm_port = llm_port or self.llm_port

        api_base = f"http://localhost:{gateway_port}/v1"

        payload = {
            "model_id": model,
            "engine_kind": "llm",
            "port": llm_port,
            "tensor_parallel_size": int(os.getenv("SAGE_STUDIO_LLM_TENSOR_PARALLEL", "1")),
        }

        try:
            resp = requests.post(
                f"{api_base}/management/engines",
                json=payload,
                timeout=120.0,
            )
            if resp.status_code == 200:
                engine_info = resp.json()
                console.print(
                    f"[green]✓[/green] LLM 引擎已通过 Control Plane 启动 "
                    f"(ID: {engine_info.get('engine_id', 'unknown')})"
                )
                return True
            else:
                console.print(f"[yellow]⚠️  Control Plane 启动 LLM 失败: {resp.text}[/yellow]")
                return False
        except Exception as e:
            console.print(f"[yellow]⚠️  Control Plane API 调用失败: {e}[/yellow]")
            return False

    def _start_llm_service(self, model: str | None = None, use_finetuned: bool = False) -> bool:
        """Start local LLM service via Control Plane or fallback to LLMLauncher.

        Uses Control Plane if available, otherwise falls back to sageLLM's
        unified LLMLauncher to start a local LLM HTTP server.

        Args:
            model: Model name/path to load (can be HF model or local path)
            use_finetuned: If True, try to use a fine-tuned model

        Returns:
            True if started successfully, False otherwise
        """
        # Determine which model to use
        model_name = model or self.llm_model

        # Get finetuned models list if needed
        finetuned_models = None
        if use_finetuned and not model:
            finetuned_models = self.list_finetuned_models()
            if not finetuned_models:
                console.print("[yellow]⚠️  未找到可用的微调模型，使用默认模型[/yellow]")
            elif finetuned_models:
                # Use the most recent finetuned model
                model_name = finetuned_models[0]["path"]

        # Check if Control Plane is already running
        if self._is_control_plane_running():
            console.print("[blue]📡 检测到 Control Plane Gateway，通过 API 启动 LLM 引擎[/blue]")
            return self._start_llm_via_control_plane(model_name)

        # Fallback to LLMLauncher
        try:
            from sage.common.components.sage_llm import LLMLauncher
        except ImportError:
            console.print(
                "[yellow]⚠️  sageLLM LLMLauncher 不可用，跳过本地 LLM 启动[/yellow]\n"
                "提示：确保已安装 sage-common 包"
            )
            return False

        # Use unified launcher
        result = LLMLauncher.launch(
            model=model_name,
            port=self.llm_port,
            gpu_memory=float(os.getenv("SAGE_STUDIO_LLM_GPU_MEMORY", "0.7")),
            tensor_parallel=int(os.getenv("SAGE_STUDIO_LLM_TENSOR_PARALLEL", "1")),
            background=True,
            use_finetuned=use_finetuned,
            finetuned_models=finetuned_models,
            verbose=True,
            check_existing=False,  # We handle existing check at Studio level
        )

        if result.success:
            self.llm_service = result.server
            return True
        else:
            console.print("[yellow]💡 提示：安装推理引擎后可使用本地服务[/yellow]")
            console.print("   示例：pip install vllm  # 安装 vLLM 引擎")
            return False

    def _stop_llm_service(self) -> bool:
        """Stop local LLM service."""
        try:
            from sage.common.components.sage_llm import LLMLauncher
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
        return LLMLauncher.stop(verbose=True)

    # ------------------------------------------------------------------
    # Embedding Service helpers
    # ------------------------------------------------------------------
    def _start_embedding_via_control_plane(
        self,
        model: str,
        gateway_port: int | None = None,
        embedding_port: int | None = None,
    ) -> bool:
        """Start Embedding engine via Control Plane API.

        Args:
            model: Embedding model name
            gateway_port: Gateway port (default: SagePorts.GATEWAY_DEFAULT)
            embedding_port: Embedding engine port (default: SagePorts.EMBEDDING_DEFAULT)

        Returns:
            True if started successfully
        """
        gateway_port = gateway_port or SagePorts.GATEWAY_DEFAULT
        embedding_port = embedding_port or SagePorts.EMBEDDING_DEFAULT

        api_base = f"http://localhost:{gateway_port}/v1"

        payload = {
            "model_id": model,
            "engine_kind": "embedding",
            "port": embedding_port,
            "use_gpu": False,  # Embedding 默认不使用 GPU
        }

        try:
            resp = requests.post(
                f"{api_base}/management/engines",
                json=payload,
                timeout=60.0,
            )
            if resp.status_code == 200:
                engine_info = resp.json()
                console.print(
                    f"[green]✓[/green] Embedding 引擎已通过 Control Plane 启动 "
                    f"(ID: {engine_info.get('engine_id', 'unknown')})"
                )
                return True
            else:
                console.print(f"[yellow]⚠️  Control Plane 启动 Embedding 失败: {resp.text}[/yellow]")
                return False
        except Exception as e:
            console.print(f"[yellow]⚠️  Control Plane API 调用失败: {e}[/yellow]")
            return False

    def _start_embedding_service(self, model: str = "BAAI/bge-m3", port: int | None = None) -> bool:
        """Start Embedding service via Control Plane or as a background process.

        Args:
            model: Embedding model name (default: BAAI/bge-m3)
            port: Server port (default: SagePorts.EMBEDDING_DEFAULT = 8090)

        Returns:
            True if started successfully
        """
        if port is None:
            port = SagePorts.EMBEDDING_DEFAULT  # 8090

        # Check if already running
        try:
            resp = requests.get(f"http://localhost:{port}/v1/models", timeout=2)
            if resp.status_code == 200:
                console.print(f"[green]✅ Embedding 服务已在运行 (localhost:{port})[/green]")
                return True
        except Exception:
            pass  # Not running, continue to start

        # Try Control Plane first if available
        if self._is_control_plane_running():
            console.print(
                "[blue]📡 检测到 Control Plane Gateway，通过 API 启动 Embedding 引擎[/blue]"
            )
            return self._start_embedding_via_control_plane(model, embedding_port=port)

        # Fallback to direct process start
        console.print(f"[blue]🎯 启动 Embedding 服务 (模型: {model}, 端口: {port})[/blue]")

        # Ensure log directory exists
        log_dir = Path.home() / ".sage" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        embedding_log = log_dir / "embedding.log"

        embedding_cmd = [
            sys.executable,
            "-m",
            "sage.common.components.sage_embedding.embedding_server",
            "--model",
            model,
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

            # Wait for service to be ready (up to 60 seconds)
            console.print("   [dim]等待服务就绪...[/dim]")
            for i in range(60):
                try:
                    resp = requests.get(f"http://localhost:{port}/v1/models", timeout=1)
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

    def _stop_embedding_service(self) -> bool:
        """Stop Embedding service if running."""
        port = SagePorts.EMBEDDING_DEFAULT
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

        # Also try to find and kill any orphan embedding server processes
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if "embedding_server" in " ".join(cmdline) and str(port) in " ".join(cmdline):
                    console.print(f"[blue]🛑 停止孤儿 Embedding 进程 (PID: {proc.pid})...[/blue]")
                    proc.terminate()
                    proc.wait(timeout=5)
                    stopped = True
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                pass

        return stopped

    # ------------------------------------------------------------------
    # Gateway helpers
    # ------------------------------------------------------------------
    def _is_gateway_running(self) -> int | None:
        if not self.gateway_pid_file.exists():
            return None

        try:
            pid = int(self.gateway_pid_file.read_text().strip())
        except Exception:
            return None

        if psutil.pid_exists(pid):
            return pid

        # 清理脏 PID 文件
        try:
            self.gateway_pid_file.unlink()
        except OSError:
            pass
        return None

    def _start_gateway(self, port: int | None = None, llm_base_url: str | None = None) -> bool:
        if self._is_gateway_running():
            console.print("[green]✅ sage-gateway 已运行[/green]")
            return True

        # Skip slow import check - just try to start directly
        # If gateway is not installed, subprocess will fail anyway
        gateway_port = port or self.gateway_port
        env = os.environ.copy()
        env.setdefault("SAGE_GATEWAY_PORT", str(gateway_port))

        # Pass LLM endpoint to Gateway if local LLM is running
        if llm_base_url:
            env["SAGE_CHAT_BASE_URL"] = llm_base_url
            console.print(f"[dim]   Gateway 将使用 LLM: {llm_base_url}[/dim]")

        console.print(f"[blue]🚀 启动 sage-gateway (端口: {gateway_port})...[/blue]")
        try:
            log_handle = open(self.gateway_log_file, "w")
            process = subprocess.Popen(
                [sys.executable, "-m", "sage.gateway.server"],
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
                "[yellow]提示: 请确保已安装 sage-gateway: "
                "pip install -e packages/sage-gateway[/yellow]"
            )
            return False

        # 等待服务就绪
        url = f"http://localhost:{gateway_port}/health"
        for _ in range(20):
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    console.print("[green]✅ gateway 已就绪[/green]")
                    return True
            except requests.RequestException:
                time.sleep(0.5)
        console.print("[yellow]⚠️ gateway 仍在启动，请稍后检查[/yellow]")
        return True

    def _stop_gateway(self) -> bool:
        pid = self._is_gateway_running()
        if not pid:
            console.print("[yellow]gateway 未运行[/yellow]")
            return True

        console.print("[blue]🛑 停止 sage-gateway...[/blue]")
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
            else:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(1)
                if psutil.pid_exists(pid):
                    os.killpg(os.getpgid(pid), signal.SIGKILL)

            self.gateway_pid_file.unlink(missing_ok=True)
            console.print("[green]✅ gateway 已停止[/green]")
            return True
        except Exception as exc:
            console.print(f"[red]❌ 停止 gateway 失败: {exc}")
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
        embedding: bool | None = None,
        embedding_model: str | None = None,
        use_finetuned: bool = False,
        interactive: bool | None = None,
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
            embedding: Enable Embedding service (default: True when LLM is enabled)
            embedding_model: Embedding model to use (default: BAAI/bge-m3)
            use_finetuned: Use latest fine-tuned model (overrides llm_model if True)
            interactive: Enable interactive mode for engine selection (auto-disabled in CI)

        Returns:
            True if all services started successfully
        """
        if gateway_port:
            self.gateway_port = gateway_port

        # Determine interactive mode (disabled in CI by default)
        is_interactive = interactive if interactive is not None else not is_ci_environment()

        # Interactive engine selection if in interactive mode and not explicit args
        start_llm, start_embedding, llm_model, embedding_model = self._select_engines_interactive(
            llm=llm,
            llm_model=llm_model,
            embedding=embedding,
            embedding_model=embedding_model,
            use_finetuned=use_finetuned,
            interactive=is_interactive,
        )

        # DEBUG
        console.print(f"[dim]DEBUG: start_llm={start_llm}, start_embedding={start_embedding}[/dim]")

        # Force disable LLM if no GPU is detected (vLLM requires GPU)
        if start_llm and not is_gpu_available():
            console.print("[yellow]⚠️  未检测到 NVIDIA GPU，自动禁用本地 LLM 服务[/yellow]")
            console.print("[dim]   提示：vLLM 需要 NVIDIA GPU 支持[/dim]")
            start_llm = False

        # Track LLM URL for Gateway
        llm_base_url: str | None = None

        # Start local LLM service first (if enabled)
        if start_llm:
            model = llm_model if not use_finetuned else None
            llm_started = self._start_llm_service(model=model, use_finetuned=use_finetuned)
            if llm_started:
                # Set LLM URL for Gateway to use
                llm_base_url = f"http://localhost:{self.llm_port}/v1"
                console.print(f"[green]💡 Gateway 将使用本地 LLM 服务: {llm_base_url}[/green]")
            else:
                console.print(
                    "[yellow]⚠️  本地 LLM 未启动，Gateway 将使用云端 API（如已配置）[/yellow]"
                )

        # Start Embedding service (if enabled)
        if start_embedding:
            self._start_embedding_service(model=embedding_model)

        # Start Gateway (pass LLM URL if local service is running)
        if not self._start_gateway(port=self.gateway_port, llm_base_url=llm_base_url):
            return False

        # Start Studio UI (use parent class method)
        console.print("[blue]⚙️ 启动 Studio 服务...[/blue]")
        success = super().start(
            port=frontend_port,
            host=host,
            dev=dev,
            backend_port=backend_port,
            auto_gateway=False,  # We manage gateway ourselves
        )

        if success:
            console.print("\n" + "=" * 70)
            console.print("[green]🎉 Chat 模式就绪！[/green]")
            if start_llm and self.llm_service:
                console.print("[green]🤖 本地 LLM: 由 sageLLM 管理[/green]")
            if start_embedding:
                console.print("[green]📊 Embedding 服务: 已启动[/green]")
            console.print(f"[green]🌐 Gateway API: http://localhost:{self.gateway_port}[/green]")
            console.print("[green]💬 打开顶部 Chat 标签即可体验[/green]")
            console.print("=" * 70)

        return success

    def _select_engines_interactive(
        self,
        llm: bool | None,
        llm_model: str | None,
        embedding: bool | None,
        embedding_model: str | None,
        use_finetuned: bool,
        interactive: bool,
    ) -> tuple[bool, bool, str | None, str | None]:
        """Interactive engine selection.

        Args:
            llm: Explicit LLM enable flag (None = ask user)
            llm_model: Explicit LLM model (None = ask user or use default)
            embedding: Explicit Embedding enable flag (None = ask user)
            embedding_model: Explicit Embedding model (None = use default)
            use_finetuned: Use fine-tuned model
            interactive: Whether to prompt user interactively

        Returns:
            Tuple of (start_llm, start_embedding, llm_model, embedding_model)
        """
        # Default values
        default_llm_model = self.llm_model
        default_embedding_model = "BAAI/bge-m3"

        # If all options are explicitly set, no interaction needed
        if llm is not None and embedding is not None:
            start_llm = llm
            start_embedding = embedding
            final_llm_model = llm_model or default_llm_model
            final_embedding_model = embedding_model or default_embedding_model
            return start_llm, start_embedding, final_llm_model, final_embedding_model

        # Use defaults if not interactive
        if not interactive:
            start_llm = llm if llm is not None else self.llm_enabled
            start_embedding = embedding if embedding is not None else start_llm
            final_llm_model = llm_model or default_llm_model
            final_embedding_model = embedding_model or default_embedding_model
            return start_llm, start_embedding, final_llm_model, final_embedding_model

        # Interactive mode: prompt user
        console.print("\n[cyan]🔧 引擎配置[/cyan]")
        console.print("[dim]提示：在 CI 环境中此交互会被跳过，使用默认配置[/dim]\n")

        # LLM selection
        if llm is None:
            has_gpu = is_gpu_available()
            if has_gpu:
                start_llm = Confirm.ask(
                    "[cyan]启动本地 LLM 服务?[/cyan]",
                    default=self.llm_enabled,
                )
            else:
                console.print("[yellow]⚠️  未检测到 GPU，LLM 服务需要 NVIDIA GPU[/yellow]")
                start_llm = False
        else:
            start_llm = llm

        # LLM model selection (if LLM enabled)
        if start_llm and llm_model is None and not use_finetuned:
            console.print("\n[cyan]可用的 LLM 模型:[/cyan]")
            llm_options = [
                ("1", "Qwen/Qwen2.5-0.5B-Instruct", "轻量级 (0.5B, ~1GB VRAM)"),
                ("2", "Qwen/Qwen2.5-1.5B-Instruct", "小型 (1.5B, ~3GB VRAM)"),
                ("3", "Qwen/Qwen2.5-7B-Instruct", "标准 (7B, ~14GB VRAM)"),
                ("4", "custom", "自定义模型路径"),
            ]
            for opt, model, desc in llm_options:
                marker = "✓" if model == default_llm_model else " "
                console.print(f"  {opt}. [{marker}] {model} - {desc}")

            choice = Prompt.ask(
                "\n[cyan]选择 LLM 模型[/cyan]",
                choices=["1", "2", "3", "4"],
                default="1",
            )

            if choice == "4":
                final_llm_model = Prompt.ask("[cyan]输入模型路径或 HuggingFace ID[/cyan]")
            else:
                final_llm_model = llm_options[int(choice) - 1][1]
        else:
            final_llm_model = llm_model or default_llm_model

        # Embedding selection
        if embedding is None:
            start_embedding = Confirm.ask(
                "[cyan]启动 Embedding 服务?[/cyan]",
                default=start_llm,  # Default to same as LLM
            )
        else:
            start_embedding = embedding

        # Embedding model selection (if enabled)
        if start_embedding and embedding_model is None:
            console.print("\n[cyan]可用的 Embedding 模型:[/cyan]")
            embed_options = [
                ("1", "BAAI/bge-m3", "多语言 (推荐)"),
                ("2", "BAAI/bge-small-zh-v1.5", "中文小型"),
                ("3", "BAAI/bge-large-zh-v1.5", "中文大型"),
                ("4", "custom", "自定义模型"),
            ]
            for opt, model, desc in embed_options:
                marker = "✓" if model == default_embedding_model else " "
                console.print(f"  {opt}. [{marker}] {model} - {desc}")

            choice = Prompt.ask(
                "\n[cyan]选择 Embedding 模型[/cyan]",
                choices=["1", "2", "3", "4"],
                default="1",
            )

            if choice == "4":
                final_embedding_model = Prompt.ask("[cyan]输入模型名称[/cyan]")
            else:
                final_embedding_model = embed_options[int(choice) - 1][1]
        else:
            final_embedding_model = embedding_model or default_embedding_model

        # Summary
        console.print("\n[cyan]📋 配置摘要:[/cyan]")
        console.print(f"  • LLM: {'✅ ' + final_llm_model if start_llm else '❌ 禁用'}")
        console.print(
            f"  • Embedding: {'✅ ' + final_embedding_model if start_embedding else '❌ 禁用'}"
        )
        console.print()

        return start_llm, start_embedding, final_llm_model, final_embedding_model

    def stop(self) -> bool:
        """Stop all Studio Chat Mode services."""
        frontend_backend = super().stop(stop_gateway=False)  # Don't stop gateway via parent
        gateway = self._stop_gateway()
        llm = self._stop_llm_service()
        embedding = self._stop_embedding_service()
        return frontend_backend and gateway and llm and embedding

    def status(self):
        """Display status of all Studio Chat Mode services."""
        super().status()  # Show Studio status first

        # Local LLM Service status - check via HTTP instead of self.llm_service
        llm_table = Table(title="本地 LLM 服务状态（sageLLM）")
        llm_table.add_column("属性", style="cyan", width=14)
        llm_table.add_column("值", style="white")

        llm_port = SagePorts.BENCHMARK_LLM  # 8901
        llm_running = False
        llm_model_name = None
        try:
            resp = requests.get(f"http://localhost:{llm_port}/v1/models", timeout=2)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                if models:
                    llm_running = True
                    llm_model_name = models[0].get("id", "unknown")
        except Exception:
            pass

        if llm_running:
            llm_table.add_row("状态", "[green]运行中[/green]")
            llm_table.add_row("端口", str(llm_port))
            llm_table.add_row("模型", llm_model_name or "unknown")
            llm_table.add_row("说明", "由 UnifiedInferenceClient 自动检测使用")
        else:
            llm_table.add_row("状态", "[red]未运行[/red]")
            llm_table.add_row("端口", str(llm_port))
            llm_table.add_row("提示", "使用 --llm 启动本地服务")

        console.print(llm_table)

        # Embedding Service status
        embedding_table = Table(title="Embedding 服务状态")
        embedding_table.add_column("属性", style="cyan", width=14)
        embedding_table.add_column("值", style="white")

        embedding_port = SagePorts.EMBEDDING_DEFAULT
        try:
            resp = requests.get(f"http://localhost:{embedding_port}/v1/models", timeout=2)
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
            url = f"http://localhost:{self.gateway_port}/health"
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
