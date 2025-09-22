#!/usr/bin/env python3
"""
SAGE CLI Config Validation
==========================

配置文件验证和处理功能
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from .exceptions import ConfigurationError, ValidationError
from .validation import (
    validate_host, validate_port, validate_path, validate_config_dict,
    validate_timeout, validate_log_level
)
from .utils import load_yaml_file, save_yaml_file


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.required_sections = []
        self.optional_sections = []
        self.section_validators = {}
    
    def add_required_section(self, section_name: str, validator_func=None):
        """添加必需的配置节"""
        self.required_sections.append(section_name)
        if validator_func:
            self.section_validators[section_name] = validator_func
    
    def add_optional_section(self, section_name: str, validator_func=None):
        """添加可选的配置节"""
        self.optional_sections.append(section_name)
        if validator_func:
            self.section_validators[section_name] = validator_func
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证配置字典
        
        Args:
            config: 配置字典
            
        Returns:
            验证并标准化后的配置
            
        Raises:
            ConfigurationError: 配置验证失败
        """
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        # 检查必需节
        missing_sections = [s for s in self.required_sections if s not in config]
        if missing_sections:
            raise ConfigurationError(f"Missing required configuration sections: {missing_sections}")
        
        # 验证各个节
        validated_config = {}
        for section_name, section_data in config.items():
            if section_name in self.section_validators:
                try:
                    validated_config[section_name] = self.section_validators[section_name](section_data)
                except Exception as e:
                    raise ConfigurationError(f"Invalid configuration in section '{section_name}': {e}")
            else:
                validated_config[section_name] = section_data
        
        return validated_config


def validate_head_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证head节点配置"""
    required_keys = ['host', 'head_port', 'dashboard_port']
    config = validate_config_dict(config, required_keys)
    
    # 验证具体字段
    config['host'] = validate_host(config['host'])
    config['head_port'] = validate_port(config['head_port'])
    config['dashboard_port'] = validate_port(config['dashboard_port'])
    
    # 可选字段验证
    if 'dashboard_host' in config:
        config['dashboard_host'] = validate_host(config['dashboard_host'])
    
    if 'temp_dir' in config:
        config['temp_dir'] = str(validate_path(config['temp_dir']))
    
    if 'log_dir' in config:
        config['log_dir'] = str(validate_path(config['log_dir']))
    
    if 'python_path' in config:
        config['python_path'] = str(validate_path(config['python_path'], must_exist=True, must_be_file=True))
    
    if 'ray_command' in config:
        config['ray_command'] = str(validate_path(config['ray_command'], must_exist=True, must_be_file=True))
    
    return config


def validate_worker_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证worker节点配置"""
    # worker配置都是可选的
    if 'bind_host' in config:
        config['bind_host'] = validate_host(config['bind_host'])
    
    if 'temp_dir' in config:
        config['temp_dir'] = str(validate_path(config['temp_dir']))
    
    if 'log_dir' in config:
        config['log_dir'] = str(validate_path(config['log_dir']))
    
    return config


def validate_ssh_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证SSH配置"""
    required_keys = ['user']
    config = validate_config_dict(config, required_keys)
    
    if 'key_path' in config:
        key_path = config['key_path']
        if key_path.startswith('~'):
            key_path = os.path.expanduser(key_path)
        config['key_path'] = str(validate_path(key_path, must_exist=True, must_be_file=True))
    
    if 'connect_timeout' in config:
        config['connect_timeout'] = validate_timeout(config['connect_timeout'])
    
    # 验证workers配置
    if 'workers' in config:
        workers = config['workers']
        if not isinstance(workers, list):
            raise ValidationError("SSH workers must be a list")
        
        for i, worker in enumerate(workers):
            if not isinstance(worker, dict):
                raise ValidationError(f"SSH worker {i} must be a dictionary")
            
            if 'host' not in worker:
                raise ValidationError(f"SSH worker {i} missing required 'host' field")
            
            worker['host'] = validate_host(worker['host'])
            
            if 'port' in worker:
                worker['port'] = validate_port(worker['port'])
            else:
                worker['port'] = 22  # 默认SSH端口
    
    return config


def validate_remote_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证远程配置"""
    if 'sage_home' in config:
        # 远程路径不能在本地验证存在性，只检查格式
        config['sage_home'] = str(Path(config['sage_home']))
    
    if 'python_path' in config:
        config['python_path'] = str(Path(config['python_path']))
    
    if 'ray_command' in config:
        config['ray_command'] = str(Path(config['ray_command']))
    
    return config


def validate_daemon_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证守护进程配置"""
    required_keys = ['host', 'port']
    config = validate_config_dict(config, required_keys)
    
    config['host'] = validate_host(config['host'])
    config['port'] = validate_port(config['port'])
    
    return config


def validate_output_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证输出配置"""
    valid_formats = ['table', 'json', 'yaml']
    
    if 'format' in config:
        if config['format'] not in valid_formats:
            raise ValidationError(f"Invalid output format: {config['format']}, must be one of {valid_formats}")
    
    if 'colors' in config:
        if not isinstance(config['colors'], bool):
            raise ValidationError("Output colors setting must be boolean")
    
    return config


def validate_monitor_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证监控配置"""
    if 'refresh_interval' in config:
        interval = config['refresh_interval']
        if not isinstance(interval, (int, float)) or interval <= 0:
            raise ValidationError("Monitor refresh_interval must be a positive number")
        config['refresh_interval'] = float(interval)
    
    return config


def validate_jobmanager_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证JobManager配置"""
    if 'timeout' in config:
        config['timeout'] = validate_timeout(config['timeout'])
    
    if 'retry_attempts' in config:
        attempts = config['retry_attempts']
        if not isinstance(attempts, int) or attempts < 0:
            raise ValidationError("JobManager retry_attempts must be a non-negative integer")
        config['retry_attempts'] = attempts
    
    return config


def create_default_config_validator() -> ConfigValidator:
    """创建默认的配置验证器"""
    validator = ConfigValidator()
    
    # 添加必需节
    validator.add_required_section('head', validate_head_config)
    validator.add_required_section('ssh', validate_ssh_config)
    validator.add_required_section('daemon', validate_daemon_config)
    
    # 添加可选节
    validator.add_optional_section('worker', validate_worker_config)
    validator.add_optional_section('remote', validate_remote_config)
    validator.add_optional_section('output', validate_output_config)
    validator.add_optional_section('monitor', validate_monitor_config)
    validator.add_optional_section('jobmanager', validate_jobmanager_config)
    
    return validator


def load_and_validate_config(config_path: Union[str, Path], 
                           validator: Optional[ConfigValidator] = None) -> Dict[str, Any]:
    """
    加载并验证配置文件
    
    Args:
        config_path: 配置文件路径
        validator: 配置验证器，如果为None则使用默认验证器
        
    Returns:
        验证后的配置字典
        
    Raises:
        ConfigurationError: 配置加载或验证失败
    """
    if validator is None:
        validator = create_default_config_validator()
    
    try:
        config = load_yaml_file(config_path)
        return validator.validate_config(config)
    except Exception as e:
        raise ConfigurationError(f"Failed to load and validate config file {config_path}: {e}")


def create_default_config() -> Dict[str, Any]:
    """创建默认配置"""
    return {
        'head': {
            'host': 'localhost',
            'head_port': 6379,
            'dashboard_port': 8265,
            'dashboard_host': '0.0.0.0',
            'temp_dir': '/tmp/ray',
            'log_dir': '/tmp/sage_logs',
        },
        'worker': {
            'bind_host': 'localhost',
            'temp_dir': '/tmp/ray_worker',
            'log_dir': '/tmp/sage_worker_logs'
        },
        'ssh': {
            'user': os.getenv('USER', 'sage'),
            'key_path': '~/.ssh/id_rsa',
            'connect_timeout': 10,
            'workers': []
        },
        'remote': {
            'sage_home': '/opt/sage',
            'python_path': '/opt/conda/bin/python',
            'ray_command': '/opt/conda/bin/ray'
        },
        'daemon': {
            'host': 'localhost',
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
