"""
配置管理模块
=========

提供配置文件加载和管理功能。

模块:
----
- loader: 配置文件加载器，支持多种文件格式和查找策略
- manager: 配置管理器，提供配置的CRUD操作和缓存

Examples:
--------
>>> from sage.common.utils.config import load_config, ConfigManager
>>> 
>>> # 简单加载配置
>>> config = load_config("config.yaml")
>>> 
>>> # 使用配置管理器
>>> manager = ConfigManager("./config")
>>> config = manager.load("app.yaml")
"""

from .loader import load_config
from .manager import ConfigManager, BaseConfig, save_config

__all__ = [
    "load_config",
    "save_config",
    "ConfigManager", 
    "BaseConfig",
]
