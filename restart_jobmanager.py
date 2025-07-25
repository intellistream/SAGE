#!/usr/bin/env python3
"""
SAGE JobManager 重启脚本

这个脚本提供了完整的JobManager生命周期管理功能：
- 启动JobManager
- 停止JobManager  
- 重启JobManager
- 检查JobManager状态
- 强制杀死JobManager进程
"""

import os
import sys
import time
import signal
import socket
import json
import psutil
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

class JobManagerController:
    """JobManager控制器"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19001):
        self.host = host
        self.port = port
        self.process_name = "job_manager.py"
        
    def check_health(self) -> Dict[str, Any]:
        """检查JobManager健康状态"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.host, self.port))
                
                # 发送健康检查请求
                request = {
                    "action": "health_check",
                    "request_id": "restart_script_health_check"
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
                if cmdline and any(self.process_name in arg for arg in cmdline):
                    # 进一步检查是否是我们的JobManager实例
                    if any(str(self.port) in arg for arg in cmdline):
                        processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return processes
    
    def stop_gracefully(self, timeout: int = 30) -> bool:
        """优雅地停止JobManager"""
        print(f"Attempting graceful shutdown of JobManager on {self.host}:{self.port}...")
        
        # 首先尝试通过健康检查确认服务存在
        health = self.check_health()
        if health.get("status") != "success":
            print("JobManager is not responding to health checks")
            return self.force_kill()
        
        # 查找进程
        processes = self.find_jobmanager_processes()
        if not processes:
            print("No JobManager processes found")
            return True
        
        print(f"Found {len(processes)} JobManager process(es)")
        
        # 发送SIGTERM信号进行优雅关闭
        for proc in processes:
            try:
                print(f"Sending SIGTERM to process {proc.pid}")
                proc.terminate()
            except psutil.NoSuchProcess:
                continue
        
        # 等待进程结束
        print(f"Waiting up to {timeout} seconds for processes to exit...")
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
                print("All JobManager processes have exited gracefully")
                return True
                
            time.sleep(1)
        
        # 如果还有进程在运行，进行强制终止
        print("Some processes did not exit gracefully, forcing termination...")
        return self.force_kill()
    
    def force_kill(self) -> bool:
        """强制杀死JobManager进程"""
        processes = self.find_jobmanager_processes()
        if not processes:
            print("No JobManager processes to kill")
            return True
        
        print(f"Force killing {len(processes)} JobManager process(es)...")
        
        for proc in processes:
            try:
                print(f"Sending SIGKILL to process {proc.pid}")
                proc.kill()
                proc.wait(timeout=5)
                print(f"Process {proc.pid} killed successfully")
            except psutil.NoSuchProcess:
                print(f"Process {proc.pid} already terminated")
            except psutil.TimeoutExpired:
                print(f"Process {proc.pid} did not respond to SIGKILL")
            except Exception as e:
                print(f"Error killing process {proc.pid}: {e}")
        
        # 再次检查是否还有残留进程
        time.sleep(2)
        remaining = self.find_jobmanager_processes()
        if remaining:
            print(f"Warning: {len(remaining)} processes may still be running")
            return False
        
        print("All JobManager processes have been terminated")
        return True
    
    def start(self, daemon: bool = True, wait_for_ready: int = 10) -> bool:
        """启动JobManager"""
        print(f"Starting JobManager on {self.host}:{self.port}...")
        
        # 检查端口是否已被占用
        if self.is_port_occupied():
            print(f"Port {self.port} is already occupied")
            health = self.check_health()
            if health.get("status") == "success":
                print("JobManager is already running and healthy")
                return True
            else:
                print("Port occupied but JobManager not responding, stopping existing process...")
                if not self.stop_gracefully():
                    return False
        
        # 构建启动命令
        import subprocess
        
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
                print(f"JobManager started as daemon process (PID: {process.pid})")
            else:
                # 在前台启动
                print("Starting JobManager in foreground mode...")
                process = subprocess.Popen(cmd)
                print(f"JobManager started in foreground (PID: {process.pid})")
                return True  # 前台模式直接返回
            
            # 等待服务就绪
            if wait_for_ready > 0:
                print(f"Waiting up to {wait_for_ready} seconds for JobManager to be ready...")
                for i in range(wait_for_ready):
                    time.sleep(1)
                    health = self.check_health()
                    if health.get("status") == "success":
                        print(f"JobManager is ready and healthy (took {i+1} seconds)")
                        return True
                    print(f"Waiting... ({i+1}/{wait_for_ready})")
                
                print("JobManager did not become ready within timeout")
                return False
            
            return True
            
        except Exception as e:
            print(f"Failed to start JobManager: {e}")
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
        print(f"Checking JobManager status on {self.host}:{self.port}...")
        
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
        print(f"Health Status: {health.get('status', 'unknown')}")
        if health.get("status") == "success":
            daemon_status = health.get("daemon_status", {})
            print(f"  - Jobs Count: {daemon_status.get('jobs_count', 'unknown')}")
            print(f"  - Session ID: {daemon_status.get('session_id', 'unknown')}")
        
        print(f"Process Count: {len(processes)}")
        for proc_info in status_info["processes"]:
            print(f"  - PID {proc_info['pid']}: {proc_info['name']}")
        
        print(f"Port {self.port} Occupied: {port_occupied}")
        
        return status_info
    
    def restart(self, force: bool = False, wait_for_ready: int = 10) -> bool:
        """重启JobManager"""
        print("=" * 50)
        print("RESTARTING JOBMANAGER")
        print("=" * 50)
        
        # 停止现有实例
        if force:
            stop_success = self.force_kill()
        else:
            stop_success = self.stop_gracefully()
        
        if not stop_success:
            print("Failed to stop existing JobManager instances")
            return False
        
        # 等待一下确保资源释放
        print("Waiting for resources to be released...")
        time.sleep(2)
        
        # 启动新实例
        start_success = self.start(daemon=True, wait_for_ready=wait_for_ready)
        
        if start_success:
            print("=" * 50)
            print("JOBMANAGER RESTART SUCCESSFUL")
            print("=" * 50)
        else:
            print("=" * 50)
            print("JOBMANAGER RESTART FAILED")
            print("=" * 50)
        
        return start_success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SAGE JobManager Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start                    # 启动JobManager
  %(prog)s stop                     # 优雅停止JobManager
  %(prog)s restart                  # 重启JobManager
  %(prog)s status                   # 检查JobManager状态
  %(prog)s kill                     # 强制杀死JobManager进程
  %(prog)s --port 19002 restart     # 在指定端口重启JobManager
        """
    )
    
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status", "kill"],
        help="要执行的操作"
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="JobManager主机地址 (默认: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=19001,
        help="JobManager端口 (默认: 19001)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制操作（用于stop和restart）"
    )
    
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="启动后不等待服务就绪"
    )
    
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="在前台启动（仅用于start操作）"
    )
    
    args = parser.parse_args()
    
    # 创建控制器
    controller = JobManagerController(host=args.host, port=args.port)
    
    # 执行操作
    success = False
    wait_time = 0 if args.no_wait else 10
    
    try:
        if args.action == "start":
            success = controller.start(daemon=not args.foreground, wait_for_ready=wait_time)
        elif args.action == "stop":
            if args.force:
                success = controller.force_kill()
            else:
                success = controller.stop_gracefully()
        elif args.action == "restart":
            success = controller.restart(force=args.force, wait_for_ready=wait_time)
        elif args.action == "status":
            controller.status()
            success = True
        elif args.action == "kill":
            success = controller.force_kill()
        
        if success:
            print(f"\n✅ Operation '{args.action}' completed successfully")
            sys.exit(0)
        else:
            print(f"\n❌ Operation '{args.action}' failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
