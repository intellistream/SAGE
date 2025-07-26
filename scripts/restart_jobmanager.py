#!/usr/bin/env python3
"""
SAGE JobManager 重启脚本 (增强版)
提供完整的JobManager生命周期管理功能
"""

import os
import sys
import time
import signal
import socket
import json
import argparse
import subprocess
import psutil
from pathlib import Path
from typing import Optional, Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class JobManagerController:
    """增强的JobManager控制器"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19001):
        self.host = host
        self.port = port
        self.process_name = "job_manager.py"
        
    def find_jobmanager_processes(self) -> List[psutil.Process]:
        """查找所有JobManager进程"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline'] or []
                # 检查是否包含job_manager.py和对应端口
                if (any(self.process_name in str(arg) for arg in cmdline) and 
                    any(str(self.port) in str(arg) for arg in cmdline)):
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return processes
        
    def check_health(self) -> Dict[str, Any]:
        """检查JobManager健康状态"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.host, self.port))
                
                # 发送健康检查请求
                request = {
                    "action": "health_check",
                    "request_id": "controller_health_check"
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
    
    def check_jobmanager_running(self) -> bool:
        """检查JobManager是否正在运行"""
        health = self.check_health()
        return health.get("status") == "success"
    
    def force_kill(self) -> bool:
        """强制杀死JobManager进程"""
        processes = self.find_jobmanager_processes()
        if not processes:
            print("未找到JobManager进程")
            return True
        
        print(f"强制终止 {len(processes)} 个JobManager进程...")
        
        for proc in processes:
            try:
                print(f"终止进程 {proc.pid}")
                proc.kill()
                proc.wait(timeout=5)
                print(f"进程 {proc.pid} 已终止")
            except psutil.NoSuchProcess:
                print(f"进程 {proc.pid} 已不存在")
            except psutil.TimeoutExpired:
                print(f"进程 {proc.pid} 未响应SIGKILL")
            except Exception as e:
                print(f"终止进程 {proc.pid} 时出错: {e}")
        
        # 再次检查
        time.sleep(2)
        remaining = self.find_jobmanager_processes()
        if remaining:
            print(f"警告: 仍有 {len(remaining)} 个进程在运行")
            return False
        
        print("所有JobManager进程已终止")
        return True
    
    def get_jobmanager_info(self) -> Optional[Dict[str, Any]]:
        """获取JobManager信息（保持兼容性）"""
        return self.check_health()
    
    def graceful_shutdown(self) -> bool:
        """优雅地关闭JobManager"""
        print("尝试优雅关闭JobManager...")
        
        # 首先检查服务状态
        info = self.get_jobmanager_info()
        if not info or info.get("status") != "success":
            print("JobManager未运行或无响应，尝试强制终止...")
            return self.force_kill()
        
        daemon_status = info.get("daemon_status", {})
        jobs_count = daemon_status.get("jobs_count", 0)
        
        print(f"当前JobManager状态:")
        print(f"  - 会话ID: {daemon_status.get('session_id', 'N/A')}")
        print(f"  - 活跃作业数: {jobs_count}")
        
        if jobs_count > 0:
            print(f"警告: 检测到 {jobs_count} 个活跃作业")
            response = input("是否继续关闭? 这将停止所有正在运行的作业 (y/N): ")
            if response.lower() != 'y':
                print("用户取消操作")
                return False
                
            # 发送清理所有作业的请求
            print("正在清理所有作业...")
            self._send_cleanup_request()
            time.sleep(2)  # 等待清理完成
        
        # 使用进程管理方式关闭
        processes = self.find_jobmanager_processes()
        if not processes:
            print("未找到JobManager进程")
            return True
        
        # 发送SIGTERM信号
        for proc in processes:
            try:
                print(f"向进程 {proc.pid} 发送SIGTERM信号...")
                proc.terminate()
            except psutil.NoSuchProcess:
                continue
        
        # 等待进程退出
        print("等待进程优雅退出...")
        timeout = 15
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
                print("所有JobManager进程已优雅退出")
                return True
                
            time.sleep(1)
        
        # 超时后强制终止
        print("优雅关闭超时，强制终止...")
        return self.force_kill()
    
    def start_jobmanager(self, daemon_mode: bool = True, wait_for_ready: int = 10) -> bool:
        """启动JobManager"""
        print(f"启动JobManager在 {self.host}:{self.port}...")
        
        # 检查端口是否已被占用
        if self.is_port_occupied():
            print(f"端口 {self.port} 已被占用")
            if self.check_jobmanager_running():
                print("JobManager已在运行")
                return True
            else:
                print("端口被其他程序占用，无法启动")
                return False
        
        try:
            # 构造启动命令
            cmd = [
                sys.executable, "-m", "sage.jobmanager.job_manager",
                "--host", self.host,
                "--port", str(self.port)
            ]
            
            if not daemon_mode:
                cmd.append("--no-daemon")
            
            if daemon_mode:
                # 后台模式启动
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    start_new_session=True
                )
                print(f"JobManager已作为守护进程启动 (PID: {process.pid})")
                
                # 等待服务就绪
                if wait_for_ready > 0:
                    print(f"等待最多 {wait_for_ready} 秒以确认服务就绪...")
                    for i in range(wait_for_ready):
                        time.sleep(1)
                        if self.check_jobmanager_running():
                            print(f"JobManager已就绪 (耗时 {i+1} 秒)")
                            return True
                        print(f"等待中... ({i+1}/{wait_for_ready})")
                    
                    print("JobManager在超时时间内未就绪")
                    return False
                
                return True
            else:
                # 前台模式启动
                print("在前台模式启动JobManager...")
                process = subprocess.Popen(cmd)
                return True
                
        except Exception as e:
            print(f"启动JobManager失败: {e}")
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
        """获取详细状态信息"""
        print(f"检查JobManager状态 ({self.host}:{self.port})...")
        
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
        print(f"健康状态: {health.get('status', 'unknown')}")
        if health.get("status") == "success":
            daemon_status = health.get("daemon_status", {})
            print(f"  - 作业数量: {daemon_status.get('jobs_count', 'unknown')}")
            print(f"  - 会话ID: {daemon_status.get('session_id', 'unknown')}")
        
        print(f"进程数量: {len(processes)}")
        for proc_info in status_info["processes"]:
            print(f"  - PID {proc_info['pid']}: {proc_info['name']}")
        
        print(f"端口 {self.port} 占用: {port_occupied}")
        
        return status_info
    
    def restart(self, force: bool = False, wait_for_ready: int = 10) -> bool:
        """重启JobManager"""
        print("=" * 50)
        print("重启 JOBMANAGER")
        print("=" * 50)
        
        # 停止现有实例
        if force:
            stop_success = self.force_kill()
        else:
            stop_success = self.graceful_shutdown()
        
        if not stop_success:
            print("停止现有JobManager实例失败")
            return False
        
        # 等待资源释放
        print("等待资源释放...")
        time.sleep(2)
        
        # 启动新实例
        start_success = self.start_jobmanager(daemon_mode=True, wait_for_ready=wait_for_ready)
        
        if start_success:
            print("=" * 50)
            print("JOBMANAGER 重启成功")
            print("=" * 50)
        else:
            print("=" * 50)
            print("JOBMANAGER 重启失败")
            print("=" * 50)
        
        return start_success
    
    def _send_cleanup_request(self) -> bool:
        """发送清理所有作业的请求"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self.host, self.port))
                
                request = {
                    "action": "cleanup_all_jobs",
                    "request_id": "restart_cleanup"
                }
                
                request_data = json.dumps(request).encode('utf-8')
                length_data = len(request_data).to_bytes(4, byteorder='big')
                sock.sendall(length_data + request_data)
                
                # 接收响应
                response_length_data = sock.recv(4)
                response_length = int.from_bytes(response_length_data, byteorder='big')
                response_data = sock.recv(response_length)
                response = json.loads(response_data.decode('utf-8'))
                
                print(f"清理作业结果: {response.get('message', 'N/A')}")
                return response.get("status") == "success"
                
        except Exception as e:
            print(f"发送清理请求失败: {e}")
            return False
    
    def _send_shutdown_signal(self) -> bool:
        """发送关闭信号到JobManager"""
        # 由于当前的JobManager实现中没有专门的shutdown命令，
        # 我们通过查找进程ID并发送SIGTERM信号来关闭
        try:
            # 查找JobManager进程
            result = subprocess.run(
                ["pgrep", "-f", f"job_manager.*--port {self.port}"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid_str in pids:
                    if pid_str:
                        pid = int(pid_str)
                        print(f"向JobManager进程 {pid} 发送SIGTERM信号...")
                        os.kill(pid, signal.SIGTERM)
                
                # 等待进程退出
                for i in range(10):  # 最多等待10秒
                    if not self.check_jobmanager_running():
                        print("JobManager已成功关闭")
                        return True
                    time.sleep(1)
                
                # 如果仍未关闭，发送SIGKILL
                print("优雅关闭超时，发送SIGKILL信号...")
                for pid_str in pids:
                    if pid_str:
                        pid = int(pid_str)
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass  # 进程已经不存在
                
                time.sleep(2)
                return not self.check_jobmanager_running()
            else:
                print("未找到JobManager进程")
                return True
                
        except Exception as e:
            print(f"发送关闭信号失败: {e}")
            return False
    
    def start_jobmanager(self, daemon_mode: bool = True) -> bool:
        """启动JobManager"""
        print(f"启动JobManager在 {self.host}:{self.port}...")
        
        try:
            # 构造启动命令
            cmd = [
                sys.executable, "-m", "sage.jobmanager.job_manager",
                "--host", self.host,
                "--port", str(self.port)
            ]
            
            if not daemon_mode:
                cmd.append("--no-daemon")
            
            if daemon_mode:
                # 后台模式启动
                self.jobmanager_process = subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                
                # 等待启动完成
                for i in range(15):  # 最多等待15秒
                    time.sleep(1)
                    if self.check_jobmanager_running():
                        print("JobManager启动成功!")
                        return True
                    print(f"等待JobManager启动... ({i+1}/15)")
                
                print("JobManager启动超时")
                return False
            else:
                # 前台模式启动
                print("以前台模式启动JobManager (Ctrl+C 停止)...")
                subprocess.run(cmd, cwd=project_root)
                return True
                
        except Exception as e:
            print(f"启动JobManager失败: {e}")
            return False
    
    def restart(self, daemon_mode: bool = True, force: bool = False) -> bool:
        """重启JobManager"""
        print("=" * 50)
        print("SAGE JobManager 重启工具")
        print("=" * 50)
        
        # 1. 检查当前状态
        is_running = self.check_jobmanager_running()
        print(f"JobManager当前状态: {'运行中' if is_running else '未运行'}")
        
        # 2. 如果正在运行，先关闭
        if is_running:
            if not force:
                # 显示当前信息
                info = self.get_jobmanager_info()
                if info:
                    daemon_status = info.get("daemon_status", {})
                    if daemon_status.get("jobs_count", 0) > 0:
                        print(f"警告: 检测到活跃作业，重启将中止这些作业!")
            
            success = self.graceful_shutdown()
            if not success:
                print("关闭JobManager失败")
                return False
        
        # 3. 启动新的JobManager
        success = self.start_jobmanager(daemon_mode)
        if success:
            print("JobManager重启完成!")
            
            # 显示新状态
            time.sleep(1)
            info = self.get_jobmanager_info()
            if info and info.get("status") == "success":
                daemon_status = info.get("daemon_status", {})
                print(f"新JobManager信息:")
                print(f"  - 会话ID: {daemon_status.get('session_id', 'N/A')}")
                print(f"  - 监听地址: {self.host}:{self.port}")
        else:
            print("JobManager重启失败")
        
        return success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SAGE JobManager重启工具")
    parser.add_argument("--host", default="127.0.0.1", help="JobManager主机地址")
    parser.add_argument("--port", type=int, default=19001, help="JobManager端口")
    parser.add_argument("--no-daemon", action="store_true", help="以前台模式启动")
    parser.add_argument("--force", action="store_true", help="强制重启，不询问确认")
    parser.add_argument("--only-start", action="store_true", help="仅启动，不检查现有实例")
    parser.add_argument("--only-stop", action="store_true", help="仅停止，不启动新实例")
    
    args = parser.parse_args()
    
    restarter = JobManagerController(args.host, args.port)
    
    try:
        if args.only_stop:
            # 仅停止
            if restarter.check_jobmanager_running():
                success = restarter.graceful_shutdown()
                print("JobManager已停止" if success else "停止JobManager失败")
            else:
                print("JobManager未运行")
        elif args.only_start:
            # 仅启动
            if restarter.check_jobmanager_running():
                print(f"JobManager已在 {args.host}:{args.port} 上运行")
            else:
                success = restarter.start_jobmanager(not args.no_daemon)
                print("JobManager已启动" if success else "启动JobManager失败")
        else:
            # 完整重启
            success = restarter.restart(not args.no_daemon, args.force)
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"重启过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
