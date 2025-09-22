#!/usr/bin/env python3
"""
SAGE Configuration Manager
统一的配置文件管理
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import typer

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            # 统一使用家目录下的配置文件以维护一致性
            self.config_path = Path.home() / ".sage" / "config.yaml"
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            return self._config
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}")
    
    def save_config(self, config: Dict[str, Any]):
        """保存配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            self._config = config
        except Exception as e:
            raise RuntimeError(f"保存配置文件失败: {e}")
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def get_head_config(self) -> Dict[str, Any]:
        """获取head节点配置"""
        return self.config.get('head', {})
    
    def get_worker_config(self) -> Dict[str, Any]:
        """获取worker配置"""
        return self.config.get('worker', {})
    
    def get_ssh_config(self) -> Dict[str, Any]:
        """获取SSH配置"""
        return self.config.get('ssh', {})
    
    def get_remote_config(self) -> Dict[str, Any]:
        """获取远程路径配置"""
        return self.config.get('remote', {})
    
    def get_workers_ssh_hosts(self) -> List[Tuple[str, int]]:
        """解析worker SSH主机列表"""
        # 先从ssh.workers中读取
        ssh_config = self.get_ssh_config()
        workers = ssh_config.get('workers', [])
        
        if workers:
            return [(w['host'], w.get('port', 22)) for w in workers]
        
        # 兼容旧的workers_ssh_hosts格式
        hosts_str = self.config.get('workers_ssh_hosts', '')
        if not hosts_str:
            return []
        
        # 检查是否为列表格式（新格式测试）
        if isinstance(hosts_str, list):
            return [(item['host'], item.get('port', 22)) for item in hosts_str]
        
        nodes = []
        for node in hosts_str.split(','):
            node = node.strip()
            if ':' in node:
                host, port = node.split(':', 1)
                port = int(port)
            else:
                host = node
                port = 22  # 默认SSH端口
            nodes.append((host, port))
        return nodes
    
    def add_worker_ssh_host(self, host: str, port: int = 22):
        """添加新的worker SSH主机"""
        current_hosts = self.get_workers_ssh_hosts()
        new_host = (host, port)
        
        # 检查是否已存在
        if new_host in current_hosts:
            return False
        
        current_hosts.append(new_host)
        hosts_str = ','.join([f"{h}:{p}" for h, p in current_hosts])
        
        config = self.config.copy()
        config['workers_ssh_hosts'] = hosts_str
        self.save_config(config)
        return True
    
    def remove_worker_ssh_host(self, host: str, port: int = 22):
        """移除worker SSH主机"""
        current_hosts = self.get_workers_ssh_hosts()
        target_host = (host, port)
        
        if target_host not in current_hosts:
            return False
        
        current_hosts.remove(target_host)
        hosts_str = ','.join([f"{h}:{p}" for h, p in current_hosts])
        
        config = self.config.copy()
        config['workers_ssh_hosts'] = hosts_str
        self.save_config(config)
        return True
    
    def create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            'head': {
                'host': 'base-sage', # 需要自动捕获头节点ip 
                'head_port': 6379,
                'dashboard_port': 8265,
                'dashboard_host': '0.0.0.0',
                'temp_dir': '/var/tmp/ray',
                'log_dir': '/var/tmp/sage_head_logs',  
                'conda_env': 'sage_lj',
                'python_path': '/home/sage/.conda/envs/sage_lj/bin/python',
                'ray_command': '/home/sage/.conda/envs/sage_lj/bin/ray',   
                'sage_home': '/home/sage',

            },
            'worker': {
                'bind_host': 'localhost',
                'temp_dir': '/tmp/ray_worker',
                'log_dir': '/tmp/sage_worker_logs'
            },
            'workers_ssh_hosts': '',
            'ssh': {
                'user': 'sage',
                'key_path': '~/.ssh/id_rsa',
                'connect_timeout': 10
            },
            'remote': {
                'sage_home': '/home/sage',
                'python_path': '/opt/conda/envs/sage/bin/python',
                'ray_command': '/opt/conda/envs/sage/bin/ray',
                'conda_env': 'sage'
            },
            'daemon': {
                'host': 'base-sage', # 需要改成头节点ip
                'port': 19001
            },
            'output': {
                'format': 'table',
                'colors': True
            },
            'monitor': {
                'refresh_interval': 5
            },
            'jobmanager': {
                'timeout': 30,
                'retry_attempts': 3
            }
        }
        
        self.save_config(default_config)
        return default_config


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager(config_path)


# Typer应用
app = typer.Typer(help="SAGE configuration management")

@app.command()
def show(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path")
):
    """显示当前配置"""
    config_manager = get_config_manager(config_path)
    try:
        config = config_manager.load_config()
        print("当前配置:")
        import pprint
        pprint.pprint(config)
    except FileNotFoundError:
        print("配置文件不存在，请先创建配置")

@app.command()
def create(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path")
):
    """创建默认配置"""
    config_manager = get_config_manager(config_path)
    config_manager.create_default_config()
    print(f"默认配置已创建: {config_manager.config_path}")

@app.command()
def set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path")
):
    """设置配置值"""
    config_manager = get_config_manager(config_path)
    try:
        config = config_manager.load_config()
        # Simple dot notation support for nested keys
        keys = key.split('.')
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        config_manager.save_config(config)
        print(f"配置已更新: {key} = {value}")
    except FileNotFoundError:
        print("配置文件不存在，请先创建配置")

if __name__ == "__main__":
    app()
