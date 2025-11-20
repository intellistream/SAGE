"""运行时配置管理器

负责加载 YAML 配置并提供运行时参数访问接口
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


class RuntimeConfig:
    """运行时配置类
    
    功能：
    1. 加载 YAML 配置文件
    2. 接收运行时参数（如 task_id）
    3. 提供统一的参数访问接口 config.get("key")
    """

    def __init__(self, config_path: str, **runtime_params):
        """初始化运行时配置
        
        Args:
            config_path: YAML 配置文件路径
            **runtime_params: 运行时参数（如 task_id, dataset 等）
        """
        self.config_path = config_path
        self.runtime_params = runtime_params
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """加载配置文件"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            print(f"❌ 配置文件不存在: {config_file}")
            sys.exit(1)

        try:
            with open(config_file) as f:
                self._config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"❌ 配置文件格式错误: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            sys.exit(1)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持点号路径和运行时参数
        
        Args:
            key: 配置键，支持嵌套访问如 "generator.vllm.api_key"
            default: 默认值
            
        Returns:
            配置值
            
        Examples:
            config.get("dataset")  # 获取运行时参数
            config.get("generator.vllm.model_name")  # 获取 YAML 嵌套配置
            config.get("pre_insert.action")  # 获取 Operator 配置
        """
        # 优先从运行时参数中获取
        if key in self.runtime_params:
            return self.runtime_params[key]
        
        # 从 YAML 配置中获取（支持嵌套路径）
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def set_runtime_param(self, key: str, value: Any) -> None:
        """设置运行时参数
        
        Args:
            key: 参数键
            value: 参数值
        """
        self.runtime_params[key] = value

    def get_full_config(self) -> dict[str, Any]:
        """获取完整的配置字典（包含运行时参数）
        
        Returns:
            配置字典
        """
        return {**self._config, **self.runtime_params}

    @staticmethod
    def create(config_path: str, **runtime_params) -> RuntimeConfig:
        """静态方法：创建运行时配置
        
        Args:
            config_path: 配置文件路径
            **runtime_params: 运行时参数
            
        Returns:
            RuntimeConfig 实例
        """
        return RuntimeConfig(config_path, **runtime_params)

    @staticmethod
    def load(config_path: str, task_id: str | None = None) -> RuntimeConfig:
        """静态方法：加载配置（简化版）
        
        Args:
            config_path: 配置文件路径
            task_id: 任务ID（可选，命令行参数）
            
        Returns:
            RuntimeConfig 实例
            
        Raises:
            SystemExit: dataset 或 task_id 不存在时退出
        """
        config = RuntimeConfig(config_path)
        
        # 处理 task_id：命令行 > YAML > None
        if task_id:
            config.set_runtime_param("task_id", task_id)
        elif config.get("runtime.task_id"):
            config.set_runtime_param("task_id", config.get("runtime.task_id"))
        # 如果都没有，设置为 None，由 MemorySource 检查
        
        # 处理 dataset：从 YAML 读取，必须存在
        dataset = config.get("runtime.dataset")
        if not dataset:
            print("❌ 配置文件缺少 runtime.dataset 字段")
            sys.exit(1)
        config.set_runtime_param("dataset", dataset)
        
        return config

