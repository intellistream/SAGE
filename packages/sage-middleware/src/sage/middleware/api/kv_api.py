"""
KV Service API Interface
键值存储服务的API接口定义
"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


class KVServiceAPI(ABC):
    """KV服务API接口"""
    
    @abstractmethod
    def put(self, key: str, value: Any) -> bool:
        """存储键值对"""
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除键值对"""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass
    
    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """列出所有键或指定前缀的键"""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """获取存储大小"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空所有数据"""
        pass
