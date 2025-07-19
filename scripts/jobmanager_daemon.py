#!/usr/bin/env python3
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
                return result == 0  # 0表示连接成功，端口被占用
        except Exception as e:
            self.logger.warning(f"Error checking port {self.port}: {e}")
            return False
    
    def test_jobmanager_service(self) -> bool:
        """测试JobManager服务是否正常响应"""
        if not self.check_port():
            return False
            
        try:
            import socket
            import json
            
            # 创建测试消息
            test_message = {
                "type": "env_status",
                "request_id": "test_request",
                "env_uuid": "test_uuid",
                "env_name": "test_env"
            }
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.host, self.port))
                
                # 发送测试消息
                message_str = json.dumps(test_message)
                message_bytes = message_str.encode('utf-8')
                length_header = len(message_bytes).to_bytes(4, byteorder='big')
                
                sock.sendall(length_header + message_bytes)
                
                # 接收响应
                response_length = int.from_bytes(sock.recv(4), byteorder='big')
                response_data = sock.recv(response_length)
                response = json.loads(response_data.decode('utf-8'))
                
                # 检查是否是有效的JobManager响应
                return (response.get('type') == 'env_status_response' or
                       response.get('payload', {}).get('error_code') == 'ERR_ENV_NOT_FOUND')
                
        except Exception as e:
            self.logger.warning(f"JobManager service test failed: {e}")
            return False
    
    def get_jobmanager_process(self) -> Optional[psutil.Process]:
        """查找JobManager进程"""
        try:
            if self.pidfile.exists():
                pid = int(self.pidfile.read_text().strip())
                try:
                    proc = psutil.Process(pid)
                    # 检查进程是否还在运行且是JobManager
                    if proc.is_running() and 'python' in proc.name().lower():
                        cmdline = ' '.join(proc.cmdline())
                        if 'jobmanager' in cmdline.lower() or 'engine.py' in cmdline:
                            return proc
                except psutil.NoSuchProcess:
                    pass
                    
                # PID文件存在但进程不存在，清理PID文件
                self.pidfile.unlink()
                
        except Exception as e:
            self.logger.warning(f"Error checking JobManager process: {e}")
            
        # 通过进程名查找
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if ('python' in proc.info['name'].lower() and
                        ('jobmanager' in cmdline.lower() or 'engine.py' in cmdline)):
                        return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.warning(f"Error searching JobManager processes: {e}")
            
        return None
    
    def start_jobmanager(self) -> bool:
        """启动JobManager服务"""
        try:
            # 准备启动脚本
            start_script = self._create_start_script()
            
            # 启动后台进程
            self.logger.info(f"Starting JobManager service on {self.host}:{self.port}")
            
            process = subprocess.Popen(
                [sys.executable, str(start_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # 创建新的会话组
                cwd=str(SAGE_ROOT)
            )
            
            # 记录PID
            self.pidfile.write_text(str(process.pid))
            self.logger.info(f"JobManager started with PID {process.pid}")
            
            # 等待服务启动
            for i in range(30):  # 最多等待30秒
                time.sleep(1)
                if self.test_jobmanager_service():
                    self.logger.info("JobManager service is ready")
                    return True
                if i % 5 == 0:
                    self.logger.info(f"Waiting for JobManager to start... ({i+1}/30)")
            
            self.logger.error("JobManager failed to start within 30 seconds")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start JobManager: {e}")
            return False
    
    def _create_start_script(self) -> Path:
        """创建JobManager启动脚本"""
        script_content = f'''#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# 添加项目路径
SAGE_ROOT = Path("{SAGE_ROOT}")
sys.path.insert(0, str(SAGE_ROOT))

# 导入并启动JobManager
from sage_jobmanager.engine import JobManager

def main():
    try:
        # 创建JobManager实例
        job_manager = JobManager(host="{self.host}", port={self.port})
        
        print(f"JobManager started on {{job_manager.tcp_server.host}}:{{job_manager.tcp_server.port}}")
        
        # 保持服务运行
        import signal
        import time
        
        def signal_handler(signum, frame):
            print("\\nShutting down JobManager...")
            try:
                job_manager.shutdown()
            except Exception as e:
                print(f"Error during shutdown: {{e}}")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 主循环
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"JobManager startup failed: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        script_path = Path("/tmp/jobmanager_start.py")
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        return script_path
    
    def stop_jobmanager(self) -> bool:
        """停止JobManager服务"""
        proc = self.get_jobmanager_process()
        if not proc:
            self.logger.info("No JobManager process found")
            return True
            
        try:
            self.logger.info(f"Stopping JobManager process (PID: {proc.pid})")
            
            # 尝试优雅关闭
            proc.terminate()
            
            # 等待进程结束
            try:
                proc.wait(timeout=10)
                self.logger.info("JobManager stopped gracefully")
            except psutil.TimeoutExpired:
                # 强制杀死
                self.logger.warning("Force killing JobManager process")
                proc.kill()
                proc.wait(timeout=5)
                
            # 清理PID文件
            if self.pidfile.exists():
                self.pidfile.unlink()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop JobManager: {e}")
            return False
    
    def status(self) -> dict:
        """获取JobManager状态"""
        port_occupied = self.check_port()
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
        
        if status["port_occupied"]:
            self.logger.warning(f"Port {self.port} is occupied by another service")
            return False
        
        if status["process_running"]:
            self.logger.warning("JobManager process exists but service is not healthy, restarting...")
            self.stop_jobmanager()
            time.sleep(2)
        
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