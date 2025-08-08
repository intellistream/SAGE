"""
VDB Service API Interface
向量数据库服务的API接口定义
"""
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod


class VDBServiceAPI(ABC):
    """VDB服务API接口"""
    
    @abstractmethod
    def add_vectors(self, documents: List[Dict[str, Any]]) -> List[str]:
        """添加向量文档"""
        pass
    
    @abstractmethod
    def search(
        self, 
        query_vector: List[float], 
        top_k: int = 10,
        similarity_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """向量相似性搜索"""
        pass
    
    @abstractmethod
    def get_vector(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取向量文档"""
        pass
    
    @abstractmethod
    def delete_vectors(self, doc_ids: List[str]) -> bool:
        """删除向量文档"""
        pass
    
    @abstractmethod
    def update_vector(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """更新向量文档"""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """获取向量总数"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空所有向量"""
        pass
    
    @abstractmethod
    def save_index(self, path: str) -> bool:
        """保存索引到磁盘"""
        pass
    
    @abstractmethod
    def load_index(self, path: str) -> bool:
        """从磁盘加载索引"""
        pass
