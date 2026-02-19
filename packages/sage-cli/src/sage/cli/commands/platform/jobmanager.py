#!/usr/bin/env python3
"""
SAGE JobManager CLI

This module provides CLI commands to manage the JobManager lifecycle using Typer.
"""

import os
import subprocess
import sys
import time
from typing import Any

import psutil  # type: ignore[import-untyped]
import typer

# 导入系统工具模块
from sage.cli.management.config_manager import ConfigManager
from sage.common.utils.system.network import (
    aggressive_port_cleanup,
    check_port_binding_permission,
    find_port_processes,
    send_tcp_health_check,
    wait_for_port_release,
)
from sage.common.utils.system.process import (
    create_sudo_manager,
    find_processes_by_name,
    get_process_info,
    kill_process_with_sudo,
    terminate_process,
)

app = typer.Typer(
    name="jobmanager",
    help="Manage the SAGE JobManager service 🚀",
    no_args_is_help=True,
)


class JobManagerController:
    """JobManager控制器"""

    def __init__(self, host: str = "0.0.0.0", port: int = 19001):
        self.host = host
        self.port = port
        self.process_names = ["job_manager.py", "jobmanager_daemon.py"]
        self.sudo_manager = create_sudo_manager()

    def _get_ray_address(self) -> str | None:
        """从 cluster.yaml 获取集群地址"""
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            head_config = config.get("head", {})
            head_host = head_config.get("host", "localhost")
            head_port = head_config.get("head_port", 6379)
            return f"{head_host}:{head_port}"
        except Exception:
            return None

    def check_health(self) -> dict[str, Any]:
        """检查JobManager健康状态"""
        request = {"action": "health_check", "request_id": "cli_health_check"}

        return send_tcp_health_check(self.host, self.port, request, timeout=5)

    def stop_gracefully(self, timeout: int = 30) -> bool:
        """优雅地停止JobManager"""
        typer.echo(f"Attempting graceful shutdown of JobManager on {self.host}:{self.port}...")

        # 首先尝试通过健康检查确认服务存在
        health = self.check_health()
        if health.get("status") != "success":
            typer.echo("JobManager is not responding to health checks")
            return self.force_kill()

        # 查找进程
        processes = find_processes_by_name(self.process_names) or find_port_processes(self.port)
        if not processes:
            typer.echo("No JobManager processes found")
            return True

        typer.echo(f"Found {len(processes)} JobManager process(es)")

        # 发送SIGTERM信号进行优雅关闭
        for proc in processes:
            try:
                typer.echo(f"Sending SIGTERM to process {proc.pid}")
                proc.terminate()
            except psutil.NoSuchProcess:
                continue

        # 等待进程结束
        typer.echo(f"Waiting up to {timeout} seconds for processes to exit...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            remaining_processes = []
            for proc in processes:
                try:
                    if proc.is_running():
                        remaining_processes.append(proc)
                except psutil.NoSuchProcess:
                    continue

            if not remaining_processes:
                typer.echo("All JobManager processes have exited gracefully")
                return True

            time.sleep(1)

        # 如果还有进程在运行，进行强制终止
        typer.echo("Some processes did not exit gracefully, forcing termination...")
        return self.force_kill()

    def force_kill(self) -> bool:
        """强制杀死JobManager进程"""
        processes = find_processes_by_name(self.process_names)

        # 如果没有找到进程，也尝试通过端口查找
        if not processes:
            typer.echo("No JobManager processes found by process name, checking by port...")
            try:
                # 使用 lsof 或 netstat 查找占用端口的进程
                import subprocess

                result = subprocess.run(
                    ["lsof", "-ti", f":{self.port}"], capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split("\n")
                    for pid_str in pids:
                        try:
                            pid = int(pid_str.strip())
                            process = psutil.Process(pid)
                            processes.append(process)
                            typer.echo(f"Found process using port {self.port}: PID {pid}")
                        except (ValueError, psutil.NoSuchProcess):
                            continue
            except (subprocess.SubprocessError, FileNotFoundError):
                # lsof 不可用，尝试使用 netstat
                try:
                    result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True)
                    if result.returncode == 0:
                        for line in result.stdout.split("\n"):
                            if f":{self.port}" in line and "LISTEN" in line:
                                # 提取PID
                                parts = line.split()
                                if len(parts) > 6 and "/" in parts[6]:
                                    pid_str = parts[6].split("/")[0]
                                    try:
                                        pid = int(pid_str)
                                        process = psutil.Process(pid)
                                        processes.append(process)
                                        typer.echo(
                                            f"Found process using port {self.port}: PID {pid}"
                                        )
                                    except (ValueError, psutil.NoSuchProcess):
                                        continue
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass

        if not processes:
            typer.echo("No JobManager processes to kill")
            return True

        # 检查是否需要sudo权限
        current_user = os.getenv("USER", "unknown")
        needs_sudo = False

        for proc in processes:
            proc_info = get_process_info(proc.pid)
            proc_user = proc_info.get("user", "N/A")
            if proc_user != current_user and proc_user != "N/A":
                needs_sudo = True
                break

        # 如果需要sudo权限但还没有获取，先获取
        if needs_sudo and not self.sudo_manager.has_sudo_access():
            typer.echo("⚠️  Some processes are owned by other users, requesting sudo access...")
            if not self.sudo_manager.ensure_sudo_access():
                typer.echo(
                    "❌ Unable to obtain sudo privileges. Cannot kill processes owned by other users."
                )
                typer.echo(
                    "💡 Suggestion: Run this command as root or ask the process owner to stop the service."
                )
                return False

        typer.echo(f"🔪 Force killing {len(processes)} JobManager process(es)...")

        killed_count = 0

        for proc in processes:
            proc_info = get_process_info(proc.pid)
            proc_user = proc_info.get("user", "N/A")

            typer.echo("\n📋 Process Information:")
            typer.echo(f"   PID: {proc_info.get('pid', 'N/A')}")
            typer.echo(f"   Name: {proc_info.get('name', 'N/A')}")
            typer.echo(f"   User: {proc_user}")
            typer.echo(f"   Status: {proc_info.get('status', 'N/A')}")
            typer.echo(f"   Command: {proc_info.get('cmdline', 'N/A')}")

            # 判断是否需要sudo权限
            needs_sudo_for_proc = proc_user != current_user and proc_user != "N/A"
            if needs_sudo_for_proc:
                typer.echo(
                    f"⚠️  Process owned by different user ({proc_user}), using sudo privileges"
                )

            # 使用工具函数终止进程
            result = terminate_process(proc.pid, timeout=5)

            if result["success"]:
                typer.echo(f"✅ Process {proc.pid} {result['message']}")
                killed_count += 1
            else:
                typer.echo(f"❌ {result['error']}")
                # 如果普通终止失败且是权限问题，尝试sudo
                if result.get("method") == "access_denied" and needs_sudo_for_proc:
                    sudo_result = kill_process_with_sudo(
                        proc.pid, self.sudo_manager.get_cached_password()
                    )
                    if sudo_result["success"]:
                        typer.echo(f"✅ Process {proc.pid} killed with sudo privileges")
                        killed_count += 1
                    else:
                        typer.echo(
                            f"❌ Failed to kill process {proc.pid} even with sudo: {sudo_result['error']}"
                        )

        # 再次检查是否还有残留进程
        typer.echo("\n🔍 Checking for remaining processes...")
        time.sleep(2)
        remaining = find_processes_by_name(self.process_names)

        if remaining:
            typer.echo(f"⚠️  Warning: {len(remaining)} processes may still be running")
            # 显示残留进程信息
            for proc in remaining:
                proc_info = get_process_info(proc.pid)
                typer.echo(
                    f"   Remaining: PID {proc_info.get('pid', 'N/A')}, User: {proc_info.get('user', 'N/A')}, Name: {proc_info.get('name', 'N/A')}"
                )
            return killed_count > 0  # 如果至少杀死了一些进程，认为部分成功

        typer.echo("✅ All JobManager processes have been terminated")
        return True

    def start(self, daemon: bool = True, wait_for_ready: int = 10, force: bool = False) -> bool:
        """启动JobManager"""
        typer.echo(f"Starting JobManager on {self.host}:{self.port}...")

        # 如果使用force模式，预先获取sudo权限
        if force:
            self.sudo_manager.ensure_sudo_access()

        # 检查端口是否已被占用
        if self.is_port_occupied():
            typer.echo(f"Port {self.port} is already occupied")

            if force:
                typer.echo("🔥 Force mode enabled, forcefully stopping existing process...")
                typer.echo("⚠️  This will terminate processes owned by other users if necessary.")
                if not self.force_kill():
                    typer.echo("❌ Failed to force kill existing processes")
                    return False

                # 等待端口释放
                if not wait_for_port_release(self.host, self.port, timeout=15):
                    typer.echo("❌ Port is still occupied after force kill")
                    # 尝试更激进的端口清理
                    typer.echo("🔧 Attempting aggressive port cleanup...")
                    aggressive_port_cleanup(self.port)
                    if not wait_for_port_release(self.host, self.port, timeout=5):
                        typer.echo("❌ Unable to free the port, startup may fail")
            else:
                health = self.check_health()
                if health.get("status") == "success":
                    typer.echo("JobManager is already running and healthy")
                    return True
                else:
                    typer.echo(
                        "Port occupied but JobManager not responding, stopping existing process..."
                    )
                    if not self.stop_gracefully():
                        return False
                    # 等待端口释放
                    wait_for_port_release(self.host, self.port, timeout=10)

        # 检查端口绑定权限
        if not check_port_binding_permission(self.host, self.port):
            typer.echo("❌ Cannot bind to port, startup will fail")
            typer.echo("💡 Suggestion: Try using a different port with --port option")
            return False

        # 在 start 方法的开头添加：
        typer.echo(f"Using Python interpreter: {sys.executable}")
        # 构建启动命令
        jobmanager_module = "sage.kernel.runtime.job_manager"
        cmd = [
            sys.executable,
            "-m",
            jobmanager_module,
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]

        # 准备环境变量，设置 RAY_ADDRESS 以连接到集群
        env = os.environ.copy()
        ray_address = self._get_ray_address()
        if ray_address:
            env["RAY_ADDRESS"] = ray_address
            typer.echo(f"Setting RAY_ADDRESS={ray_address} for cluster connection")
        else:
            typer.echo("⚠️  Could not determine cluster address from config")

        try:
            # 启动JobManager进程
            if daemon:
                # 作为守护进程启动
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    start_new_session=True,
                    env=env,
                )
                typer.echo(f"JobManager started as daemon process (PID: {process.pid})")
            else:
                # 在前台启动
                typer.echo("Starting JobManager in foreground mode...")
                process = subprocess.Popen(cmd, env=env)
                typer.echo(f"JobManager started in foreground (PID: {process.pid})")
                return True  # 前台模式直接返回

            # 等待服务就绪
            if wait_for_ready > 0:
                typer.echo(f"Waiting up to {wait_for_ready} seconds for JobManager to be ready...")
                for i in range(wait_for_ready):
                    time.sleep(1)
                    health = self.check_health()
                    if health.get("status") == "success":
                        typer.echo(f"JobManager is ready and healthy (took {i + 1} seconds)")
                        return True
                    typer.echo(f"Waiting... ({i + 1}/{wait_for_ready})")

                typer.echo("JobManager did not become ready within timeout")
                # 检查进程是否还在运行
                try:
                    if process.poll() is None:
                        typer.echo("Process is still running but not responding to health checks")
                        typer.echo("This might indicate a startup issue")
                    else:
                        typer.echo(f"Process exited with code: {process.returncode}")
                        # 尝试获取错误输出
                        _, stderr = process.communicate(timeout=1)
                        if stderr:
                            typer.echo(f"Process stderr: {stderr.decode()}")
                except Exception:
                    pass
                return False

            return True

        except Exception as e:
            typer.echo(f"Failed to start JobManager: {e}")
            return False

    def is_port_occupied(self) -> bool:
        """检查端口是否被占用"""
        from sage.common.utils.system.network import is_port_occupied as check_port_occupied

        return check_port_occupied(self.host, self.port)

    def status(self) -> dict[str, Any]:
        """获取JobManager状态"""
        typer.echo(f"Checking JobManager status on {self.host}:{self.port}...")

        # 检查健康状态
        health = self.check_health()

        # 查找进程
        processes = find_processes_by_name(self.process_names)

        # 检查端口占用
        port_occupied = self.is_port_occupied()

        status_info = {
            "health": health,
            "processes": [{"pid": p.pid, "name": p.name()} for p in processes],
            "port_occupied": port_occupied,
            "host_port": f"{self.host}:{self.port}",
        }

        # 打印状态信息
        typer.echo(f"Health Status: {health.get('status', 'unknown')}")
        if health.get("status") == "success":
            daemon_status = health.get("daemon_status", {})
            typer.echo(f"  - Jobs Count: {daemon_status.get('jobs_count', 'unknown')}")
            typer.echo(f"  - Session ID: {daemon_status.get('session_id', 'unknown')}")

        typer.echo(f"Process Count: {len(processes)}")
        for proc_info in status_info["processes"]:
            proc_pid = proc_info["pid"]
            try:
                proc = psutil.Process(proc_pid)
                proc_user = proc.username()
                proc_cmdline = " ".join(proc.cmdline())
                typer.echo(f"  - PID {proc_pid}: {proc_info['name']} (user: {proc_user})")
                typer.echo(f"    Command: {proc_cmdline}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                typer.echo(f"  - PID {proc_pid}: {proc_info['name']} (process info unavailable)")

        typer.echo(f"Port {self.port} Occupied: {port_occupied}")

        # 如果端口被占用但没有找到JobManager进程，显示占用端口的进程信息
        if port_occupied and not processes:
            typer.echo("Port is occupied by non-JobManager process:")
            try:
                import subprocess

                result = subprocess.run(
                    ["lsof", "-ti", f":{self.port}"], capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split("\n")
                    for pid_str in pids:
                        try:
                            pid = int(pid_str.strip())
                            proc = psutil.Process(pid)
                            proc_user = proc.username()
                            proc_cmdline = " ".join(proc.cmdline())
                            typer.echo(f"  - PID {pid}: {proc.name()} (user: {proc_user})")
                            typer.echo(f"    Command: {proc_cmdline}")
                        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                            typer.echo(f"  - PID {pid_str}: (process info unavailable)")
            except (subprocess.SubprocessError, FileNotFoundError):
                typer.echo("  (Unable to determine which process is using the port)")

        return status_info

    def restart(self, force: bool = False, wait_for_ready: int = 10) -> bool:
        """重启JobManager"""
        typer.echo("=" * 50)
        typer.echo("RESTARTING JOBMANAGER")
        typer.echo("=" * 50)

        # 如果使用force模式，预先获取sudo权限用于停止阶段
        if force:
            typer.echo(
                "🔐 Force restart mode: will use sudo to stop, then start with user privileges"
            )
            self.sudo_manager.ensure_sudo_access()

        # 停止现有实例
        if force:
            typer.echo("🔪 Stopping existing instances with sudo privileges...")
            stop_success = self.force_kill()
        else:
            typer.echo("🛑 Gracefully stopping existing instances...")
            stop_success = self.stop_gracefully()

        if not stop_success:
            typer.echo("❌ Failed to stop existing JobManager instances")
            return False

        # 等待一下确保资源释放
        typer.echo("⏳ Waiting for resources to be released...")
        if force:
            # 强制模式下等待更长时间，并确保端口释放
            time.sleep(3)
            if not wait_for_port_release(self.host, self.port, timeout=10):
                typer.echo("⚠️  Port may still be occupied, attempting aggressive cleanup...")
                aggressive_port_cleanup(self.port)
                wait_for_port_release(self.host, self.port, timeout=5)
        else:
            time.sleep(2)

        # 启动新实例 - 始终使用用户权限，不使用force模式
        # 这确保新的JobManager运行在正确的conda环境中
        typer.echo("🚀 Starting new instance with user privileges (in conda environment)...")
        start_success = self.start(daemon=True, wait_for_ready=wait_for_ready, force=False)

        if start_success:
            typer.echo("=" * 50)
            typer.echo("✅ JOBMANAGER RESTART SUCCESSFUL")
            typer.echo("=" * 50)
        else:
            typer.echo("=" * 50)
            typer.echo("❌ JOBMANAGER RESTART FAILED")
            typer.echo("=" * 50)

        return start_success


@app.command()
def start(
    host: str = typer.Option(
        "0.0.0.0", help="JobManager host address (use 0.0.0.0 for cluster access)"
    ),
    port: int = typer.Option(19001, help="JobManager port"),
    foreground: bool = typer.Option(False, "--foreground", help="Start in the foreground"),
    no_wait: bool = typer.Option(
        False, "--no-wait", help="Do not wait for the service to be ready"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force start by killing any existing JobManager processes",
    ),
):
    """
    Start the JobManager service.
    """
    controller = JobManagerController(host, port)
    wait_time = 0 if no_wait else 10
    success = controller.start(daemon=not foreground, wait_for_ready=wait_time, force=force)
    if success:
        typer.echo("\n✅ Operation 'start' completed successfully")
    else:
        typer.echo("\n❌ Operation 'start' failed")
        raise typer.Exit(code=1)


@app.command()
def stop(
    host: str = typer.Option("0.0.0.0", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force stop by killing any existing JobManager processes",
    ),
):
    """
    Stop the JobManager service.
    """
    controller = JobManagerController(host, port)

    # 如果使用force模式，预先获取sudo权限
    if force:
        typer.echo(
            "🔐 Force stop mode: may require sudo privileges to terminate processes owned by other users."
        )
        controller.sudo_manager.ensure_sudo_access()
        success = controller.force_kill()
    else:
        success = controller.stop_gracefully()

    if success:
        typer.echo("\n✅ Operation 'stop' completed successfully")
    else:
        typer.echo("\n❌ Operation 'stop' failed")
        raise typer.Exit(code=1)


@app.command()
def restart(
    host: str = typer.Option("0.0.0.0", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
    force: bool = typer.Option(False, "--force", "-f", help="Force the restart"),
    no_wait: bool = typer.Option(
        False, "--no-wait", help="Do not wait for the service to be ready"
    ),
):
    """
    Restart the JobManager service.
    """
    controller = JobManagerController(host, port)
    wait_time = 0 if no_wait else 10
    success = controller.restart(force=force, wait_for_ready=wait_time)
    if not success:
        raise typer.Exit(code=1)


@app.command()
def status(
    host: str = typer.Option("0.0.0.0", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
):
    """
    Check the status of the JobManager service.
    """
    controller = JobManagerController(host, port)
    controller.status()
    typer.echo("\n✅ Operation 'status' completed successfully")


@app.command()
def kill(
    host: str = typer.Option("0.0.0.0", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
):
    """
    Force kill the JobManager service.
    """
    controller = JobManagerController(host, port)

    # kill命令总是需要sudo权限，预先获取
    typer.echo(
        "🔐 Kill command: may require sudo privileges to terminate processes owned by other users."
    )
    controller.sudo_manager.ensure_sudo_access()

    success = controller.force_kill()
    if success:
        typer.echo("\n✅ Operation 'kill' completed successfully")
    else:
        typer.echo("\n❌ Operation 'kill' failed")
        raise typer.Exit(code=1)


@app.command("version")
def version_command():
    """Show version information."""
    typer.echo("🚀 SAGE JobManager")
    typer.echo("Version: 1.0.1")
    typer.echo("Author: IntelliStream Team")
    typer.echo("Repository: https://github.com/intellistream/SAGE")


if __name__ == "__main__":
    app()
