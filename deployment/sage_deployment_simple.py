#!/usr/bin/env python3
"""
SAGE System Deployment Script - Simplified Python Version
SAGE系统部署脚本 - 简化Python版本

更简洁、更Pythonic的实现
"""

import os
import sys
import subprocess
import shutil
import time
import signal
import argparse
import pwd
import grp
import logging
from pathlib import Path
import socket
import psutil

# 简单的日志配置
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class Colors:
    """颜色常量"""
    RED, GREEN, YELLOW, BLUE, NC = '\033[0;31m', '\033[0;32m', '\033[1;33m', '\033[0;34m', '\033[0m'

def log(level, message):
    """统一的日志函数"""
    color = {'INFO': Colors.BLUE, 'SUCCESS': Colors.GREEN, 'WARNING': Colors.YELLOW, 'ERROR': Colors.RED}.get(level, '')
    print(f"{color}[{level}]{Colors.NC} {message}")
    if level != 'SUCCESS':
        logger.info(f"{level}: {message}")

def run_cmd(cmd, check=True, capture=False, timeout=30):
    """运行命令的简化版本"""
    try:
        return subprocess.run(cmd, shell=isinstance(cmd, str), check=check, 
                            capture_output=capture, text=True, timeout=timeout)
    except subprocess.CalledProcessError as e:
        if check:
            log('ERROR', f"Command failed: {cmd}")
            raise
        return e
    except subprocess.TimeoutExpired:
        log('ERROR', f"Command timed out: {cmd}")
        raise

def is_port_open(port):
    """检查端口是否被占用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0
    except:
        return False

def find_processes(pattern):
    """查找包含指定模式的进程"""
    pids = []
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if pattern in cmdline:
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids

def kill_processes(pattern):
    """终止包含指定模式的进程"""
    pids = find_processes(pattern)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if pids:
        time.sleep(2)
        # 强制杀死残留进程
        for pid in find_processes(pattern):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

class SAGEDeployer:
    """SAGE部署器 - 简化版"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.config = {
            'ray_head_port': int(os.environ.get('RAY_HEAD_PORT', 10001)),
            'ray_dashboard_port': int(os.environ.get('RAY_DASHBOARD_PORT', 8265)),
            'ray_temp_dir': os.environ.get('RAY_TEMP_DIR', '/tmp/ray_shared'),
            'daemon_port': int(os.environ.get('DAEMON_PORT', 19001))
        }
        
        # 信号处理
        signal.signal(signal.SIGINT, self._cleanup_and_exit)
        signal.signal(signal.SIGTERM, self._cleanup_and_exit)
    
    def _cleanup_and_exit(self, signum, frame):
        """信号处理：清理并退出"""
        log('INFO', "Interrupted, stopping system...")
        self.stop()
        sys.exit(1)
    
    def is_ray_running(self):
        """检查Ray是否运行"""
        if shutil.which('ray'):
            result = run_cmd(['ray', 'status'], check=False, capture=True)
            return result.returncode == 0
        return len(find_processes('ray')) > 0
    
    def is_daemon_running(self):
        """检查守护进程是否运行"""
        return len(find_processes('jobmanager_daemon.py')) > 0
    
    def start_ray(self):
        """启动Ray集群"""
        if self.is_ray_running():
            log('SUCCESS', "Ray cluster already running")
            return True
        
        log('INFO', "Starting Ray cluster...")
        
        # 创建临时目录
        Path(self.config['ray_temp_dir']).mkdir(parents=True, exist_ok=True)
        
        cmd = [
            'ray', 'start', '--head',
            f'--port={self.config["ray_head_port"]}',
            f'--dashboard-port={self.config["ray_dashboard_port"]}',
            f'--temp-dir={self.config["ray_temp_dir"]}',
            '--resources={"jobmanager": 1.0}'
        ]
        
        try:
            run_cmd(cmd)
            log('SUCCESS', "Ray cluster started")
            return True
        except:
            # 备用方案
            log('WARNING', "Retrying with fallback config...")
            cmd[-2] = '--temp-dir=/tmp/ray_shared'
            try:
                run_cmd(cmd)
                log('SUCCESS', "Ray cluster started with fallback config")
                return True
            except Exception as e:
                log('ERROR', f"Failed to start Ray: {e}")
                return False
    
    def stop_ray(self):
        """停止Ray集群"""
        if not self.is_ray_running():
            return True
        
        log('INFO', "Stopping Ray cluster...")
        
        if shutil.which('ray'):
            run_cmd(['ray', 'stop'], check=False)
        else:
            kill_processes('ray')
        
        log('SUCCESS', "Ray cluster stopped")
        return True
    
    def start_daemon(self):
        """启动守护进程"""
        if self.is_daemon_running():
            log('SUCCESS', "JobManager Daemon already running")
            return True
        
        log('INFO', "Starting JobManager Daemon...")
        
        daemon_script = self.script_dir / 'app' / 'jobmanager_daemon.py'
        if not daemon_script.exists():
            log('ERROR', f"Daemon script not found: {daemon_script}")
            return False
        
        # 后台启动守护进程
        subprocess.Popen([sys.executable, str(daemon_script)], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 等待启动
        time.sleep(2)
        
        if self.is_daemon_running():
            log('SUCCESS', "JobManager Daemon started")
            return True
        else:
            log('ERROR', "Failed to start JobManager Daemon")
            return False
    
    def stop_daemon(self):
        """停止守护进程"""
        if not self.is_daemon_running():
            return True
        
        log('INFO', "Stopping JobManager Daemon...")
        kill_processes('jobmanager_daemon.py')
        log('SUCCESS', "JobManager Daemon stopped")
        return True
    
    def setup_system_install(self):
        """系统级安装 - 简化版"""
        if os.geteuid() != 0:
            log('ERROR', "System installation requires root privileges")
            return False
        
        log('INFO', "Performing system installation...")
        
        # 创建组
        try:
            grp.getgrnam('sage')
        except KeyError:
            run_cmd(['groupadd', 'sage'])
            log('SUCCESS', "Created sage group")
        
        # 创建目录
        dirs = ['/usr/local/lib/sage', '/var/log/sage', '/var/lib/sage', '/etc/sage']
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        files = [
            ('app/jobmanager_controller.py', '/usr/local/lib/sage/jobmanager_controller.py'),
            ('scripts/sage_jm_wrapper.sh', '/usr/local/lib/sage/sage_jm_wrapper.sh')
        ]
        
        for src, dst in files:
            src_path = self.script_dir / src
            if src_path.exists():
                shutil.copy2(src_path, dst)
                Path(dst).chmod(0o755 if dst.endswith('.sh') else 0o644)
        
        # 创建CLI符号链接
        cli_link = Path('/usr/local/bin/sage-jm')
        wrapper = Path('/usr/local/lib/sage/sage_jm_wrapper.sh')
        
        if cli_link.exists():
            cli_link.unlink()
        cli_link.symlink_to(wrapper)
        
        # 设置权限
        sage_gid = grp.getgrnam('sage').gr_gid
        for d in dirs:
            os.chown(d, 0, sage_gid)
            Path(d).chmod(0o775)
        
        log('SUCCESS', "System installation completed")
        return True
    
    def setup_permissions(self):
        """设置权限 - 简化版"""
        # 创建用户目录
        dirs = [Path.home() / 'sage_logs', Path('/tmp/sage')]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        
        # 设置系统目录权限（如果存在）
        for d in ['/var/log/sage', '/var/lib/sage']:
            path = Path(d)
            if path.exists():
                try:
                    path.chmod(0o775)
                except PermissionError:
                    pass
    
    def setup_cli(self):
        """设置CLI工具 - 简化版"""
        # 检查系统级安装
        system_cli = Path('/usr/local/bin/sage-jm')
        if system_cli.exists() and system_cli.is_symlink():
            log('SUCCESS', "System-level CLI installation detected")
            return True
        
        # 开发模式设置
        wrapper = self.script_dir / 'scripts' / 'sage_jm_wrapper.sh'
        if not wrapper.exists():
            log('ERROR', "CLI wrapper script not found")
            return False
        
        wrapper.chmod(0o755)
        
        # 尝试创建系统级链接
        if shutil.which('sudo') and run_cmd(['sudo', '-n', 'true'], check=False).returncode == 0:
            try:
                if system_cli.exists():
                    run_cmd(['sudo', 'rm', '-f', str(system_cli)])
                run_cmd(['sudo', 'ln', '-s', str(wrapper), str(system_cli)])
                log('SUCCESS', "CLI command installed")
                return True
            except:
                pass
        
        log('WARNING', f"CLI available at: {wrapper}")
        return False
    
    def start(self):
        """启动系统"""
        log('INFO', "=== Starting SAGE System ===")
        
        # 显示配置
        log('INFO', f"Ray GCS Port: {self.config['ray_head_port']}")
        log('INFO', f"Ray Dashboard: {self.config['ray_dashboard_port']}")
        log('INFO', f"Daemon Port: {self.config['daemon_port']}")
        
        success = True
        success &= self.start_ray()
        success &= self.start_daemon()
        
        # 验证CLI
        if shutil.which('sage-jm'):
            result = run_cmd(['sage-jm', 'health'], check=False, capture=True, timeout=5)
            if result.returncode == 0:
                log('SUCCESS', "CLI tools working")
            else:
                log('WARNING', "CLI tools cannot connect to daemon")
        
        self.status()
        
        if success:
            log('SUCCESS', "=== SAGE System Started Successfully ===")
            self._show_usage()
        
        return success
    
    def stop(self):
        """停止系统"""
        log('INFO', "=== Stopping SAGE System ===")
        
        success = True
        success &= self.stop_daemon()
        success &= self.stop_ray()
        
        if success:
            log('SUCCESS', "SAGE system stopped")
        return success
    
    def restart(self):
        """重启系统"""
        self.stop()
        time.sleep(3)
        return self.start()
    
    def status(self):
        """显示系统状态"""
        log('INFO', "=== System Status ===")
        
        # Ray状态
        if self.is_ray_running():
            log('SUCCESS', "Ray cluster: Running")
            if shutil.which('ray'):
                result = run_cmd(['ray', 'status'], check=False, capture=True)
                if result.returncode == 0:
                    # 显示前几行资源信息
                    lines = result.stdout.split('\n')[:3]
                    for line in lines:
                        if line.strip():
                            print(f"  {line}")
        else:
            log('WARNING', "Ray cluster: Stopped")
        
        # 守护进程状态
        daemon_pids = find_processes('jobmanager_daemon.py')
        if daemon_pids:
            log('SUCCESS', f"JobManager Daemon: Running (PIDs: {daemon_pids})")
        else:
            log('WARNING', "JobManager Daemon: Stopped")
        
        # CLI状态
        if shutil.which('sage-jm'):
            log('SUCCESS', "CLI tools: Available")
            result = run_cmd(['sage-jm', 'health'], check=False, capture=True, timeout=5)
            status = "Connected" if result.returncode == 0 else "Cannot connect"
            print(f"  Status: {status}")
        else:
            log('WARNING', "CLI tools: Not found")
        
        # 端口状态
        log('INFO', "Port usage:")
        ports = [
            ('Ray GCS', self.config['ray_head_port']),
            ('Ray Dashboard', self.config['ray_dashboard_port']),
            ('Daemon', self.config['daemon_port'])
        ]
        
        for name, port in ports:
            status = "In use ✓" if is_port_open(port) else "Available"
            print(f"  {name} port {port}: {status}")
    
    def _show_usage(self):
        """显示使用指南"""
        print(f"\n{Colors.GREEN}🎉 SAGE system ready!{Colors.NC}")
        print(f"\n{Colors.GREEN}💻 CLI Commands:{Colors.NC}")
        print("  sage-jm status    # Check status")
        print("  sage-jm submit    # Submit job")
        print("  sage-jm list      # List jobs")
        print(f"\n{Colors.GREEN}🌐 Dashboard:{Colors.NC}")
        print(f"  http://localhost:{self.config['ray_dashboard_port']}")
        print(f"\n{Colors.GREEN}🔄 Management:{Colors.NC}")
        print(f"  python3 {__file__} status")
        print(f"  python3 {__file__} stop")
        print(f"  python3 {__file__} restart")
    
    def full_deploy(self):
        """完整部署"""
        log('INFO', "=== Starting SAGE Full Deployment ===")
        
        # 系统级安装（如果有权限）
        if os.geteuid() == 0:
            self.setup_system_install()
        elif shutil.which('sudo') and run_cmd(['sudo', '-n', 'true'], check=False).returncode == 0:
            try:
                response = input("Perform system installation? [Y/n] ").strip().lower()
                if response not in ['n', 'no']:
                    result = subprocess.run(['sudo', sys.executable, __file__, 'system-install'])
                    if result.returncode != 0:
                        log('ERROR', "System installation failed")
                        return False
            except KeyboardInterrupt:
                log('INFO', "Installation cancelled")
                return False
        else:
            log('WARNING', "No sudo access, running in development mode")
        
        # 设置权限和CLI
        self.setup_permissions()
        self.setup_cli()
        
        # 启动系统
        success = self.start()
        
        if success:
            log('SUCCESS', "=== Full Deployment Completed ===")
        
        return success

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SAGE Deployment - Simplified Python Version")
    parser.add_argument('command', nargs='?', 
                       choices=['start', 'stop', 'restart', 'status', 'install-system', 'system-install'],
                       help='Command to execute (default: full deployment)')
    
    args = parser.parse_args()
    deployer = SAGEDeployer()
    
    try:
        if args.command is None:
            success = deployer.full_deploy()
        elif args.command == 'start':
            deployer.setup_permissions()
            success = deployer.start()
        elif args.command == 'stop':
            success = deployer.stop()
        elif args.command == 'restart':
            success = deployer.restart()
        elif args.command == 'status':
            deployer.status()
            success = True
        elif args.command in ['install-system', 'system-install']:
            success = deployer.setup_system_install()
        else:
            parser.print_help()
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        log('INFO', "Interrupted by user")
        sys.exit(1)
    except Exception as e:
        log('ERROR', f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
