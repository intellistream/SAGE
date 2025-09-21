# file sage/middleware/services/neuromem/search_engine/kv_index/__init__.py

from typing import Any, Dict, List, Optional

from .base_kv_index import BaseKVIndex
from .bm25s_index import BM25sIndex


class KVIndexFactory:
    """
    键值索引工厂类，用于创建和加载不同类型的索引
    Key-Value Index Factory for creating and loading different types of indexes
    """

    # 支持的索引类型映射
    _index_registry = {
        "bm25s": BM25sIndex,
    }

    @classmethod
    def create_index(
        cls,
        index_type: str,
        index_name: str,
        texts: List[str],
        ids: List[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseKVIndex:
        """
        创建指定类型的索引实例
        Create an index instance of the specified type

        Args:
            index_type: 索引类型，如 "bm25s"
            index_name: 索引名称
            texts: 文本列表
            ids: ID列表
            config: 额外配置参数

        Returns:
            BaseKVIndex: 创建的索引实例

        Raises:
            ValueError: 当索引类型不支持时
        """
        if index_type not in cls._index_registry:
            supported_types = list(cls._index_registry.keys())
            raise ValueError(
                f"Index type '{index_type}' not supported. Supported types: {supported_types}"
            )

        # 准备配置
        index_config = config or {}
        index_config["name"] = index_name

        # 获取索引类并创建实例
        index_class = cls._index_registry[index_type]
        index = index_class(config=index_config)

        # 构建索引
        if texts and ids:
            index.build_index(texts, ids)

        return index

    @classmethod
    def load_index(cls, index_type: str, index_name: str, dir_path: str) -> BaseKVIndex:
        """
        从磁盘加载指定类型的索引实例
        Load an index instance of the specified type from disk

        Args:
            index_type: 索引类型，如 "bm25s"
            index_name: 索引名称
            dir_path: 索引存储目录路径

        Returns:
            BaseKVIndex: 加载的索引实例

        Raises:
            ValueError: 当索引类型不支持时
        """
        if index_type not in cls._index_registry:
            supported_types = list(cls._index_registry.keys())
            raise ValueError(
                f"Index type '{index_type}' not supported. Supported types: {supported_types}"
            )

        # 获取索引类并加载实例
        index_class = cls._index_registry[index_type]
        return index_class.load(index_name, dir_path)

    @classmethod
    def get_supported_types(cls) -> List[str]:
        """
        获取所有支持的索引类型
        Get all supported index types

        Returns:
            List[str]: 支持的索引类型列表
        """
        return list(cls._index_registry.keys())

    @classmethod
    def register_index_type(cls, index_type: str, index_class: type):
        """
        注册新的索引类型
        Register a new index type

        Args:
            index_type: 索引类型名称
            index_class: 索引类
        """
        if not issubclass(index_class, BaseKVIndex):
            raise ValueError(f"Index class must be a subclass of BaseKVIndex")

        cls._index_registry[index_type] = index_class

    @classmethod
    def is_supported(cls, index_type: str) -> bool:
        """
        检查是否支持指定的索引类型
        Check if the specified index type is supported

        Args:
            index_type: 索引类型

        Returns:
            bool: 是否支持
        """
        return index_type in cls._index_registry


# 导出主要类和工厂
__all__ = ["BaseKVIndex", "BM25sIndex", "KVIndexFactory"]
