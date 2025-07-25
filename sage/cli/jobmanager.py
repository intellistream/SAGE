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
import getpass
import os
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
        self._sudo_password = None
        
    def _get_sudo_password(self) -> str:
        """获取sudo密码"""
        if self._sudo_password is None:
            typer.echo("🔐 Force mode requires sudo privileges to terminate processes owned by other users.")
            password = getpass.getpass("Please enter your sudo password (or press Enter to skip): ")
            if password.strip():
                # 验证密码是否正确
                try:
                    typer.echo("🔍 Verifying sudo password...")
                    result = subprocess.run(
                        ['sudo', '-S', 'echo', 'password_test'],
                        input=password + '\n',
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        self._sudo_password = password
                        typer.echo("✅ Sudo password verified successfully")
                    else:
                        typer.echo("❌ Invalid sudo password, will continue without sudo privileges")
                        if result.stderr:
                            typer.echo(f"   Error: {result.stderr.strip()}")
                        self._sudo_password = ""
                except subprocess.TimeoutExpired:
                    typer.echo("❌ Sudo password verification timeout, will continue without sudo privileges")
                    self._sudo_password = ""
                except Exception as e:
                    typer.echo(f"❌ Error verifying sudo password: {e}")
                    self._sudo_password = ""
            else:
                typer.echo("⚠️  No sudo password provided, may fail to kill processes owned by other users")
                self._sudo_password = ""
        return self._sudo_password
    
    def diagnose_startup_issues(self) -> Dict[str, Any]:
        """诊断启动问题"""
        typer.echo("🔍 Diagnosing potential startup issues...")
        
        issues = []
        warnings = []
        info = {}
        
        # 1. 检查端口
        port_occupied = self.is_port_occupied()
        info['port_occupied'] = port_occupied
        if port_occupied:
            issues.append(f"Port {self.port} is occupied")
        else:
            typer.echo(f"✅ Port {self.port} is available")
        
        # 2. 检查端口绑定权限
        can_bind = self._check_port_binding_permission()
        info['can_bind_port'] = can_bind
        if not can_bind:
            issues.append(f"Cannot bind to port {self.port}")
        else:
            typer.echo(f"✅ Can bind to port {self.port}")
        
        # 3. 检查Python环境
        python_path = sys.executable
        info['python_path'] = python_path
        typer.echo(f"🐍 Python executable: {python_path}")
        
        # 4. 检查SAGE模块
        try:
            import sage.jobmanager.job_manager
            typer.echo("✅ SAGE JobManager module is accessible")
            info['sage_module_accessible'] = True
        except ImportError as e:
            issues.append(f"Cannot import SAGE JobManager module: {e}")
            info['sage_module_accessible'] = False
        
        # 5. 检查用户权限
        current_user = os.getenv('USER', 'unknown')
        current_uid = os.getuid() if hasattr(os, 'getuid') else 'unknown'
        info['current_user'] = current_user
        info['current_uid'] = current_uid
        typer.echo(f"👤 Current user: {current_user} (UID: {current_uid})")
        
        # 6. 检查工作目录权限
        try:
            cwd = os.getcwd()
            info['working_directory'] = cwd
            # 测试在当前目录创建文件的权限
            test_file = os.path.join(cwd, f'.sage_test_{int(time.time())}')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            typer.echo(f"✅ Working directory writable: {cwd}")
            info['working_dir_writable'] = True
        except Exception as e:
            warnings.append(f"Working directory may not be writable: {e}")
            info['working_dir_writable'] = False
        
        # 7. 检查环境变量
        important_env_vars = ['PATH', 'PYTHONPATH', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV']
        env_info = {}
        for var in important_env_vars:
            value = os.getenv(var)
            env_info[var] = value
            if value:
                typer.echo(f"🌍 {var}: {value}")
        info['environment_variables'] = env_info
        
        # 8. 尝试创建测试进程
        try:
            test_cmd = [sys.executable, '-c', 'print("test process"); import sys; sys.exit(0)']
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                typer.echo("✅ Can create subprocess successfully")
                info['can_create_subprocess'] = True
            else:
                issues.append(f"Test subprocess failed with return code {result.returncode}")
                info['can_create_subprocess'] = False
        except Exception as e:
            issues.append(f"Cannot create subprocess: {e}")
            info['can_create_subprocess'] = False
        
        # 9. 检查网络连接能力
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect(('127.0.0.1', 80))  # 尝试连接到本地
            typer.echo("✅ Network connectivity available")
            info['network_available'] = True
        except:
            # 这不一定是问题，只是信息
            info['network_available'] = False
        
        # 汇总结果
        typer.echo(f"\n📊 Diagnosis Summary:")
        if issues:
            typer.echo(f"❌ Found {len(issues)} issues:")
            for i, issue in enumerate(issues, 1):
                typer.echo(f"   {i}. {issue}")
        else:
            typer.echo("✅ No critical issues found")
            
        if warnings:
            typer.echo(f"⚠️  Found {len(warnings)} warnings:")
            for i, warning in enumerate(warnings, 1):
                typer.echo(f"   {i}. {warning}")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'info': info
        }
    
    def _wait_for_port_release(self, timeout: int = 10) -> bool:
        """等待端口释放"""
        typer.echo(f"⏳ Waiting for port {self.port} to be released...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.is_port_occupied():
                typer.echo(f"✅ Port {self.port} is now available")
                return True
            typer.echo(f"   Port still occupied, waiting... ({int(time.time() - start_time)}/{timeout}s)")
            time.sleep(1)
        
        typer.echo(f"⚠️  Port {self.port} is still occupied after {timeout} seconds")
        return False
    
    def _aggressive_port_cleanup(self) -> bool:
        """激进的端口清理 - 尝试杀死所有占用指定端口的进程"""
        typer.echo(f"🔧 Performing aggressive cleanup for port {self.port}...")
        
        killed_any = False
        
        # 使用多种方法查找占用端口的进程
        methods = [
            # Method 1: lsof
            lambda: self._find_port_processes_lsof(),
            # Method 2: netstat + ss
            lambda: self._find_port_processes_netstat(),
            # Method 3: fuser
            lambda: self._find_port_processes_fuser()
        ]
        
        all_pids = set()
        for method in methods:
            try:
                pids = method()
                all_pids.update(pids)
            except:
                continue
        
        if not all_pids:
            typer.echo("No processes found occupying the port")
            return False
        
        # 尝试杀死所有找到的进程
        for pid in all_pids:
            try:
                proc = psutil.Process(pid)
                proc_info = self._get_process_info(pid)
                typer.echo(f"🎯 Found port-occupying process: PID {pid} ({proc_info['user']})")
                
                # 先尝试普通kill
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                    typer.echo(f"✅ Killed process {pid}")
                    killed_any = True
                except psutil.AccessDenied:
                    # 尝试sudo kill
                    if self._kill_process_with_sudo(pid):
                        killed_any = True
                except:
                    continue
                    
            except psutil.NoSuchProcess:
                continue
            except Exception as e:
                typer.echo(f"Error killing process {pid}: {e}")
                continue
        
        return killed_any
    
    def _find_port_processes_lsof(self) -> List[int]:
        """使用lsof查找占用端口的进程"""
        try:
            result = subprocess.run(
                ['lsof', '-ti', f':{self.port}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip().isdigit()]
        except:
            pass
        return []
    
    def _find_port_processes_netstat(self) -> List[int]:
        """使用netstat查找占用端口的进程"""
        try:
            result = subprocess.run(
                ['netstat', '-tlnp'],
                capture_output=True,
                text=True,
                timeout=5
            )
            pids = []
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f':{self.port}' in line and 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) > 6 and '/' in parts[6]:
                            pid_str = parts[6].split('/')[0]
                            if pid_str.isdigit():
                                pids.append(int(pid_str))
            return pids
        except:
            pass
        return []
    
    def _find_port_processes_fuser(self) -> List[int]:
        """使用fuser查找占用端口的进程"""
        try:
            result = subprocess.run(
                ['fuser', f'{self.port}/tcp'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return [int(pid.strip()) for pid in result.stdout.strip().split() if pid.strip().isdigit()]
        except:
            pass
        return []
    
    def _check_port_binding_permission(self) -> bool:
        """检查是否有端口绑定权限"""
        try:
            # 尝试绑定端口来检查权限
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.host, self.port))
                typer.echo(f"✅ Port {self.port} binding permission verified")
                return True
        except PermissionError:
            typer.echo(f"❌ Permission denied to bind port {self.port}")
            return False
        except OSError as e:
            if e.errno == 98:  # Address already in use
                typer.echo(f"⚠️  Port {self.port} is still in use")
                return False
            else:
                typer.echo(f"❌ Error checking port binding permission: {e}")
                return False
        except Exception as e:
            typer.echo(f"❌ Unexpected error checking port permission: {e}")
            return False
    
    def _ensure_sudo_access(self) -> bool:
        """确保有sudo访问权限，返回是否成功获取权限"""
        password = self._get_sudo_password()
        has_access = bool(password)
        if not has_access:
            typer.echo("⚠️  Warning: No sudo access available. May fail to terminate processes owned by other users.")
        return has_access
    
    def _get_process_info(self, pid: int) -> Dict[str, str]:
        """获取进程详细信息"""
        try:
            proc = psutil.Process(pid)
            return {
                "pid": str(pid),
                "name": proc.name(),
                "user": proc.username(),
                "cmdline": ' '.join(proc.cmdline()),
                "status": proc.status()
            }
        except psutil.NoSuchProcess:
            return {"pid": str(pid), "name": "N/A", "user": "N/A", "cmdline": "N/A", "status": "Not Found"}
        except psutil.AccessDenied:
            return {"pid": str(pid), "name": "N/A", "user": "N/A", "cmdline": "N/A", "status": "Access Denied"}
    
    def _kill_process_with_sudo(self, pid: int) -> bool:
        """使用sudo权限杀死进程"""
        password = self._get_sudo_password()
        if not password:
            typer.echo(f"❌ No sudo password available to kill process {pid}")
            return False
            
        try:
            typer.echo(f"🔐 Attempting to kill process {pid} with sudo...")
            result = subprocess.run(
                ['sudo', '-S', 'kill', '-9', str(pid)],
                input=password + '\n',
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                typer.echo(f"✅ Successfully killed process {pid} with sudo")
                return True
            else:
                typer.echo(f"❌ Failed to kill process {pid} with sudo")
                if result.stderr:
                    typer.echo(f"   Error: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            typer.echo(f"⏰ Timeout while trying to kill process {pid} with sudo")
            return False
        except subprocess.SubprocessError as e:
            typer.echo(f"❌ Subprocess error while killing process {pid}: {e}")
            return False
        except Exception as e:
            typer.echo(f"❌ Unexpected error while killing process {pid}: {e}")
            return False
        
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
        
        # 如果没有找到进程，也尝试通过端口查找
        if not processes:
            typer.echo("No JobManager processes found by process name, checking by port...")
            try:
                # 使用 lsof 或 netstat 查找占用端口的进程
                import subprocess
                result = subprocess.run(
                    ['lsof', '-ti', f':{self.port}'], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
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
                    result = subprocess.run(
                        ['netstat', '-tlnp'], 
                        capture_output=True, 
                        text=True
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if f':{self.port}' in line and 'LISTEN' in line:
                                # 提取PID
                                parts = line.split()
                                if len(parts) > 6 and '/' in parts[6]:
                                    pid_str = parts[6].split('/')[0]
                                    try:
                                        pid = int(pid_str)
                                        process = psutil.Process(pid)
                                        processes.append(process)
                                        typer.echo(f"Found process using port {self.port}: PID {pid}")
                                    except (ValueError, psutil.NoSuchProcess):
                                        continue
                except subprocess.SubprocessError:
                    pass
        
        if not processes:
            typer.echo("No JobManager processes to kill")
            return True
        
        # 检查是否需要sudo权限
        current_user = os.getenv('USER', 'unknown')
        needs_sudo = False
        
        for proc in processes:
            proc_info = self._get_process_info(proc.pid)
            proc_user = proc_info['user']
            if proc_user != current_user and proc_user != 'N/A':
                needs_sudo = True
                break
        
        # 如果需要sudo权限但还没有获取，先获取
        if needs_sudo and self._sudo_password is None:
            typer.echo("⚠️  Some processes are owned by other users, requesting sudo access...")
            if not self._ensure_sudo_access():
                typer.echo("❌ Unable to obtain sudo privileges. Cannot kill processes owned by other users.")
                typer.echo("💡 Suggestion: Run this command as root or ask the process owner to stop the service.")
                return False
        
        typer.echo(f"🔪 Force killing {len(processes)} JobManager process(es)...")
        
        killed_count = 0
        
        for proc in processes:
            proc_info = self._get_process_info(proc.pid)
            proc_user = proc_info['user']
            
            typer.echo(f"\n📋 Process Information:")
            typer.echo(f"   PID: {proc_info['pid']}")
            typer.echo(f"   Name: {proc_info['name']}")
            typer.echo(f"   User: {proc_user}")
            typer.echo(f"   Status: {proc_info['status']}")
            typer.echo(f"   Command: {proc_info['cmdline']}")
            
            # 判断是否需要sudo权限
            needs_sudo_for_proc = proc_user != current_user and proc_user != 'N/A'
            if needs_sudo_for_proc:
                typer.echo(f"⚠️  Process owned by different user ({proc_user}), using sudo privileges")
            
            try:
                # 尝试发送 SIGKILL
                proc.kill()
                proc.wait(timeout=5)
                typer.echo(f"✅ Process {proc.pid} killed successfully")
                killed_count += 1
                
            except psutil.NoSuchProcess:
                typer.echo(f"✅ Process {proc.pid} already terminated")
                killed_count += 1
            except psutil.AccessDenied:
                typer.echo(f"❌ Permission denied to kill process {proc.pid}")
                # 尝试使用sudo权限强制终止
                if self._kill_process_with_sudo(proc.pid):
                    typer.echo(f"✅ Process {proc.pid} killed with sudo privileges")
                    killed_count += 1
                else:
                    typer.echo(f"❌ Failed to kill process {proc.pid} even with sudo privileges")
            except psutil.TimeoutExpired:
                typer.echo(f"⏰ Process {proc.pid} did not respond to SIGKILL within timeout")
            except Exception as e:
                typer.echo(f"❌ Error killing process {proc.pid}: {e}")
        
        # 再次检查是否还有残留进程
        typer.echo(f"\n🔍 Checking for remaining processes...")
        time.sleep(2)
        remaining = self.find_jobmanager_processes()
        
        if remaining:
            typer.echo(f"⚠️  Warning: {len(remaining)} processes may still be running")
            # 显示残留进程信息
            for proc in remaining:
                proc_info = self._get_process_info(proc.pid)
                typer.echo(f"   Remaining: PID {proc_info['pid']}, User: {proc_info['user']}, Name: {proc_info['name']}")
            return killed_count > 0  # 如果至少杀死了一些进程，认为部分成功
        
        typer.echo("✅ All JobManager processes have been terminated")
        return True
    
    def start(self, daemon: bool = True, wait_for_ready: int = 10, force: bool = False) -> bool:
        """启动JobManager"""
        typer.echo(f"Starting JobManager on {self.host}:{self.port}...")
        
        # 如果使用force模式，预先获取sudo权限
        if force:
            self._ensure_sudo_access()
        
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
                if not self._wait_for_port_release(15):
                    typer.echo("❌ Port is still occupied after force kill")
                    # 尝试更激进的端口清理
                    typer.echo("🔧 Attempting aggressive port cleanup...")
                    self._aggressive_port_cleanup()
                    if not self._wait_for_port_release(5):
                        typer.echo("❌ Unable to free the port, startup may fail")
            else:
                health = self.check_health()
                if health.get("status") == "success":
                    typer.echo("JobManager is already running and healthy")
                    return True
                else:
                    typer.echo("Port occupied but JobManager not responding, stopping existing process...")
                    if not self.stop_gracefully():
                        return False
                    # 等待端口释放
                    self._wait_for_port_release(10)
        
        # 检查端口绑定权限
        if not self._check_port_binding_permission():
            typer.echo("❌ Cannot bind to port, startup will fail")
            typer.echo("💡 Suggestion: Try using a different port with --port option")
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
                # 自动运行诊断
                typer.echo("\n🔍 Running automatic diagnosis...")
                self.diagnose_startup_issues()
                
                # 检查进程是否还在运行
                try:
                    if process.poll() is None:
                        typer.echo("Process is still running but not responding to health checks")
                        typer.echo("This might indicate a startup issue")
                        # 尝试获取进程输出
                        try:
                            stdout, stderr = process.communicate(timeout=2)
                            if stdout:
                                typer.echo(f"Process stdout: {stdout.decode()}")
                            if stderr:
                                typer.echo(f"Process stderr: {stderr.decode()}")
                        except subprocess.TimeoutExpired:
                            typer.echo("Process is still running, cannot get output")
                        except Exception as e:
                            typer.echo(f"Error getting process output: {e}")
                    else:
                        typer.echo(f"Process exited with code: {process.returncode}")
                        # 尝试获取错误输出
                        try:
                            stdout, stderr = process.communicate(timeout=1)
                            if stdout:
                                typer.echo(f"Process stdout: {stdout.decode()}")
                            if stderr:
                                typer.echo(f"Process stderr: {stderr.decode()}")
                        except Exception as e:
                            typer.echo(f"Error getting process output: {e}")
                except Exception as e:
                    typer.echo(f"Error checking process status: {e}")
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
            proc_pid = proc_info['pid']
            try:
                proc = psutil.Process(proc_pid)
                proc_user = proc.username()
                proc_cmdline = ' '.join(proc.cmdline())
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
                    ['lsof', '-ti', f':{self.port}'], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid_str in pids:
                        try:
                            pid = int(pid_str.strip())
                            proc = psutil.Process(pid)
                            proc_user = proc.username()
                            proc_cmdline = ' '.join(proc.cmdline())
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
            typer.echo("🔐 Force restart mode: will use sudo to stop, then start with user privileges")
            self._ensure_sudo_access()
        
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
            if not self._wait_for_port_release(10):
                typer.echo("⚠️  Port may still be occupied, attempting aggressive cleanup...")
                self._aggressive_port_cleanup()
                self._wait_for_port_release(5)
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

def get_controller(host: str, port: int) -> JobManagerController:
    return JobManagerController(host=host, port=port)

@app.command()
def start(
    host: str = typer.Option("127.0.0.1", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
    foreground: bool = typer.Option(False, "--foreground", help="Start in the foreground"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Do not wait for the service to be ready"),
    force: bool = typer.Option(False, "--force", "-f", help="Force start by killing any existing JobManager processes")
):
    """
    Start the JobManager service.
    """
    controller = get_controller(host, port)
    wait_time = 0 if no_wait else 10
    success = controller.start(daemon=not foreground, wait_for_ready=wait_time, force=force)
    if success:
        typer.echo(f"\n✅ Operation 'start' completed successfully")
    else:
        typer.echo(f"\n❌ Operation 'start' failed")
        raise typer.Exit(code=1)

@app.command()
def stop(
    host: str = typer.Option("127.0.0.1", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port"),
    force: bool = typer.Option(False, "--force", "-f", help="Force stop by killing any existing JobManager processes")
):
    """
    Stop the JobManager service.
    """
    controller = get_controller(host, port)
    
    # 如果使用force模式，预先获取sudo权限
    if force:
        typer.echo("🔐 Force stop mode: may require sudo privileges to terminate processes owned by other users.")
        controller._ensure_sudo_access()
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
    
    # kill命令总是需要sudo权限，预先获取
    typer.echo("🔐 Kill command: may require sudo privileges to terminate processes owned by other users.")
    controller._ensure_sudo_access()
    
    success = controller.force_kill()
    if success:
        typer.echo(f"\n✅ Operation 'kill' completed successfully")
    else:
        typer.echo(f"\n❌ Operation 'kill' failed")
        raise typer.Exit(code=1)

@app.command()
def diagnose(
    host: str = typer.Option("127.0.0.1", help="JobManager host address"),
    port: int = typer.Option(19001, help="JobManager port")
):
    """
    Diagnose potential JobManager startup issues.
    """
    controller = get_controller(host, port)
    diagnosis = controller.diagnose_startup_issues()
    
    if diagnosis['issues']:
        typer.echo(f"\n💡 Suggestions to fix issues:")
        for issue in diagnosis['issues']:
            if "Port" in issue and "occupied" in issue:
                typer.echo("   • Use --force to kill existing processes")
                typer.echo("   • Or use a different port with --port")
            elif "Cannot bind" in issue:
                typer.echo("   • Check if port is privileged (< 1024)")
                typer.echo("   • Try a different port with --port")
            elif "Cannot import" in issue:
                typer.echo("   • Check if SAGE is properly installed")
                typer.echo("   • Verify conda/virtual environment is activated")
            elif "subprocess" in issue:
                typer.echo("   • Check system resources and permissions")
    
    typer.echo(f"\n✅ Operation 'diagnose' completed")

if __name__ == "__main__":
    app()
