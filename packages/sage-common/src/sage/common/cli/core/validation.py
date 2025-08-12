#!/usr/bin/env python3
"""
SAGE CLI Validation
===================

输入验证和数据校验功能
"""

import re
import socket
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
from urllib.parse import urlparse

from .exceptions import ValidationError


def validate_host(host: str) -> str:
    """
    验证主机地址
    
    Args:
        host: 主机地址
        
    Returns:
        验证通过的主机地址
        
    Raises:
        ValidationError: 主机地址格式错误
    """
    if not host or not isinstance(host, str):
        raise ValidationError("Host cannot be empty")
    
    host = host.strip()
    
    # 检查是否为有效的IP地址
    try:
        socket.inet_pton(socket.AF_INET, host)
        return host
    except socket.error:
        pass
    
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return host
    except socket.error:
        pass
    
    # 检查是否为有效的主机名
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$', host):
        # 允许localhost和简单主机名
        if host not in ['localhost'] and not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$', host) and not re.match(r'^[a-zA-Z0-9]+$', host):
            raise ValidationError(f"Invalid host address: {host}")
    
    return host


def validate_port(port: Union[int, str]) -> int:
    """
    验证端口号
    
    Args:
        port: 端口号
        
    Returns:
        验证通过的端口号
        
    Raises:
        ValidationError: 端口号无效
    """
    try:
        port = int(port)
    except (ValueError, TypeError):
        raise ValidationError(f"Port must be a number: {port}")
    
    if not (1 <= port <= 65535):
        raise ValidationError(f"Port must be between 1 and 65535: {port}")
    
    return port


def validate_path(path: Union[str, Path], must_exist: bool = False, 
                 must_be_file: bool = False, must_be_dir: bool = False,
                 create_if_missing: bool = False) -> Path:
    """
    验证文件路径
    
    Args:
        path: 文件路径
        must_exist: 路径必须存在
        must_be_file: 必须是文件
        must_be_dir: 必须是目录
        create_if_missing: 如果不存在则创建
        
    Returns:
        验证通过的路径对象
        
    Raises:
        ValidationError: 路径验证失败
    """
    if not path:
        raise ValidationError("Path cannot be empty")
    
    path = Path(path)
    
    # 处理波浪号
    if str(path).startswith('~'):
        path = path.expanduser()
    
    # 转换为绝对路径
    path = path.resolve()
    
    if must_exist and not path.exists():
        if create_if_missing:
            if must_be_dir:
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
        else:
            raise ValidationError(f"Path does not exist: {path}")
    
    if path.exists():
        if must_be_file and not path.is_file():
            raise ValidationError(f"Path is not a file: {path}")
        
        if must_be_dir and not path.is_dir():
            raise ValidationError(f"Path is not a directory: {path}")
    
    return path


def validate_url(url: str) -> str:
    """
    验证URL格式
    
    Args:
        url: URL字符串
        
    Returns:
        验证通过的URL
        
    Raises:
        ValidationError: URL格式错误
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL cannot be empty")
    
    url = url.strip()
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(f"Invalid URL format: {url}")
        return url
    except Exception as e:
        raise ValidationError(f"Invalid URL: {url}, error: {e}")


def validate_email(email: str) -> str:
    """
    验证邮箱地址
    
    Args:
        email: 邮箱地址
        
    Returns:
        验证通过的邮箱地址
        
    Raises:
        ValidationError: 邮箱格式错误
    """
    if not email or not isinstance(email, str):
        raise ValidationError("Email cannot be empty")
    
    email = email.strip()
    
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    if not email_pattern.match(email):
        raise ValidationError(f"Invalid email format: {email}")
    
    return email


def validate_uuid(uuid_str: str, allow_partial: bool = False) -> str:
    """
    验证UUID格式
    
    Args:
        uuid_str: UUID字符串
        allow_partial: 是否允许部分UUID（用于前缀匹配）
        
    Returns:
        验证通过的UUID字符串
        
    Raises:
        ValidationError: UUID格式错误
    """
    if not uuid_str or not isinstance(uuid_str, str):
        raise ValidationError("UUID cannot be empty")
    
    uuid_str = uuid_str.strip()
    
    if allow_partial:
        # 允许部分UUID，但至少要有8个字符
        if len(uuid_str) < 8:
            raise ValidationError("Partial UUID must be at least 8 characters")
        # 检查是否只包含有效的十六进制字符和连字符
        if not re.match(r'^[0-9a-f-]+$', uuid_str.lower()):
            raise ValidationError(f"Invalid UUID format: {uuid_str}")
    else:
        # 完整UUID格式验证
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(uuid_str):
            raise ValidationError(f"Invalid UUID format: {uuid_str}")
    
    return uuid_str


def validate_env_name(name: str) -> str:
    """
    验证环境变量名
    
    Args:
        name: 环境变量名
        
    Returns:
        验证通过的环境变量名
        
    Raises:
        ValidationError: 环境变量名格式错误
    """
    if not name or not isinstance(name, str):
        raise ValidationError("Environment variable name cannot be empty")
    
    name = name.strip()
    
    # 环境变量名应该只包含字母、数字和下划线，且不能以数字开头
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValidationError(f"Invalid environment variable name: {name}")
    
    return name


def validate_service_name(name: str) -> str:
    """
    验证服务名
    
    Args:
        name: 服务名
        
    Returns:
        验证通过的服务名
        
    Raises:
        ValidationError: 服务名格式错误
    """
    if not name or not isinstance(name, str):
        raise ValidationError("Service name cannot be empty")
    
    name = name.strip()
    
    # 服务名应该只包含字母、数字、连字符和下划线
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValidationError(f"Invalid service name: {name}")
    
    if len(name) > 63:
        raise ValidationError(f"Service name too long (max 63 characters): {name}")
    
    return name


def validate_config_dict(config: Dict[str, Any], required_keys: List[str] = None,
                        valid_keys: List[str] = None) -> Dict[str, Any]:
    """
    验证配置字典
    
    Args:
        config: 配置字典
        required_keys: 必需的键列表
        valid_keys: 有效的键列表
        
    Returns:
        验证通过的配置字典
        
    Raises:
        ValidationError: 配置验证失败
    """
    if not isinstance(config, dict):
        raise ValidationError("Config must be a dictionary")
    
    if required_keys:
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValidationError(f"Missing required config keys: {missing_keys}")
    
    if valid_keys:
        invalid_keys = [key for key in config.keys() if key not in valid_keys]
        if invalid_keys:
            raise ValidationError(f"Invalid config keys: {invalid_keys}")
    
    return config


def validate_timeout(timeout: Union[int, str, float]) -> int:
    """
    验证超时值
    
    Args:
        timeout: 超时值（秒）
        
    Returns:
        验证通过的超时值
        
    Raises:
        ValidationError: 超时值无效
    """
    try:
        timeout = int(timeout)
    except (ValueError, TypeError):
        raise ValidationError(f"Timeout must be a number: {timeout}")
    
    if timeout <= 0:
        raise ValidationError(f"Timeout must be positive: {timeout}")
    
    if timeout > 3600:  # 最大1小时
        raise ValidationError(f"Timeout too large (max 3600 seconds): {timeout}")
    
    return timeout


def validate_log_level(level: str) -> str:
    """
    验证日志级别
    
    Args:
        level: 日志级别
        
    Returns:
        验证通过的日志级别
        
    Raises:
        ValidationError: 日志级别无效
    """
    if not level or not isinstance(level, str):
        raise ValidationError("Log level cannot be empty")
    
    level = level.strip().upper()
    
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if level not in valid_levels:
        raise ValidationError(f"Invalid log level: {level}, must be one of {valid_levels}")
    
    return level


def validate_memory_size(size: str) -> str:
    """
    验证内存大小格式
    
    Args:
        size: 内存大小字符串，如 "1G", "512M", "2048MB"
        
    Returns:
        验证通过的内存大小字符串
        
    Raises:
        ValidationError: 内存大小格式错误
    """
    if not size or not isinstance(size, str):
        raise ValidationError("Memory size cannot be empty")
    
    size = size.strip()
    
    # 匹配内存大小格式
    pattern = re.compile(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?|[kmgt]?b?)$', re.IGNORECASE)
    match = pattern.match(size)
    
    if not match:
        raise ValidationError(f"Invalid memory size format: {size}")
    
    number, unit = match.groups()
    
    try:
        float(number)  # 验证数字部分
    except ValueError:
        raise ValidationError(f"Invalid number in memory size: {number}")
    
    return size
