# file sage/core/neuromem/memory_manager.py
# python -m sage.core.neuromem.memory_manager

from typing import Any, Dict, List, Optional, Union
from sage.runtime.collection_wrapper import CollectionWrapper
from sage.core.neuromem.memory_collection.base_collection import (
    BaseMemoryCollection,
    VDBMemoryCollection,
    KVMemoryCollection,
    GraphMemoryCollection,
)


class MemoryManager:
    """
    内存管理器，管理不同类型的 MemoryCollection 实例
    所有集合自动封装为CollectionWrapper，使调用透明化
    """

    def __init__(self):
        # 统一使用 collections 名称存储包装后的集合
        self.collections: Dict[str, CollectionWrapper] = {}
        self.collection_metadata: Dict[str, Dict[str, any]] = {}

    def create_collection(
            self,
            name: str,
            backend_type: str,
            description: str = "",
            embedding_model: Optional[Any] = None,
            dim: Optional[int] = None,
            as_ray_actor: bool = False
    ) -> CollectionWrapper:
        """
        创建新的集合（可选择作为Ray Actor封装）
        始终返回CollectionWrapper对象
        """
        if name in self.collections:
            raise ValueError(f"Collection with name '{name}' already exists.")

        # 创建基础集合
        if backend_type == "VDB":
            if embedding_model is None or dim is None:
                raise ValueError("VDB requires 'embedding_model' and 'dim'")
            collection = VDBMemoryCollection(name, embedding_model, dim)
        elif backend_type == "KV":
            collection = KVMemoryCollection(name)
        elif backend_type == "GRAPH":
            collection = GraphMemoryCollection(name)
        else:
            raise ValueError(f"Unsupported backend_type: {backend_type}")

        if as_ray_actor:
            # 尝试导入Ray
            try:
                import ray
                # 创建Ray Actor
                actor_cls = ray.remote(type(collection))
                # 根据类型处理不同构造参数
                if backend_type == "VDB":
                    ray_actor = actor_cls.remote(name, embedding_model, dim)
                else:
                    ray_actor = actor_cls.remote(name)

                # 封装Ray Actor
                wrapped_collection = CollectionWrapper(ray_actor)
            except ImportError:
                # Ray不可用，回退到本地
                print("Ray not available, falling back to local collection")
                as_ray_actor = False
                wrapped_collection = CollectionWrapper(collection)
        else:
            # 封装本地集合
            wrapped_collection = CollectionWrapper(collection)

        # 存储到 collections
        self.collections[name] = wrapped_collection
        self.collection_metadata[name] = {
            "description": description,
            "backend_type": backend_type,
            "is_ray_actor": as_ray_actor
        }
        return wrapped_collection

    def get_collection(self, name: str) -> CollectionWrapper:
        """获取已封装的集合"""
        if name in self.collections:
            return self.collections[name]
        raise KeyError(f"Collection {name} not found")

    def delete_collection(self, name: str):
        """
        删除一个 collection。
        """
        if name in self.collections:
            del self.collections[name]
        if name in self.collection_metadata:
            del self.collection_metadata[name]
        else:
            raise KeyError(f"Collection '{name}' not found.")
    def connect_collection(self, name: str) -> CollectionWrapper:
        """
        连接已存在的 collection（未实现）。
        Connect to an existing collection(not implemented).
        1. 加载已经被创建的 collection(在内存里了)  2. 加载离弦的 collection(disk) ==> 数据结构(manager创建时，会到某个路径去读取文件，collection_name信息)
        """
        if name not in self.collections:
            raise KeyError(f"Collection '{name}' not found. (disk loading not implemented)")
        return self.collections[name]

    def merge_collections(self, *names: str):
        """
        合并多个 collection（未实现）。
        Merge multiple collections (not implemented).
        """
        pass

    def store_collection(self, name: str):
        """
        存储 collection 到磁盘（未实现）。
        Store a collection to disk (not implemented).
        """
        pass

    def list_collection(self, name: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        列出一个或所有 collection 的基本信息。
        List basic info of one or all collections.
        """
        if name:
            if name not in self.collection_metadata:
                raise KeyError(f"Collection '{name}' not found.")
            return {"name": name, **self.collection_metadata[name]}
        else:
            return [
                {"name": n, **meta}
                for n, meta in self.collection_metadata.items()
            ]

    def rename(self, former_name: str, new_name: str, new_description: Optional[str] = None):
        """
        重命名 collection 并更新描述（可选）。
        Rename a collection and update description (optional).
        """
        if former_name not in self.collections:
            raise KeyError(f"Collection '{former_name}' not found.")
        if new_name in self.collections:
            raise ValueError(f"Collection '{new_name}' already exists.")

        collection = self.collections.pop(former_name)
        collection.name = new_name
        self.collections[new_name] = collection

        metadata = self.collection_metadata.pop(former_name)
        metadata["description"] = new_description or metadata.get("description", "")
        self.collection_metadata[new_name] = metadata

