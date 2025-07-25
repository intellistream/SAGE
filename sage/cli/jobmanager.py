#!/usr/bin/env python3
"""
SAGE JobManager CLI

This module provides CLI commands to manage the JobManager lifecycle using Typer.
"""

import sys
import time
import socket
import json
import psutil
import typer
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path

app = typer.Typer(
    name="jobmanager",
    help="Manage the SAGE JobManager service 🚀",
    no_args_is_help=True
)

class JobManagerController:
    """JobManager控制器"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19001):
        self.host = host
        self.port = port
        self.process_names = ["job_manager.py", "jobmanager_daemon.py", "sage.jobmanager.job_manager"]
        
    def check_health(self) -> Dict[str, Any]:
        """检查JobManager健康状态"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.host, self.port))
                
                # 发送健康检查请求
                request = {
                    "action": "health_check",
                    "request_id": "cli_health_check"
                }
                
                request_data = json.dumps(request).encode('utf-8')
                length_data = len(request_data).to_bytes(4, byteorder='big')
                sock.sendall(length_data + request_data)
                
                # 接收响应
                response_length_data = sock.recv(4)
                if len(response_length_data) != 4:
                    return {"status": "error", "message": "Invalid response"}
                
                response_length = int.from_bytes(response_length_data, byteorder='big')
                response_data = b''
                while len(response_data) < response_length:
                    chunk = sock.recv(min(response_length - len(response_data), 8192))
                    response_data += chunk
                
                response = json.loads(response_data.decode('utf-8'))
                return response
                
        except socket.error as e:
            return {"status": "error", "message": f"Connection failed: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Health check failed: {e}"}
    
    def find_jobmanager_processes(self) -> List[psutil.Process]:
        """查找所有JobManager进程"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline:
                    # 检查命令行参数是否包含任何JobManager进程名
                    has_process_name = any(
                        any(process_name in arg for arg in cmdline) 
                        for process_name in self.process_names
                    )
                    
                    if has_process_name:
                        # 进一步检查是否是我们的JobManager实例（通过端口号）
                        if any(str(self.port) in arg for arg in cmdline):
                            processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return processes
    
    def stop_gracefully(self, timeout: int = 30) -> bool:
        """优雅地停止JobManager"""
        typer.echo(f"Attempting graceful shutdown of JobManager on {self.host}:{self.port}...")
        
        # 首先尝试通过健康检查确认服务存在
        health = self.check_health()
        if health.get("status") != "success":
            typer.echo("JobManager is not responding to health checks")
            return self.force_kill()
        
        # 查找进程
        processes = self.find_jobmanager_processes()
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
        processes = self.find_jobmanager_processes()
        if not processes:
            typer.echo("No JobManager processes to kill")
            return True
        
        typer.echo(f"Force killing {len(processes)} JobManager process(es)...")
        
        for proc in processes:
            try:
                typer.echo(f"Sending SIGKILL to process {proc.pid}")
                proc.kill()
                proc.wait(timeout=5)
                typer.echo(f"Process {proc.pid} killed successfully")
            except psutil.NoSuchProcess:
                typer.echo(f"Process {proc.pid} already terminated")
            except psutil.TimeoutExpired:
                typer.echo(f"Process {proc.pid} did not respond to SIGKILL")
            except Exception as e:
                typer.echo(f"Error killing process {proc.pid}: {e}")
        
        # 再次检查是否还有残留进程
        time.sleep(2)
        remaining = self.find_jobmanager_processes()
        if remaining:
            typer.echo(f"Warning: {len(remaining)} processes may still be running")
            return False
        
        typer.echo("All JobManager processes have been terminated")
        return True
    
    def start(self, daemon: bool = True, wait_for_ready: int = 10) -> bool:
        """启动JobManager"""
        typer.echo(f"Starting JobManager on {self.host}:{self.port}...")
        
        # 检查端口是否已被占用
        if self.is_port_occupied():
            typer.echo(f"Port {self.port} is already occupied")
            health = self.check_health()
            if health.get("status") == "success":
                typer.echo("JobManager is already running and healthy")
                return True
            else:
                typer.echo("Port occupied but JobManager not responding, stopping existing process...")
                if not self.stop_gracefully():
                    return False
        
        # 构建启动命令
        jobmanager_module = "sage.jobmanager.job_manager"
        cmd = [
            sys.executable, "-m", jobmanager_module,
            "--host", self.host,
            "--port", str(self.port)
        ]
        
        try:
            # 启动JobManager进程
            if daemon:
                # 作为守护进程启动
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    start_new_session=True
                )
                typer.echo(f"JobManager started as daemon process (PID: {process.pid})")
            else:
                # 在前台启动
                typer.echo("Starting JobManager in foreground mode...")
                process = subprocess.Popen(cmd)
                typer.echo(f"JobManager started in foreground (PID: {process.pid})")
                return True  # 前台模式直接返回
            
            # 等待服务就绪
            if wait_for_ready > 0:
                typer.echo(f"Waiting up to {wait_for_ready} seconds for JobManager to be ready...")
                for i in range(wait_for_ready):
                    time.sleep(1)
                    health = self.check_health()
                    if health.get("status") == "success":
                        typer.echo(f"JobManager is ready and healthy (took {i+1} seconds)")
                        return True
                    typer.echo(f"Waiting... ({i+1}/{wait_for_ready})")
                
                typer.echo("JobManager did not become ready within timeout")
                return False
            
            return True
            
        except Exception as e:
            typer.echo(f"Failed to start JobManager: {e}")
            return False
    
    def is_port_occupied(self) -> bool:
        """检查端口是否被占用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex((self.host, self.port))
                return result == 0
        except Exception:
            return False
    
    def status(self) -> Dict[str, Any]:
        """获取JobManager状态"""
        typer.echo(f"Checking JobManager status on {self.host}:{self.port}...")
        
        # 检查健康状态
        health = self.check_health()
        
        # 查找进程
        processes = self.find_jobmanager_processes()
        
        # 检查端口占用
        port_occupied = self.is_port_occupied()
        
        status_info = {
            "health": health,
            "processes": [{"pid": p.pid, "name": p.name()} for p in processes],
            "port_occupied": port_occupied,
            "host_port": f"{self.host}:{self.port}"
        }
        
        # 打印状态信息
        typer.echo(f"Health Status: {health.get('status', 'unknown')}")
        if health.get("status") == "success":
            daemon_status = health.get("daemon_status", {})
            typer.echo(f"  - Jobs Count: {daemon_status.get('jobs_count', 'unknown')}")
            typer.echo(f"  - Session ID: {daemon_status.get('session_id', 'unknown')}")
        
        typer.echo(f"Process Count: {len(processes)}")
        for proc_info in status_info["processes"]:
            typer.echo(f"  - PID {proc_info['pid']}: {proc_info['name']}")
        
        typer.echo(f"Port {self.port} Occupied: {port_occupied}")
        
        return status_info
    
    def restart(self, force: bool = False, wait_for_ready: int = 10) -> bool:
        """重启JobManager"""
        typer.echo("=" * 50)
        typer.echo("RESTARTING JOBMANAGER")
        typer.echo("=" * 50)
        
        # 停止现有实例
        if force:
            stop_success = self.force_kill()
        else:
            stop_success = self.stop_gracefully()
        
        if not stop_success:
            typer.echo("Failed to stop existing JobManager instances")
            return False
        
        # 等待一下确保资源释放
        typer.echo("Waiting for resources to be released...")
        time.sleep(2)
        
        # 启动新实例
        start_success = self.start(daemon=True, wait_for_ready=wait_for_ready)
        
        if start_success:
            typer.echo("=" * 50)
            typer.echo("JOBMANAGER RESTART SUCCESSFUL")
            typer.echo("=" * 50)
        else:
            typer.echo("=" * 50)
            typer.echo("JOBMANAGER RESTART FAILED")
            typer.echo("=" * 50)
        
        return start_success

def get_controller(host: str, port: int) -> JobManagerController:
    return JobManagerController(host=host, port=port)

@app.command()
def start(
    host: str = typer.Option("127.0.0.1", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
    foreground: bool = typer.Option(False, "--foreground", help="Start in the foreground"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Do not wait for the service to be ready")
):
    """
    Start the JobManager service.
    """
    controller = get_controller(host, port)
    wait_time = 0 if no_wait else 10
    success = controller.start(daemon=not foreground, wait_for_ready=wait_time)
    if success:
        typer.echo(f"\n✅ Operation 'start' completed successfully")
    else:
        typer.echo(f"\n❌ Operation 'start' failed")
        raise typer.Exit(code=1)

@app.command()
def stop(
    host: str = typer.Option("127.0.0.1", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
    force: bool = typer.Option(False, "--force", "-f", help="Force the operation")
):
    """
    Stop the JobManager service.
    """
    controller = get_controller(host, port)
    if force:
        success = controller.force_kill()
    else:
        success = controller.stop_gracefully()
    
    if success:
        typer.echo(f"\n✅ Operation 'stop' completed successfully")
    else:
        typer.echo(f"\n❌ Operation 'stop' failed")
        raise typer.Exit(code=1)

@app.command()
def restart(
    host: str = typer.Option("127.0.0.1", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
    force: bool = typer.Option(False, "--force", "-f", help="Force the restart"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Do not wait for the service to be ready")
):
    """
    Restart the JobManager service.
    """
    controller = get_controller(host, port)
    wait_time = 0 if no_wait else 10
    success = controller.restart(force=force, wait_for_ready=wait_time)
    if not success:
        raise typer.Exit(code=1)

@app.command()
def status(
    host: str = typer.Option("127.0.0.1", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port")
):
    """
    Check the status of the JobManager service.
    """
    controller = get_controller(host, port)
    controller.status()
    typer.echo(f"\n✅ Operation 'status' completed successfully")

@app.command()
def kill(
    host: str = typer.Option("127.0.0.1", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port")
):
    """
    Force kill the JobManager service.
    """
    controller = get_controller(host, port)
    success = controller.force_kill()
    if success:
        typer.echo(f"\n✅ Operation 'kill' completed successfully")
    else:
        typer.echo(f"\n❌ Operation 'kill' failed")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
