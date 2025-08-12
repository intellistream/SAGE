#!/usr/bin/env python3
"""
SAGE 统一工具模块 (Enhanced)
==========================

提供开发环境和PyPI环境都能使用的工具函数，
替代原来分散在scripts/目录下的bash脚本。

Features:
- 彩色日志输出
- 进度条显示  
- 系统检查
- Conda环境管理
- 用户交互
- 进程运行
"""

import os
import sys
import subprocess
import platform
import shutil
import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

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
    """增强的彩色日志输出类"""
    
    @staticmethod
    def print_status(message: str):
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")
    
    @staticmethod
    def print_success(message: str):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")
    
    @staticmethod
    def print_warning(message: str):
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")
    
    @staticmethod
    def print_error(message: str):
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")
    
    @staticmethod
    def print_header(message: str):
        print(f"\n{Colors.PURPLE}{'='*60}{Colors.NC}")
        print(f"{Colors.PURPLE}{message}{Colors.NC}")
        print(f"{Colors.PURPLE}{'='*60}{Colors.NC}\n")
    
    @staticmethod
    def print_debug(message: str):
        if os.environ.get('SAGE_DEBUG', '0') == '1':
            print(f"{Colors.CYAN}[DEBUG]{Colors.NC} {message}")

class ProgressBar:
    """进度条显示类"""
    
    def __init__(self, total: int, width: int = 50):
        self.total = total
        self.current = 0
        self.width = width
        
    def update(self, current: int, message: str = ""):
        self.current = current
        percentage = int(current * 100 / self.total)
        filled = int(current * self.width / self.total)
        empty = self.width - filled
        
        bar = "=" * filled + "-" * empty
        print(f"\r[{bar}] {percentage:3d}% {message}", end="", flush=True)
        
        if current >= self.total:
            print()  # 完成后换行

class SystemChecker:
    """系统检查工具类"""
    
    @staticmethod
    def check_command(command: str, required: bool = True, quiet: bool = False) -> bool:
        """检查命令是否存在"""
        if shutil.which(command):
            if not required and not quiet:  # 仅在详细模式下显示
                Logger.print_success(f"✅ {command} 可用")
            return True
        else:
            if required and not quiet:
                Logger.print_error(f"❌ {command} 未安装或不可用")
            elif not quiet:
                Logger.print_warning(f"⚠️  {command} 不可用 (可选)")
            return False
    
    @staticmethod
    def check_python_version(min_version: tuple = (3, 10), quiet: bool = False) -> bool:
        current = sys.version_info[:2]
        if current >= min_version:
            if not quiet:
                Logger.print_success(f"✅ Python {'.'.join(map(str, current))} (满足要求)")
            return True
        else:
            if not quiet:
                Logger.print_error(f"❌ Python {'.'.join(map(str, min_version))}+ 需要, 当前: {'.'.join(map(str, current))}")
            return False
    
    @staticmethod
    def check_disk_space(min_gb: float = 1.0, quiet: bool = False) -> bool:
        try:
            statvfs = os.statvfs('.')
            free_bytes = statvfs.f_frsize * statvfs.f_bavail
            free_gb = free_bytes / (1024**3)
            
            if free_gb >= min_gb:
                if not quiet:
                    Logger.print_success(f"✅ 磁盘空间: {free_gb:.1f}GB 可用")
                return True
            else:
                if not quiet:
                    Logger.print_error(f"❌ 磁盘空间不足: {free_gb:.1f}GB (需要 {min_gb}GB)")
                return False
        except:
            if not quiet:
                Logger.print_warning("⚠️  无法检查磁盘空间")
            return True
    
    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """获取系统信息"""
        return {
            'platform': platform.system(),
            'architecture': platform.machine(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'python_executable': sys.executable,
            'conda_env': os.environ.get('CONDA_DEFAULT_ENV', 'None'),
            'is_conda': 'conda' in sys.executable or 'CONDA_DEFAULT_ENV' in os.environ
        }

class CondaManager:
    """Conda环境管理类 - 替代conda_utils.sh"""
    
    @staticmethod
    def is_conda_available(quiet: bool = False) -> bool:
        """检查conda是否可用"""
        return SystemChecker.check_command('conda', required=False, quiet=quiet)
    
    @staticmethod
    def list_environments() -> List[str]:
        """列出所有conda环境"""
        try:
            result = subprocess.run(['conda', 'env', 'list', '--json'], 
                                  capture_output=True, text=True, check=True)
            envs_data = json.loads(result.stdout)
            env_names = []
            for env_path in envs_data['envs']:
                env_name = Path(env_path).name
                if env_name != 'envs':  # 跳过envs目录本身
                    env_names.append(env_name)
            return env_names
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []
    
    @staticmethod
    def environment_exists(env_name: str) -> bool:
        """检查环境是否存在"""
        envs = CondaManager.list_environments()
        return env_name in envs
    
    @staticmethod
    def create_environment(env_name: str, python_version: str = "3.11") -> bool:
        """创建conda环境"""
        Logger.print_status(f"创建conda环境: {env_name} (Python {python_version})")
        try:
            cmd = ['conda', 'create', '-n', env_name, f'python={python_version}', '-y']
            result = subprocess.run(cmd, check=True)
            Logger.print_success(f"环境 {env_name} 创建成功")
            return True
        except subprocess.CalledProcessError as e:
            Logger.print_error(f"环境创建失败: {e}")
            return False
    
    @staticmethod
    def remove_environment(env_name: str) -> bool:
        """删除conda环境"""
        Logger.print_warning(f"删除conda环境: {env_name}")
        try:
            cmd = ['conda', 'env', 'remove', '-n', env_name, '-y']
            result = subprocess.run(cmd, check=True)
            Logger.print_success(f"环境 {env_name} 删除成功")
            return True
        except subprocess.CalledProcessError as e:
            Logger.print_error(f"环境删除失败: {e}")
            return False

class UserInteraction:
    """用户交互工具类"""
    
    @staticmethod
    def confirm(message: str, default: bool = True) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            try:
                response = input(f"{message} {suffix}: ").strip().lower()
                if not response:
                    return default
                if response in ['y', 'yes', '是']:
                    return True
                elif response in ['n', 'no', '否']:
                    return False
                else:
                    Logger.print_warning("请输入 y/yes 或 n/no")
            except KeyboardInterrupt:
                Logger.print_warning("\n操作已取消")
                return False
    
    @staticmethod
    def select_option(prompt: str, options: List[str], default: int = 0) -> int:
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
                return -1
    
    @staticmethod
    def input_with_default(prompt: str, default: str = "") -> str:
        if default:
            full_prompt = f"{prompt} [默认: {default}]: "
        else:
            full_prompt = f"{prompt}: "
        
        try:
            response = input(full_prompt).strip()
            return response if response else default
        except KeyboardInterrupt:
            Logger.print_warning("\n操作已取消")
            return default

class ProcessRunner:
    """进程运行工具类 - 替代部分common_utils.sh功能"""
    
    @staticmethod
    def run_command(cmd: List[str], description: str = "", 
                   show_output: bool = False, timeout: int = 300,
                   env: Optional[Dict[str, str]] = None) -> Tuple[bool, str, str]:
        """运行命令并返回结果"""
        if description:
            Logger.print_status(f"🔄 {description}...")
        
        try:
            if show_output:
                result = subprocess.run(cmd, timeout=timeout, check=True, env=env)
                stdout, stderr = "", ""
            else:
                result = subprocess.run(cmd, capture_output=True, 
                                     text=True, timeout=timeout, check=True, env=env)
                stdout, stderr = result.stdout, result.stderr
            
            if description:
                Logger.print_success(f"✅ {description} 完成")
            return True, stdout, stderr
            
        except subprocess.CalledProcessError as e:
            if description:
                Logger.print_error(f"❌ {description} 失败")
            stderr = getattr(e, 'stderr', '') or str(e)
            return False, "", stderr
        except subprocess.TimeoutExpired:
            Logger.print_error(f"❌ {description} 超时")
            return False, "", "Command timeout"
    
    @staticmethod
    def run_pip_command(args: List[str], description: str = "") -> bool:
        """运行pip命令"""
        cmd = [sys.executable, "-m", "pip"] + args
        success, stdout, stderr = ProcessRunner.run_command(
            cmd, description or f"执行 pip {' '.join(args)}")
        return success
    
    @staticmethod
    def run_conda_command(args: List[str], env_name: str = None, description: str = "") -> bool:
        """运行conda命令"""
        cmd = ['conda'] + args
        if env_name:
            cmd.extend(['-n', env_name])
        
        success, stdout, stderr = ProcessRunner.run_command(
            cmd, description or f"执行 conda {' '.join(args)}")
        return success

class FileManager:
    """文件管理工具类 - 替代部分common_utils.sh功能"""
    
    @staticmethod
    def check_file_exists(file_path: str, description: str = "文件") -> bool:
        if Path(file_path).exists():
            return True
        else:
            Logger.print_error(f"{description} 不存在: {file_path}")
            return False
    
    @staticmethod
    def check_dir_exists(dir_path: str, description: str = "目录") -> bool:
        if Path(dir_path).is_dir():
            return True
        else:
            Logger.print_error(f"{description} 不存在: {dir_path}")
            return False
    
    @staticmethod
    def create_directory(dir_path: str, description: str = "目录") -> bool:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            Logger.print_success(f"✅ {description} 创建成功: {dir_path}")
            return True
        except Exception as e:
            Logger.print_error(f"❌ {description} 创建失败: {e}")
            return False
    
    @staticmethod
    def backup_file(file_path: str) -> Optional[str]:
        """备份文件"""
        try:
            backup_path = f"{file_path}.backup.{int(time.time())}"
            shutil.copy2(file_path, backup_path)
            Logger.print_success(f"文件已备份: {backup_path}")
            return backup_path
        except Exception as e:
            Logger.print_error(f"备份文件失败: {e}")
            return None

# 便捷的全局实例
logger = Logger()
checker = SystemChecker()
conda_mgr = CondaManager()
interact = UserInteraction()
runner = ProcessRunner()
file_mgr = FileManager()

def create_progress_bar(total: int, width: int = 50) -> ProgressBar:
    """创建进度条"""
    return ProgressBar(total, width)

def main():
    """测试功能"""
    logger.print_header("SAGE 统一工具模块测试")
    
    # 测试系统检查
    info = checker.get_system_info()
    for key, value in info.items():
        logger.print_status(f"{key}: {value}")
    
    # 测试conda功能
    if conda_mgr.is_conda_available():
        envs = conda_mgr.list_environments()
        logger.print_status(f"发现 {len(envs)} 个conda环境")
    
    logger.print_success("工具模块测试完成")

if __name__ == "__main__":
    main()
