#!/usr/bin/env python3
"""
SAGE CLI Base Classes
=====================

基础CLI命令类和装饰器
"""

import functools
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Union

import typer

from .exceptions import CLIException, ConfigurationError, ConnectionError
from .output import OutputFormatter, print_status
from .config import load_and_validate_config, create_default_config_validator
from .utils import find_project_root


class BaseCommand(ABC):
    """基础命令类"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None,
                 output_format: str = "table", use_colors: bool = True):
        self.config_path = config_path
        self.config = None
        self.formatter = OutputFormatter(colors=use_colors, format_type=output_format)
        self.project_root = None
        
        # 初始化配置
        self._load_config()
        
        # 查找项目根目录
        self._find_project_root()
    
    def _load_config(self):
        """加载配置文件"""
        if self.config_path is None:
            # 使用默认配置路径
            self.config_path = Path.home() / ".sage" / "config.yaml"
        
        if isinstance(self.config_path, str):
            self.config_path = Path(self.config_path)
        
        try:
            if self.config_path.exists():
                self.config = load_and_validate_config(self.config_path)
            else:
                # 如果配置文件不存在，提示用户创建
                self.formatter.print_warning(f"Configuration file not found: {self.config_path}")
                self.formatter.print_info("Run 'sage config init' to create a default configuration")
                self.config = {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _find_project_root(self):
        """查找项目根目录"""
        self.project_root = find_project_root()
        if not self.project_root:
            self.formatter.print_warning("Project root directory not found")
    
    @abstractmethod
    def execute(self, *args, **kwargs):
        """执行命令的主要逻辑"""
        pass
    
    def get_config_section(self, section_name: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取配置节"""
        return self.config.get(section_name, default or {})
    
    def validate_config_exists(self):
        """验证配置文件存在"""
        if not self.config or not self.config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}\n"
                "Please run 'sage config init' to create a default configuration"
            )
    
    def print_section_header(self, title: str):
        """打印节标题"""
        self.formatter.print_section(title)
    
    def handle_exception(self, e: Exception) -> int:
        """处理异常并返回退出码"""
        if isinstance(e, CLIException):
            self.formatter.print_error(str(e))
            return e.exit_code
        else:
            self.formatter.print_error(f"Unexpected error: {e}")
            return 1


class ServiceCommand(BaseCommand):
    """服务管理命令基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection_required = False
        self._connected = False
    
    def require_connection(self):
        """标记此命令需要连接"""
        self.connection_required = True
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass
    
    def ensure_connected(self):
        """确保已连接"""
        if self.connection_required and not self.is_connected():
            if not self.connect():
                raise ConnectionError("Failed to establish connection")
    
    def execute_with_connection(self, func: Callable, *args, **kwargs):
        """在确保连接的情况下执行函数"""
        self.ensure_connected()
        return func(*args, **kwargs)


class RemoteCommand(BaseCommand):
    """远程命令执行基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssh_manager = None
        self.remote_executor = None
    
    def _setup_ssh(self):
        """设置SSH连接"""
        ssh_config = self.get_config_section('ssh')
        
        if not ssh_config:
            raise ConfigurationError("SSH configuration not found")
        
        from .ssh import SSHConfig, SSHManager, RemoteExecutor
        
        ssh_conf = SSHConfig(
            user=ssh_config.get('user', 'sage'),
            key_path=ssh_config.get('key_path', '~/.ssh/id_rsa'),
            connect_timeout=ssh_config.get('connect_timeout', 10),
            strict_host_key_checking=ssh_config.get('strict_host_key_checking', False),
            known_hosts_file=ssh_config.get('known_hosts_file')
        )
        
        self.ssh_manager = SSHManager(ssh_conf)
        self.remote_executor = RemoteExecutor(self.ssh_manager)
    
    def get_worker_hosts(self) -> List[tuple]:
        """获取worker主机列表"""
        ssh_config = self.get_config_section('ssh')
        workers = ssh_config.get('workers', [])
        
        if not workers:
            # 兼容旧格式
            hosts_str = self.config.get('workers_ssh_hosts', '')
            if hosts_str:
                nodes = []
                for node in hosts_str.split(','):
                    node = node.strip()
                    if ':' in node:
                        host, port = node.split(':', 1)
                        port = int(port)
                    else:
                        host = node
                        port = 22
                    nodes.append((host, port))
                return nodes
        else:
            return [(w['host'], w.get('port', 22)) for w in workers]
        
        return []
    
    def execute_on_workers(self, command: str, parallel: bool = False, 
                          timeout: int = 60) -> Dict[str, Any]:
        """在所有worker节点上执行命令"""
        if not self.ssh_manager:
            self._setup_ssh()
        
        worker_hosts = self.get_worker_hosts()
        if not worker_hosts:
            raise ConfigurationError("No worker hosts configured")
        
        return self.remote_executor.batch_execute(worker_hosts, command, parallel, timeout)


def cli_command(name: str = None, help_text: str = None, require_config: bool = True):
    """
    CLI命令装饰器
    
    Args:
        name: 命令名称
        help_text: 帮助文本
        require_config: 是否需要配置文件
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # 如果需要配置文件，验证配置存在
                if require_config:
                    config_path = Path.home() / ".sage" / "config.yaml"
                    if not config_path.exists():
                        print_status("error", f"Configuration file not found: {config_path}")
                        print_status("info", "Run 'sage config init' to create a default configuration")
                        raise typer.Exit(1)
                
                return func(*args, **kwargs)
            
            except CLIException as e:
                print_status("error", str(e))
                raise typer.Exit(e.exit_code)
            
            except Exception as e:
                print_status("error", f"Unexpected error: {e}")
                raise typer.Exit(1)
        
        # 设置命令元数据
        if name:
            wrapper.__name__ = name
        if help_text:
            wrapper.__doc__ = help_text
        
        return wrapper
    
    return decorator


def require_connection(func: Callable) -> Callable:
    """
    需要连接的命令装饰器
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 这里可以添加连接检查逻辑
        return func(*args, **kwargs)
    
    return wrapper


class JobManagerCommand(ServiceCommand):
    """JobManager命令基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = None
        self.daemon_host = None
        self.daemon_port = None
        self._setup_daemon_config()
    
    def _setup_daemon_config(self):
        """设置守护进程配置"""
        daemon_config = self.get_config_section('daemon')
        self.daemon_host = daemon_config.get('host', '127.0.0.1')
        self.daemon_port = daemon_config.get('port', 19001)
    
    def connect(self) -> bool:
        """连接到JobManager守护进程"""
        try:
            from sage.kernel import JobManagerClient
            
            self.client = JobManagerClient(self.daemon_host, self.daemon_port)
            
            # 健康检查
            health = self.client.health_check()
            if health.get("status") != "success":
                raise ConnectionError(f"Daemon health check failed: {health.get('message')}")
            
            self._connected = True
            return True
        
        except ImportError:
            raise CLIException("JobManager client not available. Please ensure SAGE is properly installed.")
        except Exception as e:
            self.formatter.print_error(f"Failed to connect to JobManager: {e}")
            self._connected = False
            return False
    
    def resolve_job_identifier(self, identifier: str) -> Optional[str]:
        """解析作业标识符（可以是作业编号或UUID）"""
        try:
            self.ensure_connected()
            
            # 获取作业列表
            response = self.client.list_jobs()
            if response.get("status") != "success":
                raise CLIException(f"Failed to get job list: {response.get('message')}")
            
            jobs = response.get("jobs", [])
            
            # 如果是数字，当作作业编号处理
            if identifier.isdigit():
                job_index = int(identifier) - 1  # 转换为0基索引
                if 0 <= job_index < len(jobs):
                    return jobs[job_index].get('uuid')
                else:
                    self.formatter.print_error(f"Job number {identifier} is out of range (1-{len(jobs)})")
                    return None
            
            # 如果是UUID（完整或部分）
            # 首先尝试精确匹配
            for job in jobs:
                if job.get('uuid') == identifier:
                    return identifier
            
            # 然后尝试前缀匹配
            matching_jobs = [job for job in jobs if job.get('uuid', '').startswith(identifier)]
            
            if len(matching_jobs) == 1:
                return matching_jobs[0].get('uuid')
            elif len(matching_jobs) > 1:
                self.formatter.print_error(f"Ambiguous job identifier '{identifier}'. Matches:")
                for i, job in enumerate(matching_jobs, 1):
                    self.formatter.print_info(f"  {i}. {job.get('uuid')} ({job.get('name', 'unknown')})")
                return None
            else:
                self.formatter.print_error(f"No job found matching '{identifier}'")
                return None
                
        except Exception as e:
            self.formatter.print_error(f"Failed to resolve job identifier: {e}")
            return None
