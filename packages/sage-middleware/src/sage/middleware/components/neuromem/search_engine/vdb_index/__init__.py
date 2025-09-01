# file sage/middleware/services/neuromem/search_engine/vdb_index/__init__.py

from typing import Dict, Type, Optional, List, Any, Callable
import numpy as np
from sage.common.utils.logging.custom_logger import CustomLogger
from .base_vdb_index import BaseVDBIndex


class VDBIndexFactory:
    """
    向量数据库索引工厂类
    Vector Database Index Factory Class
    
    负责创建和管理不同类型的向量索引实例
    Responsible for creating and managing different types of vector index instances
    """
    
    # 注册的索引类型映射
    _index_registry: Dict[str, Type[BaseVDBIndex]] = {}
    
    def __init__(self):
        self.logger = CustomLogger()
        
    @classmethod
    def register_index(cls, index_type: str, index_class: Type[BaseVDBIndex]):
        """
        注册新的索引类型
        Register a new index type
        
        Args:
            index_type: 索引类型名称，如 "FAISS", "CHROMA", "PINECONE" 等
            index_class: 索引类的类型，必须继承自 BaseVDBIndex
        """
        if not issubclass(index_class, BaseVDBIndex):
            raise TypeError(f"Index class {index_class} must inherit from BaseVDBIndex")
        
        cls._index_registry[index_type.upper()] = index_class
        
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """
        获取所有支持的索引类型
        Get all supported index types
        """
        return list(cls._index_registry.keys())
    
    def create_index(
        self,
        index_name: str,
        dim: int,
        backend_type: str = "FAISS",
        config: Optional[Dict[str, Any]] = None,
        vectors: Optional[List[np.ndarray]] = None,
        ids: Optional[List[str]] = None,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **kwargs
    ) -> BaseVDBIndex:
        """
        创建指定类型的向量索引
        Create a vector index of the specified type
        
        Args:
            index_name: 索引名称
            dim: 向量维度
            backend_type: 后端类型，如 "FAISS", "CHROMA" 等
            config: 索引配置参数
            vectors: 初始向量列表
            ids: 初始向量对应的ID列表
            metadata_filter_func: 元数据过滤函数
            **kwargs: 其他传递给索引构造函数的参数
            
        Returns:
            创建的索引实例
            
        Raises:
            ValueError: 当指定的索引类型不支持时
            TypeError: 当参数类型不正确时
        """
        backend_type = backend_type.upper()
        
        if backend_type not in self._index_registry:
            supported_types = ", ".join(self.get_supported_types())
            raise ValueError(
                f"Unsupported index type: {backend_type}. "
                f"Supported types: {supported_types}"
            )
        
        # 准备配置参数
        if config is None:
            config = {}
        
        # 确保配置中包含必要的参数
        config.update({
            "name": index_name,
            "dim": dim,
            **kwargs
        })
        
        # 验证向量和ID的数量匹配
        if vectors is not None and ids is not None:
            if len(vectors) != len(ids):
                raise ValueError("The number of vectors must match the number of IDs")
        
        try:
            index_class = self._index_registry[backend_type]
            
            # 创建索引实例
            if backend_type == "FAISS":
                # 对于FAISS索引，使用新的config-only构造方式
                index = index_class(config=config)
                
                # 如果提供了初始数据，批量插入
                if vectors is not None and ids is not None:
                    if hasattr(index, 'batch_insert'):
                        index.batch_insert(vectors, ids)
                    else:
                        # 如果没有batch_insert方法，逐个插入
                        for vector, vector_id in zip(vectors, ids):
                            index.insert(vector, vector_id)
            else:
                # 对于其他类型的索引，使用通用的构造方式
                index = index_class(
                    name=index_name,
                    dim=dim,
                    config=config,
                    vectors=vectors,
                    ids=ids,
                    **kwargs
                )
            
            self.logger.info(f"Successfully created {backend_type} index: {index_name}")
            return index
            
        except Exception as e:
            self.logger.error(f"Failed to create {backend_type} index {index_name}: {str(e)}")
            raise
    
    def create_index_from_config(
        self,
        config: Dict[str, Any],
        vectors: Optional[List[np.ndarray]] = None,
        ids: Optional[List[str]] = None,
        **kwargs
    ) -> BaseVDBIndex:
        """
        直接从配置字典创建索引（简化的接口）
        Create index directly from config dictionary (simplified interface)
        
        Args:
            config: 完整的配置字典，必须包含 name, dim, backend_type 等字段
            vectors: 初始向量列表
            ids: 初始向量对应的ID列表
            **kwargs: 其他传递给索引构造函数的参数
            
        Returns:
            创建的索引实例
            
        Raises:
            ValueError: 当配置缺少必要字段时
        """
        # 检查必要的配置字段
        required_fields = ["name", "dim"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"配置中缺少必要字段: {field}")
        
        index_name = config["name"]
        dim = config["dim"]
        backend_type = config.get("backend_type", "FAISS")
        
        return self.create_index(
            index_name=index_name,
            dim=dim,
            backend_type=backend_type,
            config=config,
            vectors=vectors,
            ids=ids,
            **kwargs
        )
    
    def load_index(
        self,
        index_name: str,
        backend_type: str,
        load_path: str
    ) -> BaseVDBIndex:
        """
        从磁盘加载索引
        Load index from disk
        
        Args:
            index_name: 索引名称
            backend_type: 后端类型
            load_path: 加载路径
            
        Returns:
            加载的索引实例
        """
        backend_type = backend_type.upper()
        
        if backend_type not in self._index_registry:
            supported_types = ", ".join(self.get_supported_types())
            raise ValueError(
                f"Unsupported index type: {backend_type}. "
                f"Supported types: {supported_types}"
            )
        
        try:
            index_class = self._index_registry[backend_type]
            index = index_class.load(index_name, load_path)
            
            self.logger.info(f"Successfully loaded {backend_type} index: {index_name}")
            return index
            
        except Exception as e:
            self.logger.error(f"Failed to load {backend_type} index {index_name}: {str(e)}")
            raise


# 全局工厂实例
index_factory = VDBIndexFactory()


def register_index_type(index_type: str, index_class: Type[BaseVDBIndex]):
    """
    便捷函数：注册新的索引类型
    Convenience function: register a new index type
    """
    VDBIndexFactory.register_index(index_type, index_class)


def create_index(
    index_name: str,
    dim: int,
    backend_type: str = "FAISS",
    config: Optional[Dict[str, Any]] = None,
    vectors: Optional[List[np.ndarray]] = None,
    ids: Optional[List[str]] = None,
    **kwargs
) -> BaseVDBIndex:
    """
    便捷函数：创建索引
    Convenience function: create index
    """
    return index_factory.create_index(
        index_name=index_name,
        dim=dim,
        backend_type=backend_type,
        config=config,
        vectors=vectors,
        ids=ids,
        **kwargs
    )


def create_index_from_config(
    config: Dict[str, Any],
    vectors: Optional[List[np.ndarray]] = None,
    ids: Optional[List[str]] = None,
    **kwargs
) -> BaseVDBIndex:
    """
    便捷函数：直接从配置字典创建索引
    Convenience function: create index directly from config dictionary
    """
    return index_factory.create_index_from_config(
        config=config,
        vectors=vectors,
        ids=ids,
        **kwargs
    )


def load_index(index_name: str, backend_type: str, load_path: str) -> BaseVDBIndex:
    """
    便捷函数：加载索引
    Convenience function: load index
    """
    return index_factory.load_index(index_name, backend_type, load_path)


def get_supported_index_types() -> List[str]:
    """
    便捷函数：获取支持的索引类型
    Convenience function: get supported index types
    """
    return VDBIndexFactory.get_supported_types()


# 自动注册已知的索引类型
def _auto_register_indexes():
    """自动注册已知的索引类型"""
    try:
        from .faiss_index import FaissIndex
        register_index_type("FAISS", FaissIndex)
    except ImportError:
        pass
    
    # 未来可以在这里添加其他索引类型的自动注册
    # try:
    #     from .chroma_index import ChromaIndex
    #     register_index_type("CHROMA", ChromaIndex)
    # except ImportError:
    #     pass


# 执行自动注册
_auto_register_indexes()


# 导出公共接口
__all__ = [
    "VDBIndexFactory",
    "BaseVDBIndex",
    "index_factory",
    "register_index_type",
    "create_index",
    "create_index_from_config",
    "load_index",
    "get_supported_index_types"
]
