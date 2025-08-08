"""
配置管理模块
============

提供统一的配置加载、保存和管理功能。
支持YAML、JSON、TOML等多种格式。
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Union, Optional
from pydantic import BaseModel, ValidationError

__all__ = ["load_config", "save_config", "ConfigManager", "BaseConfig"]


class BaseConfig(BaseModel):
    """基础配置类"""
    
    class Config:
        extra = "allow"  # 允许额外字段
        validate_assignment = True  # 验证赋值


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认使用当前目录的config/
        """
        if config_dir is None:
            config_dir = Path.cwd() / "config"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def load(self, filename: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            filename: 配置文件名
            use_cache: 是否使用缓存
            
        Returns:
            配置字典
        """
        if use_cache and filename in self._cache:
            return self._cache[filename].copy()
        
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件未找到: {config_path}")
        
        # 根据扩展名选择解析器
        suffix = config_path.suffix.lower()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
            elif suffix == '.json':
                config = json.load(f)
            elif suffix == '.toml':
                try:
                    import tomli
                    content = f.read()
                    config = tomli.loads(content)
                except ImportError:
                    raise ImportError("需要安装 tomli 库来支持 TOML 格式")
            else:
                raise ValueError(f"不支持的配置文件格式: {suffix}")
        
        if config is None:
            config = {}
        
        # 缓存配置
        if use_cache:
            self._cache[filename] = config.copy()
        
        return config
    
    def save(self, filename: str, config: Dict[str, Any], format: Optional[str] = None):
        """
        保存配置文件
        
        Args:
            filename: 配置文件名
            config: 配置字典
            format: 强制指定格式 (yaml, json, toml)
        """
        config_path = self.config_dir / filename
        
        # 确定保存格式
        if format:
            save_format = format.lower()
        else:
            suffix = config_path.suffix.lower()
            if suffix in ['.yaml', '.yml']:
                save_format = 'yaml'
            elif suffix == '.json':
                save_format = 'json'
            elif suffix == '.toml':
                save_format = 'toml'
            else:
                save_format = 'yaml'  # 默认使用YAML
        
        # 保存文件
        if save_format == 'toml':
            try:
                import tomli_w
                with open(config_path, 'wb') as f:
                    tomli_w.dump(config, f)
            except ImportError:
                raise ImportError("需要安装 tomli-w 库来保存 TOML 格式")
        else:
            with open(config_path, 'w', encoding='utf-8') as f:
                if save_format == 'yaml':
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                elif save_format == 'json':
                    json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 更新缓存
        self._cache[filename] = config.copy()
    
    def get(self, filename: str, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            filename: 配置文件名
            key: 配置键，支持点分割的嵌套键 (如 'database.host')
            default: 默认值
            
        Returns:
            配置值
        """
        config = self.load(filename)
        
        # 处理嵌套键
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, filename: str, key: str, value: Any):
        """
        设置配置项
        
        Args:
            filename: 配置文件名  
            key: 配置键，支持点分割的嵌套键
            value: 配置值
        """
        config = self.load(filename) if filename in self._cache or (self.config_dir / filename).exists() else {}
        
        # 处理嵌套键
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        
        # 保存配置
        self.save(filename, config)
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


# 全局配置管理器实例
_global_config_manager = ConfigManager()


def load_config(filename: str, config_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    加载配置文件 (便捷函数)
    
    Args:
        filename: 配置文件名
        config_dir: 配置目录，如果提供则创建新的ConfigManager实例
        
    Returns:
        配置字典
    """
    if config_dir is not None:
        manager = ConfigManager(config_dir)
        return manager.load(filename)
    
    return _global_config_manager.load(filename)


def save_config(filename: str, config: Dict[str, Any], config_dir: Optional[Union[str, Path]] = None):
    """
    保存配置文件 (便捷函数)
    
    Args:
        filename: 配置文件名
        config: 配置字典
        config_dir: 配置目录，如果提供则创建新的ConfigManager实例
    """
    if config_dir is not None:
        manager = ConfigManager(config_dir)
        manager.save(filename, config)
    else:
        _global_config_manager.save(filename, config)
