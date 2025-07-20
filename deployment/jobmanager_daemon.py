#!/usr/bin/env python3

# TODO: 添加一个SAGE的集群配置和启动
# TODO: 通过Ray提供的接口，实现把actor和机器进行1对1绑定的功能。

"""
JobManager守护进程脚本
检查19000端口是否有服务，如果没有则启动JobManager作为后台服务
"""

import os
import sys
import socket
import time
import signal
import psutil
import subprocess
import argparse
import logging
import json
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
SAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SAGE_ROOT))

class JobManagerDaemon:
    def __init__(self, host: str = "127.0.0.1", port: int = 19000, 
                 pidfile: str = "/tmp/jobmanager.pid",
                 logfile: str = "/tmp/jobmanager.log"):
        self.host = host
        self.port = port
        self.pidfile = Path(pidfile)
        self.logfile = Path(logfile)
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('JobManagerDaemon')
        logger.setLevel(logging.INFO)
        
        # 清除现有的处理器
        logger.handlers.clear()
        
        # 文件处理器
        file_handler = logging.FileHandler(self.logfile)
        file_handler.setLevel(logging.INFO)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def check_port(self) -> bool:
        """检查端口是否被占用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)  # 2秒超时
                result = sock.connect_ex((self.host, self.port))
                self.logger.debug(f"Port check result: {result}")
                return result == 0  # 0表示连接成功，端口被占用
        except Exception as e:
            self.logger.warning(f"Error checking port {self.port}: {e}")
            return False
    
    def test_jobmanager_service(self) -> bool:
        """测试JobManager服务是否正常响应"""
        self.logger.debug("Testing JobManager service...")
        if not self.check_port():
            self.logger.debug("Port not occupied, service not running")
            return False
            
        try:
            # 创建简单的ping消息
            test_message = {
                "type": "ping",
                "timestamp": time.time()
            }
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.host, self.port))
                
                # 发送测试消息
                message_str = json.dumps(test_message)
                message_bytes = message_str.encode('utf-8')
                length_header = len(message_bytes).to_bytes(4, byteorder='big')
                
                sock.sendall(length_header + message_bytes)
                
                # 尝试接收响应（可能没有响应，只要连接成功就算健康）
                try:
                    sock.settimeout(2)  # 短超时
                    response_length_bytes = sock.recv(4)
                    if len(response_length_bytes) == 4:
                        response_length = int.from_bytes(response_length_bytes, byteorder='big')
                        if 0 < response_length < 10000:  # 合理的响应长度
                            response_data = sock.recv(response_length)
                            response = json.loads(response_data.decode('utf-8'))
                            self.logger.debug(f"Service response: {response}")
                except socket.timeout:
                    # 超时也算正常，说明服务在运行但可能不处理ping消息
                    self.logger.debug("Service responded with timeout (acceptable)")
                    
                return True  # 能连接上就算健康
                
        except Exception as e:
            self.logger.warning(f"JobManager service test failed: {e}")
            return False
    def _process_uses_port(self, pid: int, port: int) -> bool:
        """检查进程是否使用指定端口"""
        try:
            proc = psutil.Process(pid)
            connections = proc.connections(kind='inet')
            for conn in connections:
                if (conn.laddr and conn.laddr.port == port and 
                    conn.status == psutil.CONN_LISTEN):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return False
    def get_jobmanager_process(self) -> Optional[psutil.Process]:
        """查找JobManager进程（改进版本）"""
        current_pid = os.getpid()  # 获取当前进程的PID
        
        # 首先尝试通过PID文件查找
        try:
            if self.pidfile.exists():
                pid = int(self.pidfile.read_text().strip())
                try:
                    proc = psutil.Process(pid)
                    # 确保不是当前进程且进程在运行
                    if proc.pid != current_pid and proc.is_running():
                        self.logger.debug(f"Found JobManager process from pidfile: PID {proc.pid}")
                        return proc
                except psutil.NoSuchProcess:
                    pass
                    
                # PID文件存在但进程不存在，清理PID文件
                self.pidfile.unlink()
                self.logger.info("Cleaned stale pidfile")
                
        except Exception as e:
            self.logger.warning(f"Error checking JobManager process from pidfile: {e}")
        
        # 通过端口查找进程
        try:
            # 使用lsof查找监听19000端口的进程
            result = subprocess.run(['lsof', '-ti', f':{self.port}'], 
                                capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid_str in pids:
                    try:
                        pid = int(pid_str)
                        if pid != current_pid:  # 排除当前进程
                            proc = psutil.Process(pid)
                            if proc.is_running():
                                cmdline = ' '.join(proc.cmdline())
                                # 检查是否是Python进程且不是当前daemon脚本
                                if ('python' in proc.name().lower() and 
                                    'jobmanager_daemon.py' not in cmdline):
                                    self.logger.info(f"Found process using port {self.port}: PID {pid}")
                                    self.logger.debug(f"Command line: {cmdline}")
                                    return proc
                    except (ValueError, psutil.NoSuchProcess):
                        continue
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            self.logger.debug(f"lsof command not available or failed: {e}")
        
        # 备用方法：通过进程名查找
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # 跳过当前进程
                    if proc.info['pid'] == current_pid:
                        continue
                        
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # 查找可能的JobManager进程
                    if ('python' in proc.info['name'].lower()):
                        # 检查是否包含JobManager相关关键词，但排除daemon脚本
                        if (('sage_jobmanager' in cmdline or 
                            'engine.py' in cmdline or
                            'JobManager' in cmdline or
                            'SAGE_JOBMANAGER_INSTANCE' in cmdline) and
                            'jobmanager_daemon.py' not in cmdline):
                            
                            # 验证进程是否真的在使用目标端口
                            if self._process_uses_port(proc.info['pid'], self.port):
                                self.logger.info(f"Found JobManager process by search: PID {proc.info['pid']}")
                                self.logger.debug(f"Command line: {cmdline}")
                                return psutil.Process(proc.info['pid'])
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.warning(f"Error searching JobManager processes: {e}")
            
        return None
        
    def start_jobmanager(self) -> bool:
        """启动JobManager服务"""
        try:
            # 确保没有其他服务占用端口
            if self.check_port():
                self.logger.error(f"Port {self.port} is already in use")
                return False
            
            # 准备启动脚本
            start_script = self._create_start_script()
            
            # 启动后台进程
            self.logger.info(f"Starting JobManager service on {self.host}:{self.port}")
            
            # 创建启动日志文件
            startup_log = Path("/tmp/jobmanager_startup.log")
            
            with open(startup_log, 'w') as log_file:
                process = subprocess.Popen(
                    [sys.executable, str(start_script)],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,  # 创建新的会话组
                    cwd=str(SAGE_ROOT)
                )
            
            # 记录PID
            self.pidfile.write_text(str(process.pid))
            self.logger.info(f"JobManager started with PID {process.pid}")
            
            # 等待服务启动
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)
                
                # 检查进程是否还在运行
                if process.poll() is not None:
                    self.logger.error(f"JobManager process exited with code {process.poll()}")
                    # 显示启动日志
                    if startup_log.exists():
                        log_content = startup_log.read_text()
                        self.logger.error(f"Startup log:\n{log_content}")
                    return False
                
                # 检查服务是否健康
                if self.check_port():  # 先检查端口是否开放
                    self.logger.info("JobManager service is ready")
                    return True
                    
                if i % 5 == 0:
                    self.logger.info(f"Waiting for JobManager to start... ({i+1}/{max_wait})")
            
            self.logger.error("JobManager failed to start within 30 seconds")
            # 显示启动日志
            if startup_log.exists():
                log_content = startup_log.read_text()
                self.logger.error(f"Startup log:\n{log_content}")
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start JobManager: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _create_start_script(self) -> Path:
        """创建JobManager启动脚本"""
        script_content = f'''#!/usr/bin/env python3
# SAGE_JOBMANAGER_INSTANCE - 唯一标识符
import sys
import os
from pathlib import Path

# 添加项目路径
SAGE_ROOT = Path("{SAGE_ROOT}")
sys.path.insert(0, str(SAGE_ROOT))

# 导入并启动JobManager
from sage_jobmanager.job_manager import JobManager

def main():
    try:
        print("Creating JobManager instance...")
        
        # 创建JobManager实例
        job_manager = JobManager(host="{self.host}", port={self.port})
        
        print("Starting TCP server...")
        
        # 检查TCP服务器是否有start方法
        if hasattr(job_manager.tcp_server, 'start'):
            job_manager.tcp_server.start()
            print(f"JobManager TCP server started on {self.host}:{self.port}")
        elif hasattr(job_manager, 'start'):
            job_manager.start()
            print(f"JobManager started on {self.host}:{self.port}")
        else:
            print(f"JobManager created on {self.host}:{self.port} (no explicit start method)")
        
        # 保持服务运行
        import signal
        import time
        
        def signal_handler(signum, frame):
            print(f"\\nReceived signal {{signum}}, shutting down JobManager...")
            try:
                if hasattr(job_manager.tcp_server, 'stop'):
                    job_manager.tcp_server.stop()
                elif hasattr(job_manager, 'shutdown'):
                    job_manager.shutdown()
                print("JobManager shutdown complete")
            except Exception as e:
                print(f"Error during shutdown: {{e}}")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("JobManager is running. Press Ctrl+C to stop.")
        
        # 主循环
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"JobManager startup failed: {{e}}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        # 使用绝对路径
        script_path = Path("/tmp/jobmanager_start.py")
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        return script_path
    
    def force_kill_port_process(self) -> bool:
        """强制杀死占用端口的进程"""
        try:
            # 使用lsof找到占用端口的进程
            result = subprocess.run(['lsof', '-ti', f':{self.port}'], 
                                capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0 or not result.stdout.strip():
                self.logger.info(f"No process found using port {self.port}")
                return True
            
            pids = result.stdout.strip().split('\n')
            killed_any = False
            
            for pid_str in pids:
                try:
                    pid = int(pid_str)
                    current_pid = os.getpid()
                    
                    # 不要杀死自己
                    if pid == current_pid:
                        continue
                    
                    self.logger.info(f"Force killing process {pid} using port {self.port}")
                    
                    # 先尝试SIGTERM
                    subprocess.run(['kill', '-TERM', str(pid)], 
                                capture_output=True, timeout=5)
                    time.sleep(2)
                    
                    # 检查进程是否还在运行
                    try:
                        proc = psutil.Process(pid)
                        if proc.is_running():
                            # 使用SIGKILL强制杀死
                            subprocess.run(['kill', '-KILL', str(pid)], 
                                        capture_output=True, timeout=5)
                            time.sleep(1)
                            
                        killed_any = True
                        self.logger.info(f"Successfully killed process {pid}")
                        
                    except psutil.NoSuchProcess:
                        killed_any = True
                        self.logger.info(f"Process {pid} already terminated")
                        
                except (ValueError, subprocess.TimeoutExpired) as e:
                    self.logger.error(f"Failed to kill process {pid_str}: {e}")
                    
            return killed_any
            
        except Exception as e:
            self.logger.error(f"Failed to force kill port processes: {e}")
            return False

    def stop_jobmanager(self) -> bool:
        """停止JobManager服务（改进版本）"""
        proc = self.get_jobmanager_process()
        
        if not proc:
            self.logger.warning("No JobManager process found through normal search")
            
            # 检查端口是否仍被占用
            if self.check_port():
                self.logger.warning(f"Port {self.port} is still occupied, attempting force kill")
                return self.force_kill_port_process()
            else:
                self.logger.info("Port is not occupied, nothing to stop")
                return True
            
        try:
            pid = proc.pid
            self.logger.info(f"Stopping JobManager process (PID: {pid})")
            
            # 使用subprocess执行kill命令，避免信号传播到当前进程
            try:
                # 先尝试SIGTERM
                result = subprocess.run(['kill', '-TERM', str(pid)], 
                                    capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.logger.info("Sent SIGTERM signal to JobManager")
                else:
                    self.logger.warning(f"Kill command failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                self.logger.warning("Kill command timed out")
            except FileNotFoundError:
                # 如果没有kill命令，回退到psutil
                self.logger.info("Using psutil terminate as fallback")
                try:
                    proc.terminate()
                except psutil.NoSuchProcess:
                    self.logger.info("Process already terminated")
                    return True
            
            # 等待进程结束
            max_wait = 100  # 10秒
            for i in range(max_wait):
                time.sleep(0.1)
                try:
                    # 检查进程是否还存在
                    if not proc.is_running():
                        self.logger.info("JobManager stopped gracefully")
                        break
                except psutil.NoSuchProcess:
                    self.logger.info("JobManager stopped gracefully")
                    break
            else:
                # 超时后强制杀死
                self.logger.warning("Graceful shutdown timeout, force killing...")
                try:
                    result = subprocess.run(['kill', '-KILL', str(pid)], 
                                        capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.logger.info("JobManager force killed")
                        time.sleep(1)  # 等待进程彻底结束
                    else:
                        self.logger.error(f"Force kill failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    self.logger.error("Force kill command timed out")
                except FileNotFoundError:
                    # 回退到psutil
                    try:
                        proc.kill()
                        proc.wait(timeout=5)
                        self.logger.info("JobManager force killed (psutil)")
                    except Exception as e:
                        self.logger.error(f"Force kill failed: {e}")
            
            # 清理PID文件
            if self.pidfile.exists():
                try:
                    self.pidfile.unlink()
                    self.logger.info("Cleaned up PID file")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up PID file: {e}")
                    
            # 最终检查端口是否释放
            time.sleep(1)
            if self.check_port():
                self.logger.error("Port is still occupied after stopping process")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop JobManager: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def status(self) -> dict:
        """获取JobManager状态"""
        port_occupied = self.check_port()
        service_healthy = False
        
        if port_occupied:
            self.logger.debug("Checking service health...")
            service_healthy = self.test_jobmanager_service()
        
        process = self.get_jobmanager_process()
        
        status = {
            "port_occupied": port_occupied,
            "service_healthy": service_healthy,
            "process_running": process is not None,
            "host": self.host,
            "port": self.port
        }
        
        if process:
            status.update({
                "pid": process.pid,
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "create_time": process.create_time()
            })
        
        return status
    
    def ensure_running(self) -> bool:
        """确保JobManager服务正在运行"""
        status = self.status()
        
        if status["service_healthy"]:
            self.logger.info("JobManager service is already running and healthy")
            return True
        
        if status["port_occupied"] and not status["service_healthy"]:
            self.logger.warning(f"Port {self.port} is occupied by unknown service")
            return False
        
        if status["process_running"] and not status["port_occupied"]:
            self.logger.warning("JobManager process exists but port not listening, restarting...")
            if not self.stop_jobmanager():
                self.logger.error("Failed to stop existing process")
                return False
            time.sleep(3)
        
        return self.start_jobmanager()


def main():
    parser = argparse.ArgumentParser(description="JobManager守护进程管理器")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "ensure"],
                       help="要执行的命令")
    parser.add_argument("--host", default="127.0.0.1", help="服务主机地址")
    parser.add_argument("--port", type=int, default=19000, help="服务端口")
    parser.add_argument("--pidfile", default="/tmp/jobmanager.pid", help="PID文件路径")
    parser.add_argument("--logfile", default="/tmp/jobmanager.log", help="日志文件路径")
    
    args = parser.parse_args()
    
    daemon = JobManagerDaemon(
        host=args.host,
        port=args.port,
        pidfile=args.pidfile,
        logfile=args.logfile
    )
    
    if args.command == "start":
        if daemon.ensure_running():
            print("✅ JobManager started successfully")
            sys.exit(0)
        else:
            print("❌ Failed to start JobManager")
            sys.exit(1)
            
    elif args.command == "stop":
        if daemon.stop_jobmanager():
            print("✅ JobManager stopped successfully")
            sys.exit(0)
        else:
            print("❌ Failed to stop JobManager")
            sys.exit(1)
            
    elif args.command == "restart":
        print("Stopping JobManager...")
        daemon.stop_jobmanager()
        time.sleep(2)
        print("Starting JobManager...")
        if daemon.ensure_running():
            print("✅ JobManager restarted successfully")
            sys.exit(0)
        else:
            print("❌ Failed to restart JobManager")
            sys.exit(1)
            
    elif args.command == "status":
        status = daemon.status()
        print(f"📊 JobManager Status:")
        print(f"   Host: {status['host']}:{status['port']}")
        print(f"   Port Occupied: {'✅' if status['port_occupied'] else '❌'}")
        print(f"   Service Healthy: {'✅' if status['service_healthy'] else '❌'}")
        print(f"   Process Running: {'✅' if status['process_running'] else '❌'}")
        
        if status['process_running']:
            print(f"   PID: {status['pid']}")
            print(f"   Memory: {status['memory_mb']} MB")
            print(f"   CPU: {status['cpu_percent']}%")
            
    elif args.command == "ensure":
        if daemon.ensure_running():
            print("✅ JobManager is running")
            sys.exit(0)
        else:
            print("❌ Failed to ensure JobManager is running")
            sys.exit(1)


if __name__ == "__main__":
    main()