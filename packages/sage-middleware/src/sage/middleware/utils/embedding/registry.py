"""Embedding model registry for managing available embedding methods."""

import os
from typing import Dict, List, Type, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ModelStatus(Enum):
    """模型可用状态枚举"""
    AVAILABLE = "available"           # 直接可用
    NEEDS_API_KEY = "needs_api_key"   # 需要 API Key
    NEEDS_DOWNLOAD = "needs_download" # 需要下载模型
    CACHED = "cached"                 # 已缓存到本地
    UNAVAILABLE = "unavailable"       # 不可用


@dataclass
class ModelInfo:
    """模型元信息数据类
    
    Attributes:
        method: 方法名（如 'hf', 'openai', 'hash'）
        display_name: 显示名称
        description: 描述信息
        requires_api_key: 是否需要 API Key
        requires_model_download: 是否需要下载模型
        default_dimension: 默认维度（可选）
        example_models: 示例模型名称列表
        wrapper_class: Wrapper 类引用
    """
    method: str
    display_name: str
    description: str
    requires_api_key: bool
    requires_model_download: bool
    default_dimension: Optional[int]
    example_models: List[str]
    wrapper_class: Type


class EmbeddingRegistry:
    """Embedding 模型注册表
    
    管理所有可用的 embedding 方法及其元信息。
    
    Examples:
        >>> # 注册新方法
        >>> EmbeddingRegistry.register(
        ...     method="hash",
        ...     display_name="Hash Embedding",
        ...     description="轻量级哈希 embedding",
        ...     wrapper_class=HashEmbedding,
        ...     default_dimension=384,
        ... )
        >>> 
        >>> # 列出所有方法
        >>> EmbeddingRegistry.list_methods()
        ['hash', 'hf', 'openai', ...]
        >>> 
        >>> # 获取模型信息
        >>> info = EmbeddingRegistry.get_model_info("hf")
        >>> info.requires_model_download
        True
    """
    
    _registry: Dict[str, ModelInfo] = {}
    
    @classmethod
    def register(
        cls,
        method: str,
        display_name: str,
        description: str,
        wrapper_class: Type,
        requires_api_key: bool = False,
        requires_model_download: bool = False,
        default_dimension: Optional[int] = None,
        example_models: Optional[List[str]] = None,
    ) -> None:
        """注册 embedding 方法
        
        Args:
            method: 方法名称（唯一标识符）
            display_name: 显示名称
            description: 描述信息
            wrapper_class: Wrapper 类
            requires_api_key: 是否需要 API Key
            requires_model_download: 是否需要下载模型
            default_dimension: 默认维度
            example_models: 示例模型名称列表
        
        Examples:
            >>> EmbeddingRegistry.register(
            ...     method="openai",
            ...     display_name="OpenAI Embedding API",
            ...     description="OpenAI 官方或兼容 API",
            ...     wrapper_class=OpenAIEmbedding,
            ...     requires_api_key=True,
            ...     example_models=["text-embedding-3-small"],
            ... )
        """
        cls._registry[method] = ModelInfo(
            method=method,
            display_name=display_name,
            description=description,
            requires_api_key=requires_api_key,
            requires_model_download=requires_model_download,
            default_dimension=default_dimension,
            example_models=example_models or [],
            wrapper_class=wrapper_class,
        )
    
    @classmethod
    def list_methods(cls) -> List[str]:
        """列出所有已注册的方法名称
        
        Returns:
            方法名称列表（按字母顺序排序）
        
        Examples:
            >>> methods = EmbeddingRegistry.list_methods()
            >>> 'hash' in methods
            True
        """
        return sorted(cls._registry.keys())
    
    @classmethod
    def get_model_info(cls, method: str) -> Optional[ModelInfo]:
        """获取指定方法的模型信息
        
        Args:
            method: 方法名称
        
        Returns:
            ModelInfo 对象，如果方法未注册则返回 None
        
        Examples:
            >>> info = EmbeddingRegistry.get_model_info("hf")
            >>> if info:
            ...     print(info.display_name)
            HuggingFace Models
        """
        return cls._registry.get(method)
    
    @classmethod
    def check_status(cls, method: str, **kwargs: Any) -> ModelStatus:
        """检查模型可用状态
        
        Args:
            method: 方法名称
            **kwargs: 方法特定参数（如 api_key, model 等）
        
        Returns:
            ModelStatus 枚举值
        
        Examples:
            >>> # 检查 OpenAI（无 API Key）
            >>> status = EmbeddingRegistry.check_status("openai")
            >>> status == ModelStatus.NEEDS_API_KEY
            True
            >>> 
            >>> # 检查 HuggingFace 模型
            >>> status = EmbeddingRegistry.check_status(
            ...     "hf", 
            ...     model="BAAI/bge-small-zh-v1.5"
            ... )
            >>> status in [ModelStatus.CACHED, ModelStatus.NEEDS_DOWNLOAD]
            True
        """
        info = cls.get_model_info(method)
        if not info:
            return ModelStatus.UNAVAILABLE
        
        # API Key 检查
        if info.requires_api_key:
            api_key = kwargs.get("api_key")
            if not api_key:
                # 尝试从环境变量读取
                env_var_names = [
                    f"{method.upper()}_API_KEY",
                    "OPENAI_API_KEY",  # 通用 fallback
                ]
                api_key = next(
                    (os.getenv(name) for name in env_var_names if os.getenv(name)),
                    None
                )
            if not api_key:
                return ModelStatus.NEEDS_API_KEY
        
        # 本地模型缓存检查
        if info.requires_model_download:
            model_name = kwargs.get("model")
            if model_name and cls._is_model_cached(model_name):
                return ModelStatus.CACHED
            return ModelStatus.NEEDS_DOWNLOAD
        
        return ModelStatus.AVAILABLE
    
    @classmethod
    def get_wrapper_class(cls, method: str) -> Optional[Type]:
        """获取指定方法的 Wrapper 类
        
        Args:
            method: 方法名称
        
        Returns:
            Wrapper 类，如果方法未注册则返回 None
        
        Examples:
            >>> wrapper_cls = EmbeddingRegistry.get_wrapper_class("hash")
            >>> if wrapper_cls:
            ...     emb = wrapper_cls(dim=384)
        """
        info = cls.get_model_info(method)
        return info.wrapper_class if info else None
    
    @classmethod
    def _is_model_cached(cls, model_name: str) -> bool:
        """检查 HuggingFace 模型是否已缓存到本地
        
        Args:
            model_name: 模型名称（如 'BAAI/bge-small-zh-v1.5'）
        
        Returns:
            True 如果已缓存，False 否则
        """
        try:
            # HuggingFace 缓存目录
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            if not cache_dir.exists():
                return False
            
            # 模型名称转换为缓存目录格式
            # 例如: "BAAI/bge-small-zh-v1.5" -> "models--BAAI--bge-small-zh-v1.5"
            model_slug = "models--" + model_name.replace("/", "--")
            
            # 检查是否存在对应的缓存目录
            cached = any(cache_dir.glob(f"{model_slug}*"))
            return cached
        except Exception:
            # 如果检查失败，保守地返回 False
            return False
    
    @classmethod
    def clear(cls) -> None:
        """清空注册表（主要用于测试）
        
        Examples:
            >>> EmbeddingRegistry.clear()
            >>> EmbeddingRegistry.list_methods()
            []
        """
        cls._registry.clear()
