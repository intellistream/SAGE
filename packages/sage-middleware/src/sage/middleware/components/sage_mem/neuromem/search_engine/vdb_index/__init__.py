# file sage/middleware/services/neuromem/search_engine/vdb_index/__init__.py

from typing import Any, Dict, Type  # noqa: F401

from .base_vdb_index import BaseVDBIndex


class VDBIndexFactory:
    """向量数据库索引工厂类 - 简化版本"""

    # 注册的索引类型映射
    _index_registry: Dict[str, Type[BaseVDBIndex]] = {}

    @classmethod
    def register_index(cls, index_type: str, index_class: Type[BaseVDBIndex]):
        """注册新的索引类型"""
        if not issubclass(index_class, BaseVDBIndex):
            raise TypeError(f"Index class {index_class} must inherit from BaseVDBIndex")
        cls._index_registry[index_type.upper()] = index_class

    def create_index(self, config: Dict[str, Any]) -> BaseVDBIndex:
        """
        创建索引 - 简化版本，只支持config方式创建

        Args:
            config: 配置字典，必须包含 name, dim, backend_type

        Returns:
            创建的索引实例
        """
        # 检查必要字段
        required_fields = ["name", "dim"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"配置中缺少必要字段: {field}")

        backend_type = config.get("backend_type", "FAISS").upper()

        if backend_type not in self._index_registry:
            raise ValueError(f"不支持的索引类型: {backend_type}")

        index_class = self._index_registry[backend_type]
        return index_class(config=config)


# 全局工厂实例
index_factory = VDBIndexFactory()


def register_index_type(index_type: str, index_class: Type[BaseVDBIndex]):
    """注册新的索引类型"""
    VDBIndexFactory.register_index(index_type, index_class)


def create_index(config: Dict[str, Any]) -> BaseVDBIndex:
    """创建索引"""
    return index_factory.create_index(config)


# 自动注册FAISS索引
def _auto_register_indexes():
    """自动注册已知的索引类型"""
    try:
        from .faiss_index import FaissIndex

        register_index_type("FAISS", FaissIndex)
    except ImportError:
        pass


# 执行自动注册
_auto_register_indexes()


# 导出公共接口
__all__ = [
    "VDBIndexFactory",
    "BaseVDBIndex",
    "index_factory",
    "register_index_type",
    "create_index",
]
