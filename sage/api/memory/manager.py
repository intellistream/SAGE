# sage/api/memory/manager.py
"""
API layer MemoryManager
代理 sage.core.neuromem.memory_manager.MemoryManager，
避免 application 直接依赖 core，实现分层解耦。
"""
import os
import json
from typing import Any, Dict, List, Optional, Union

from sage.core.neuromem.memory_manager import MemoryManager as _CoreMemoryManager
from sage.core.runtime.collection_wrapper import CollectionWrapper


class MemoryManager:
    """
    API 层 MemoryManager，管理不同类型的 MemoryCollection 实例。
    内部使用 core.neuromem.memory_manager.MemoryManager 完成具体逻辑。
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化 MemoryManager。
        :param data_dir: 数据存储路径，默认为 core 默认目录。
        """
        self._inner = _CoreMemoryManager(data_dir)

    def create_collection(
        self,
        name: str,
        backend_type: str,
        embedding_model: Optional[Any] = None,
        dim: Optional[int] = None,
        description: str = "",
        as_ray_actor: bool = False
    ) -> CollectionWrapper:
        """
        创建新的 collection 并返回 CollectionWrapper。
        :param name: collection 名称
        :param backend_type: 存储类型，如 VDB, KV, GRAPH
        :param embedding_model: 嵌入模型，仅 VDB 时必需
        :param dim: 向量维度，仅 VDB 时必需
        :param description: 描述信息
        :param as_ray_actor: 是否以 Ray Actor 方式封装
        """
        return self._inner.create_collection(
            name=name,
            backend_type=backend_type,
            embedding_model=embedding_model,
            dim=dim,
            description=description,
            as_ray_actor=as_ray_actor
        )

    def get_collection(self, name: str) -> CollectionWrapper:
        """
        获取已创建的 collection。
        :param name: collection 名称
        """
        return self._inner.get_collection(name)

    def delete_collection(self, name: str) -> None:
        """
        删除指定 collection。
        :param name: collection 名称
        """
        self._inner.delete_collection(name)

    def connect_collection(
        self,
        name: str,
        embedding_model: Optional[Any] = None
    ) -> CollectionWrapper:
        """
        从持久化中加载并连接 collection。
        :param name: collection 名称
        :param embedding_model: 嵌入模型，仅 VDB 恢复时必需
        """
        return self._inner.connect_collection(name, embedding_model)

    def list_collection(
        self,
        name: Optional[str] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        列出一个或所有 collection 的元信息。
        :param name: 可选，单个 collection 名称
        """
        return self._inner.list_collection(name)

    def rename_collection(
        self,
        former_name: str,
        new_name: str,
        new_description: Optional[str] = None
    ) -> None:
        """
        重命名 collection 并更新描述。
        :param former_name: 旧名称
        :param new_name: 新名称
        :param new_description: 可选新描述
        """
        self._inner.rename(former_name, new_name, new_description)

    def store_collection(self, name: Optional[str] = None) -> None:
        """
        持久化指定或所有 collections，并更新 manager.json。
        :param name: 可选，单个 collection 名称
        """
        self._inner.store_collection(name)

    def merge_collections(self, *names: str) -> None:
        """
        合并多个 collections（如有需要，可实现）。
        :param names: 要合并的 collection 名称列表
        """
        return self._inner.merge_collections(*names)
