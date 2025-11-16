"""Chat Mode Manager - orchestrates gateway + studio backend/frontend"""

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

from .studio_manager import StudioManager

console = Console()


class ChatModeManager:
    """Manage services required for Studio Chat Mode."""

    def __init__(self):
        self.studio_manager = StudioManager()
        self.chat_dir = Path.home() / ".sage" / "studio" / "chat"
        self.gateway_pid_file = self.chat_dir / "gateway.pid"
        self.gateway_log_file = self.chat_dir / "gateway.log"
        self.gateway_port = 8000
        self.gateway_host = "0.0.0.0"
        self.chat_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Gateway helpers
    # ------------------------------------------------------------------
    def _ensure_gateway_importable(self) -> bool:
        try:
            import sage.gateway.server  # noqa: F401

            return True
        except ImportError as exc:  # pragma: no cover - user guidance path
            console.print(
                "[red]无法导入 sage-gateway 包[/red]\n"
                "请先在当前环境中安装: pip install -e packages/sage-gateway",
            )
            console.print(f"详细错误: {exc}")
            return False

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

        if not self._ensure_gateway_importable():
            return False

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
    ) -> bool:
        if gateway_port:
            self.gateway_port = gateway_port

        if not self._start_gateway(port=self.gateway_port):
            return False

        console.print("[blue]⚙️ 启动 Studio 服务...[/blue]")
        success = self.studio_manager.start(
            port=frontend_port,
            host=host,
            dev=dev,
            backend_port=backend_port,
        )
        if success:
            console.print("[green]🎉 Chat 模式就绪！打开顶部 Chat 标签即可体验[/green]")
        return success

    def stop(self) -> bool:
        frontend_backend = self.studio_manager.stop()
        gateway = self._stop_gateway()
        return frontend_backend and gateway

    def status(self):
        self.studio_manager.status()

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
        if gateway:
            log_file = self.gateway_log_file
            name = "gateway"
        elif backend:
            log_file = self.studio_manager.backend_log_file
            name = "Studio Backend"
        else:
            log_file = self.studio_manager.log_file
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
