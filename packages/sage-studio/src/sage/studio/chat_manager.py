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
from rich.table import Table

from sage.common.config.ports import SagePorts

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
    # Local LLM Service helpers (via sageLLM LLMLauncher)
    # ------------------------------------------------------------------
    def _start_llm_service(self, model: str | None = None, use_finetuned: bool = False) -> bool:
        """Start local LLM service via sageLLM.

        Uses sageLLM's unified LLMLauncher to start a local LLM HTTP server.
        The server provides OpenAI-compatible API at http://localhost:{port}/v1

        Args:
            model: Model name/path to load (can be HF model or local path)
            use_finetuned: If True, try to use a fine-tuned model

        Returns:
            True if started successfully, False otherwise
        """
        try:
            from sage.common.components.sage_llm import LLMLauncher
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

    def _start_gateway(self, port: int | None = None) -> bool:
        if self._is_gateway_running():
            console.print("[green]✅ sage-gateway 已运行[/green]")
            return True

        # Skip slow import check - just try to start directly
        # If gateway is not installed, subprocess will fail anyway
        gateway_port = port or self.gateway_port
        env = os.environ.copy()
        env.setdefault("SAGE_GATEWAY_PORT", str(gateway_port))

        console.print(f"[blue]🚀 启动 sage-gateway (端口: {gateway_port})...[/blue]")
        try:
            log_handle = open(self.gateway_log_file, "w")
            process = subprocess.Popen(
                [sys.executable, "-m", "sage.gateway.server"],
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
        use_finetuned: bool = False,
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
            model = llm_model or self.llm_model if not use_finetuned else None
            llm_started = self._start_llm_service(model=model, use_finetuned=use_finetuned)
            if llm_started:
                console.print(
                    "[green]💡 Gateway 将自动使用本地 LLM 服务（通过 IntelligentLLMClient 自动检测）[/green]"
                )
            else:
                console.print(
                    "[yellow]⚠️  本地 LLM 未启动，Gateway 将使用云端 API（如已配置）[/yellow]"
                )

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

    def stop(self) -> bool:
        """Stop all Studio Chat Mode services."""
        frontend_backend = super().stop(stop_gateway=False)  # Don't stop gateway via parent
        gateway = self._stop_gateway()
        llm = self._stop_llm_service()
        return frontend_backend and gateway and llm

    def status(self):
        """Display status of all Studio Chat Mode services."""
        super().status()  # Show Studio status first

        # Local LLM Service status (via sageLLM)
        llm_table = Table(title="本地 LLM 服务状态（sageLLM）")
        llm_table.add_column("属性", style="cyan", width=14)
        llm_table.add_column("值", style="white")

        if self.llm_service:
            llm_table.add_row("状态", "[green]运行中[/green]")
            llm_table.add_row("引擎", "sageLLM (可配置不同 vendor)")
            llm_table.add_row("模型", self.llm_model)
            llm_table.add_row("说明", "由 IntelligentLLMClient 自动检测使用")
        else:
            llm_table.add_row("状态", "[red]未运行[/red]")
            llm_table.add_row("提示", "使用 --llm 启动本地服务")
            llm_table.add_row("说明", "支持通过 sageLLM 配置不同推理引擎")

        console.print(llm_table)

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
