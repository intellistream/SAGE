#!/usr/bin/env python3
"""
SAGE CLI Utilities
==================

通用工具函数
"""

import os
import subprocess
import sys
import tempfile
import shutil
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
import time
import json
import yaml

from .exceptions import CLIException, ValidationError


def find_project_root(start_path: Optional[Path] = None, 
                     markers: List[str] = None) -> Optional[Path]:
    """
    查找项目根目录
    
    Args:
        start_path: 开始查找的路径，默认为当前目录
        markers: 用于识别项目根目录的标记文件/目录
        
    Returns:
        项目根目录路径，如果找不到返回None
    """
    if start_path is None:
        start_path = Path.cwd()
    
    if markers is None:
        markers = [
            "setup.py", "pyproject.toml", "requirements.txt", 
            ".git", "sage", "packages", "SAGE_API_REFACTOR_SUMMARY.md"
        ]
    
    current = Path(start_path).resolve()
    
    # 向上查找包含标记文件的路径
    for parent in [current] + list(current.parents):
        if any((parent / marker).exists() for marker in markers):
            return parent
    
    # 检查当前Python环境中的sage包位置
    try:
        import sage
        sage_path = Path(sage.__file__).parent.parent
        if any((sage_path / marker).exists() for marker in markers):
            return sage_path
    except ImportError:
        pass
    
    return None


def ensure_directory(path: Union[str, Path], parents: bool = True, 
                    exist_ok: bool = True) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
        parents: 是否创建父目录
        exist_ok: 如果目录已存在是否报错
        
    Returns:
        目录路径对象
        
    Raises:
        CLIException: 创建目录失败
    """
    path = Path(path)
    try:
        path.mkdir(parents=parents, exist_ok=exist_ok)
        return path
    except Exception as e:
        raise CLIException(f"Failed to create directory {path}: {e}")


def run_subprocess(command: Union[str, List[str]], 
                  cwd: Optional[Path] = None,
                  timeout: Optional[int] = None,
                  check: bool = True,
                  capture_output: bool = True,
                  text: bool = True,
                  shell: Optional[bool] = None,
                  env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    """
    执行子进程命令
    
    Args:
        command: 要执行的命令
        cwd: 工作目录
        timeout: 超时时间（秒）
        check: 是否检查返回码
        capture_output: 是否捕获输出
        text: 是否以文本模式处理输出
        shell: 是否使用shell
        env: 环境变量
        
    Returns:
        subprocess.CompletedProcess对象
        
    Raises:
        CLIException: 命令执行失败
    """
    if shell is None:
        shell = isinstance(command, str)
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            timeout=timeout,
            check=check,
            capture_output=capture_output,
            text=text,
            shell=shell,
            env=env
        )
        return result
    
    except subprocess.CalledProcessError as e:
        cmd_str = ' '.join(command) if isinstance(command, list) else command
        error_msg = f"Command failed: {cmd_str}"
        if e.stderr:
            error_msg += f"\nStderr: {e.stderr}"
        raise CLIException(error_msg, e.returncode)
    
    except subprocess.TimeoutExpired as e:
        cmd_str = ' '.join(command) if isinstance(command, list) else command
        raise CLIException(f"Command timeout: {cmd_str} (timeout: {timeout}s)")
    
    except Exception as e:
        cmd_str = ' '.join(command) if isinstance(command, list) else command
        raise CLIException(f"Unexpected error running command '{cmd_str}': {e}")


def load_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    加载YAML文件
    
    Args:
        file_path: YAML文件路径
        
    Returns:
        解析后的数据
        
    Raises:
        CLIException: 文件加载失败
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise CLIException(f"YAML file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise CLIException(f"Failed to load YAML file {file_path}: {e}")


def save_yaml_file(data: Dict[str, Any], file_path: Union[str, Path]):
    """
    保存数据到YAML文件
    
    Args:
        data: 要保存的数据
        file_path: YAML文件路径
        
    Raises:
        CLIException: 文件保存失败
    """
    file_path = Path(file_path)
    
    try:
        ensure_directory(file_path.parent)
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        raise CLIException(f"Failed to save YAML file {file_path}: {e}")


def load_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    加载JSON文件
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        解析后的数据
        
    Raises:
        CLIException: 文件加载失败
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise CLIException(f"JSON file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise CLIException(f"Failed to load JSON file {file_path}: {e}")


def save_json_file(data: Any, file_path: Union[str, Path], indent: int = 2):
    """
    保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        file_path: JSON文件路径
        indent: 缩进空格数
        
    Raises:
        CLIException: 文件保存失败
    """
    file_path = Path(file_path)
    
    try:
        ensure_directory(file_path.parent)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except Exception as e:
        raise CLIException(f"Failed to save JSON file {file_path}: {e}")


def resolve_path(path: Union[str, Path], base_path: Optional[Path] = None) -> Path:
    """
    解析路径，支持相对路径和波浪号扩展
    
    Args:
        path: 要解析的路径
        base_path: 基础路径，用于解析相对路径
        
    Returns:
        解析后的绝对路径
    """
    path = Path(path)
    
    if str(path).startswith('~'):
        path = path.expanduser()
    
    if not path.is_absolute() and base_path:
        path = base_path / path
    
    return path.resolve()


def is_port_available(host: str, port: int) -> bool:
    """
    检查端口是否可用
    
    Args:
        host: 主机地址
        port: 端口号
        
    Returns:
        True if port is available, False otherwise
    """
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0
    except Exception:
        return False


def wait_for_port(host: str, port: int, timeout: int = 30, 
                 check_interval: float = 1.0) -> bool:
    """
    等待端口变为可用（服务启动）
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间（秒）
        check_interval: 检查间隔（秒）
        
    Returns:
        True if port becomes available, False if timeout
    """
    import socket
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                if sock.connect_ex((host, port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(check_interval)
    
    return False


def create_temp_file(suffix: str = None, prefix: str = "sage_", 
                    content: str = None) -> Path:
    """
    创建临时文件
    
    Args:
        suffix: 文件后缀
        prefix: 文件前缀
        content: 文件内容
        
    Returns:
        临时文件路径
    """
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    temp_path = Path(temp_path)
    
    try:
        if content:
            with open(fd, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            os.close(fd)
        return temp_path
    except Exception as e:
        os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise CLIException(f"Failed to create temp file: {e}")


def create_temp_directory(prefix: str = "sage_") -> Path:
    """
    创建临时目录
    
    Args:
        prefix: 目录前缀
        
    Returns:
        临时目录路径
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    return Path(temp_dir)


def safe_delete(path: Union[str, Path], missing_ok: bool = True):
    """
    安全删除文件或目录
    
    Args:
        path: 要删除的路径
        missing_ok: 文件不存在是否报错
        
    Raises:
        CLIException: 删除失败
    """
    path = Path(path)
    
    try:
        if path.is_file():
            path.unlink(missing_ok=missing_ok)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=missing_ok)
    except Exception as e:
        if not missing_ok:
            raise CLIException(f"Failed to delete {path}: {e}")


def parse_key_value_pairs(pairs: List[str]) -> Dict[str, str]:
    """
    解析键值对列表
    
    Args:
        pairs: 键值对列表，格式为 ["key1=value1", "key2=value2"]
        
    Returns:
        解析后的字典
        
    Raises:
        ValidationError: 格式错误
    """
    result = {}
    
    for pair in pairs:
        if '=' not in pair:
            raise ValidationError(f"Invalid key-value pair format: {pair}")
        
        key, value = pair.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        if not key:
            raise ValidationError(f"Empty key in pair: {pair}")
        
        result[key] = value
    
    return result


def setup_signal_handlers(cleanup_func=None):
    """
    设置信号处理器
    
    Args:
        cleanup_func: 清理函数，在收到终止信号时调用
    """
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, cleaning up...")
        if cleanup_func:
            try:
                cleanup_func()
            except Exception as e:
                print(f"Error during cleanup: {e}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def format_command_for_display(command: Union[str, List[str]]) -> str:
    """
    格式化命令用于显示
    
    Args:
        command: 命令
        
    Returns:
        格式化后的命令字符串
    """
    if isinstance(command, list):
        return ' '.join(command)
    return command
