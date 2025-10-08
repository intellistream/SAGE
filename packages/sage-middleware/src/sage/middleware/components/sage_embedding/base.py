"""Base class for all embedding models."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class BaseEmbedding(ABC):
    """所有 Embedding 模型的抽象基类
    
    所有 embedding wrapper 都应继承此类并实现抽象方法。
    这确保了所有 embedding 方法提供一致的接口。
    
    Attributes:
        config: 初始化时传入的配置参数
    
    Examples:
        >>> class MyEmbedding(BaseEmbedding):
        ...     def embed(self, text: str) -> List[float]:
        ...         return [0.1, 0.2, 0.3]
        ...     
        ...     def get_dim(self) -> int:
        ...         return 3
        ...     
        ...     @property
        ...     def method_name(self) -> str:
        ...         return "my_method"
        >>> 
        >>> emb = MyEmbedding()
        >>> emb.embed("hello")
        [0.1, 0.2, 0.3]
    """
    
    def __init__(self, **kwargs: Any) -> None:
        """初始化 embedding 模型
        
        Args:
            **kwargs: 方法特定的配置参数
        """
        self.config = kwargs
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """将文本转换为 embedding 向量
        
        Args:
            text: 输入文本
        
        Returns:
            embedding 向量（浮点数列表）
        
        Raises:
            RuntimeError: 如果 embedding 失败
        """
        pass
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量将文本转换为 embedding 向量
        
        默认实现为逐个调用 embed()。子类可以重写此方法以提供更高效的批量处理。
        
        Args:
            texts: 输入文本列表
        
        Returns:
            embedding 向量列表
        
        Examples:
            >>> emb = get_embedding_model("hash")
            >>> vectors = emb.embed_batch(["hello", "world"])
            >>> len(vectors)
            2
        """
        return [self.embed(text) for text in texts]
    
    @abstractmethod
    def get_dim(self) -> int:
        """获取 embedding 向量的维度
        
        Returns:
            向量维度
        
        Examples:
            >>> emb = get_embedding_model("hash", dim=384)
            >>> emb.get_dim()
            384
        """
        pass
    
    @property
    @abstractmethod
    def method_name(self) -> str:
        """返回 embedding 方法名称
        
        Returns:
            方法名称（如 'hf', 'openai', 'hash'）
        
        Examples:
            >>> emb = get_embedding_model("hf", model="...")
            >>> emb.method_name
            'hf'
        """
        pass
    
    @classmethod
    def get_model_info(cls) -> Dict[str, Any]:
        """返回模型元信息（子类可选实现）
        
        Returns:
            包含以下键的字典:
                - method: 方法名称
                - requires_api_key: 是否需要 API Key
                - requires_model_download: 是否需要下载模型
                - default_dimension: 默认维度（可选）
        
        Examples:
            >>> HFEmbedding.get_model_info()
            {
                'method': 'hf',
                'requires_api_key': False,
                'requires_model_download': True,
                'default_dimension': None
            }
        """
        return {
            "method": cls.__name__,
            "requires_api_key": False,
            "requires_model_download": False,
            "default_dimension": None,
        }
    
    def __repr__(self) -> str:
        """返回对象的字符串表示"""
        params = ", ".join(f"{k}={v}" for k, v in list(self.config.items())[:3])
        if len(self.config) > 3:
            params += ", ..."
        return f"{self.__class__.__name__}({params})"
