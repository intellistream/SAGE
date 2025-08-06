"""
Memory Service API Interface
记忆服务的API接口定义
"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


class MemoryServiceAPI(ABC):
    """Memory服务API接口 - 高级记忆管理"""
    
    @abstractmethod
    def store_memory(
        self,
        content: str,
        vector: List[float],
        session_id: Optional[str] = None,
        memory_type: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """存储记忆"""
        pass
    
    @abstractmethod
    def retrieve_memories(
        self,
        query_vector: List[float],
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        pass
    
    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取特定记忆"""
        pass
    
    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def search_memories(
        self,
        query: str,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """基于文本搜索记忆"""
        pass
    
    @abstractmethod
    def get_session_memories(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的所有记忆"""
        pass
    
    @abstractmethod
    def clear_session_memories(self, session_id: str) -> bool:
        """清空会话记忆"""
        pass
