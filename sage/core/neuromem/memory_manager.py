# file sage/core/neuromem/memory_manager.py
# python -m sage.core.neuromem.memory_manager

import os
import json
from typing import Any, Dict, List, Optional, Union
from sage.runtime.collection_wrapper import CollectionWrapper
from sage.core.neuromem.memory_collection.base_collection import BaseMemoryCollection
from sage.core.neuromem.memory_collection.vdb_collection import VDBMemoryCollection
from sage.core.neuromem.memory_collection.kv_collection import KVMemoryCollection
from sage.core.neuromem.memory_collection.graph_collection import GraphMemoryCollection

class MemoryManager:
    """
    内存管理器，管理不同类型的 MemoryCollection 实例
    所有集合自动封装为CollectionWrapper，使调用透明化
    """

    def __init__(self, data_dir: Optional[str] = None):
        # 统一使用 collections 名称存储包装后的集合
        if data_dir is None:
            # SAGE目录下 data/neuromem
            from sage.core.neuromem.memory_collection.base_collection import get_default_data_dir
            self.data_dir = get_default_data_dir()
        else:
            self.data_dir = data_dir
        self.collections: Dict[str, CollectionWrapper] = {}
        self.collection_metadata: Dict[str, Dict[str, Any]] = {}
        self.manager_path = os.path.join(self.data_dir, "manager.json")
        if os.path.exists(self.manager_path):
            self._load_manager()

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
        
    def connect_collection(self, name: str, embedding_model=None) -> CollectionWrapper:
        """
        支持外部提供 embedding_model，用于 VDB 类型 collection 的恢复。
        """
        if name in self.collections:
            return self.collections[name]
        # 只磁盘加载时需要传递 embedding_model（懒加载模型）
        if name not in self.collection_metadata:
            raise KeyError(f"Collection '{name}' metadata not found. (disk loading not implemented)")
        meta = self.collection_metadata[name]
        backend_type = meta.get("backend_type")
        if backend_type == "VDB":
            # 拼出存储路径
            vdb_path = os.path.join(self.data_dir, "vdb_collection", name)
            collection = VDBMemoryCollection.load(name, embedding_model, vdb_path)
        elif backend_type == "KV":
            kv_path = os.path.join(self.data_dir, "kv_collection", name)
            collection = KVMemoryCollection.load(name, kv_path)
        elif backend_type == "GRAPH":
            graph_path = os.path.join(self.data_dir, "graph_collection", name)
            collection = GraphMemoryCollection.load(name, graph_path)
        else:
            raise ValueError(f"Unknown backend_type: {backend_type}")
        self.collections[name] = CollectionWrapper(collection)
        return self.collections[name]



    def merge_collections(self, *names: str):
        """
        合并多个 collection（未实现）。
        Merge multiple collections (not implemented).
        """
        pass

    def store_collection(self, name: Optional[str] = None):
        """
        持久化：保存所有（或指定）collection数据，并刷新manager.json索引
        """
        all_collections = [name] if name else list(self.collections.keys())
        for cname in all_collections:
            wrapper = self.collections[cname]
            # 这里要兼容多种collection的存储函数（KV/VDB/Graph等）
            col_obj = wrapper.obj if hasattr(wrapper, "obj") else wrapper  # 兼容CollectionWrapper
            if hasattr(col_obj, "store"):
                col_obj.store(self.data_dir)
        # 存所有元信息
        with open(self.manager_path, "w", encoding="utf-8") as f:
            json.dump(self.collection_metadata, f, ensure_ascii=False, indent=2)
        print(f"Manager info saved to {self.manager_path}")
        
    def _load_manager(self):
        """
        加载manager和所有已持久化的collection
        """
        if not os.path.exists(self.manager_path):
            return
        with open(self.manager_path, "r", encoding="utf-8") as f:
            self.collection_metadata = json.load(f)
        # 只自动加载KV和GRAPH
        for name, meta in self.collection_metadata.items():
            backend_type = meta.get("backend_type")
            if backend_type == "KV":
                collection = KVMemoryCollection.load(name, self.data_dir)
            elif backend_type == "GRAPH":
                collection = GraphMemoryCollection.load(name, self.data_dir)
            # VDB 不自动加载
            else:
                continue
            self.collections[name] = CollectionWrapper(collection)

            
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

