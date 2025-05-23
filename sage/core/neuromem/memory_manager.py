# file sage/core/neuromem/memory_manager.py
# python -m sage.core.neuromem.memory_manager

# TODO:

from typing import Any, Dict, List, Optional, Union
from sage.core.neuromem.memory_collection import (
    BaseMemoryCollection,
    VDBMemoryCollection,
    KVMemoryCollection,
    GraphMemoryCollection,
)

class MemoryManager:
    """
    内存管理器，管理不同类型的 MemoryCollection 实例。
    Memory manager for handling multiple types of memory collections.
    """
    def __init__(self):
        # 名称到 collection 实例的映射
        # Mapping from name to collection instance
        self.collections: Dict[str, BaseMemoryCollection] = {}

        # collection 元信息表：名称 -> 描述、backend_type
        # Metadata registry for collections: name -> description, backend_type
        self.collection_metadata: Dict[str, Dict[str, str]] = {}    
    
    def create_collection(
        self,
        name: str,
        backend_type: str,
        description: str = "",
        embedding_model: Optional[Any] = None,
        dim: Optional[int] = None
    ) -> BaseMemoryCollection:
        """
        创建一个新的 collection。
        Create a new collection.
        """
        if name in self.collections:
            raise ValueError(f"Collection with name '{name}' already exists.")

        if backend_type == "VDB":
            if embedding_model is None or dim is None:
                raise ValueError("VDB requires 'embedding_model' and 'dim'")
            collection = VDBMemoryCollection(name, embedding_model, dim)

        elif backend_type == "KV":
            collection = KVMemoryCollection(name)  # 假设该类已提供

        elif backend_type == "GRAPH":
            collection = GraphMemoryCollection(name)  # 假设该类已提供

        else:
            raise ValueError(f"Unsupported backend_type: {backend_type}")

        self.collections[name] = collection
        self.collection_metadata[name] = {
            "description": description,
            "backend_type": backend_type
        }
        return collection

    def delete_collection(self, name: str):
        """
        删除一个 collection。
        Delete a collection.
        """
        if name in self.collections:
            del self.collections[name]
            del self.collection_metadata[name]
        else:
            raise KeyError(f"Collection '{name}' not found.")
    
    def connect_collection(self, name: str) -> BaseMemoryCollection:
        """
        连接已存在的 collection。
        Connect to an existing collection.
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

