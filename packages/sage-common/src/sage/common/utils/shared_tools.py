#!/usr/bin/env python3
"""
SAGE 通用工具模块
================

提供彩色日志、进度显示、用户交互等高级功能，
可以被PyPI安装工具和其他Python脚本共享使用。
"""

import os
import sys
import time
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path

# ANSI 颜色代码
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

class Logger:
    """彩色日志输出类"""
    
    @staticmethod
    def print_status(message: str):
        """打印状态信息"""
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")
    
    @staticmethod
    def print_success(message: str):
        """打印成功信息"""
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")
    
    @staticmethod
    def print_warning(message: str):
        """打印警告信息"""
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")
    
    @staticmethod
    def print_error(message: str):
        """打印错误信息"""
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")
    
    @staticmethod
    def print_header(message: str):
        """打印标题"""
        print(f"\n{Colors.PURPLE}{'='*50}{Colors.NC}")
        print(f"{Colors.PURPLE}{message}{Colors.NC}")
        print(f"{Colors.PURPLE}{'='*50}{Colors.NC}\n")
    
    @staticmethod
    def print_debug(message: str):
        """打印调试信息"""
        if os.environ.get('SAGE_DEBUG', '0') == '1':
            print(f"{Colors.CYAN}[DEBUG]{Colors.NC} {message}")

class ProgressBar:
    """进度条显示类"""
    
    def __init__(self, total: int, width: int = 50):
        self.total = total
        self.current = 0
        self.width = width
        
    def update(self, current: int, message: str = ""):
        """更新进度"""
        self.current = current
        percentage = int(current * 100 / self.total)
        filled = int(current * self.width / self.total)
        empty = self.width - filled
        
        bar = "=" * filled + "-" * empty
        print(f"\r[{bar}] {percentage:3d}% {message}", end="", flush=True)
        
        if current >= self.total:
            print()  # 完成后换行
    
    def step(self, message: str = ""):
        """前进一步"""
        self.update(self.current + 1, message)

class UserInteraction:
    """用户交互工具类"""
    
    @staticmethod
    def confirm(message: str, default: bool = True) -> bool:
        """确认对话框"""
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            response = input(f"{message} {suffix}: ").strip().lower()
            if not response:
                return default
            if response in ['y', 'yes', '是']:
                return True
            elif response in ['n', 'no', '否']:
                return False
            else:
                Logger.print_warning("请输入 y/yes 或 n/no")
    
    @staticmethod
    def select_option(prompt: str, options: List[str], default: int = 0) -> int:
        """选择选项"""
        print(f"\n{prompt}")
        for i, option in enumerate(options, 1):
            prefix = "* " if i == default + 1 else "  "
            print(f"{prefix}{i}. {option}")
        
        while True:
            try:
                choice = input(f"\n请选择 [1-{len(options)}]: ").strip()
                if not choice:
                    return default
                
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    return idx
                else:
                    Logger.print_warning(f"请输入 1-{len(options)} 之间的数字")
            except ValueError:
                Logger.print_warning("请输入有效的数字")
            except KeyboardInterrupt:
                Logger.print_warning("\n操作已取消")
                sys.exit(0)
    
    @staticmethod
    def input_with_default(prompt: str, default: str = "") -> str:
        """带默认值的输入"""
        if default:
            full_prompt = f"{prompt} [默认: {default}]: "
        else:
            full_prompt = f"{prompt}: "
        
        response = input(full_prompt).strip()
        return response if response else default

class SystemChecker:
    """系统检查工具类"""
    
    @staticmethod
    def check_command(command: str, required: bool = True) -> bool:
        """检查命令是否存在"""
        try:
            subprocess.run([command, "--version"], 
                         capture_output=True, check=True, timeout=5)
            Logger.print_success(f"✅ {command} 可用")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            if required:
                Logger.print_error(f"❌ {command} 未安装或不可用")
            else:
                Logger.print_warning(f"⚠️  {command} 不可用 (可选)")
            return False
    
    @staticmethod
    def check_python_version(min_version: tuple = (3, 10)) -> bool:
        """检查Python版本"""
        current = sys.version_info[:2]
        if current >= min_version:
            Logger.print_success(f"✅ Python {'.'.join(map(str, current))} (满足要求)")
            return True
        else:
            Logger.print_error(f"❌ Python {'.'.join(map(str, min_version))}+ 需要, 当前: {'.'.join(map(str, current))}")
            return False
    
    @staticmethod
    def check_disk_space(min_gb: float = 1.0) -> bool:
        """检查磁盘空间"""
        try:
            statvfs = os.statvfs('.')
            free_bytes = statvfs.f_frsize * statvfs.f_bavail
            free_gb = free_bytes / (1024**3)
            
            if free_gb >= min_gb:
                Logger.print_success(f"✅ 磁盘空间: {free_gb:.1f}GB 可用")
                return True
            else:
                Logger.print_error(f"❌ 磁盘空间不足: {free_gb:.1f}GB (需要 {min_gb}GB)")
                return False
        except:
            Logger.print_warning("⚠️  无法检查磁盘空间")
            return True
    
    @staticmethod
    def check_network_connection(host: str = "pypi.org", port: int = 443) -> bool:
        """检查网络连接"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                Logger.print_success(f"✅ 网络连接正常 ({host})")
                return True
            else:
                Logger.print_warning(f"⚠️  网络连接可能有问题 ({host})")
                return False
        except Exception as e:
            Logger.print_warning(f"⚠️  网络检查失败: {e}")
            return False

class ProcessRunner:
    """进程运行工具类"""
    
    @staticmethod
    def run_command(cmd: List[str], description: str = "", 
                   show_output: bool = False, timeout: int = 300) -> bool:
        """运行命令并显示进度"""
        if description:
            Logger.print_status(f"🔄 {description}...")
        
        try:
            if show_output:
                result = subprocess.run(cmd, timeout=timeout, check=True)
            else:
                result = subprocess.run(cmd, capture_output=True, 
                                     text=True, timeout=timeout, check=True)
            
            if description:
                Logger.print_success(f"✅ {description} 完成")
            return True
            
        except subprocess.CalledProcessError as e:
            if description:
                Logger.print_error(f"❌ {description} 失败")
            if not show_output and e.stderr:
                Logger.print_error(f"错误输出: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            Logger.print_error(f"❌ {description} 超时")
            return False
    
    @staticmethod
    def run_pip_install(packages: List[str], description: str = "") -> bool:
        """运行pip安装"""
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        return ProcessRunner.run_command(cmd, description or f"安装 {', '.join(packages)}")

# 便捷的全局实例
logger = Logger()
checker = SystemChecker()
runner = ProcessRunner()
interact = UserInteraction()

def create_progress_bar(total: int, width: int = 50) -> ProgressBar:
    """创建进度条"""
    return ProgressBar(total, width)
