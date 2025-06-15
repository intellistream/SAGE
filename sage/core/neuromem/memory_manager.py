# file sage/core/neuromem/memory_manager.py
# python -m sage.core.neuromem.memory_manager

"""
MemoryManager – 统一的 Collection 生命周期管理器

功能
----
* 磁盘扫描：启动时读取 `./memory_storage/*` 目录，收集 manifest 元数据。
* 按需加载 / 卸载：load_collection / release_collection
* 创建 / 删除：create_collection / delete_collection
* 批量保存：save_all – 将所有脏索引写盘（Text/Meta/Vec 已在 append 时实时落盘）。
* 查询与重命名：list_collection / rename

约定:仅 索引文件 和 manifest.json 需要在 `flush()` 中显式保存，其他文件实时写盘。

"""


#TODO:
#给 load_collection() 写精细化的 overload（IDE 友好）,不然返回类型不能一直是Any。

#

# collection 的 auto-save 策略？(自动flush)

# manager 的生命周期（是否需要 shutdown）？

# collection 的 update / snapshot / merge 操作 

from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sage.core.neuromem.memory_collection.base_collection import BaseMemoryCollection
from sage.core.neuromem.memory_collection.kv_collection import KVMemoryCollection
from sage.core.neuromem.memory_collection.vdb_collection import VDBMemoryCollection
from sage.core.neuromem.memory_collection.graph_collection import GraphMemoryCollection

STORAGE_ROOT = Path("./memory_storage")


class MemoryManager:
    """
内存管理器，管理不同类型的 MemoryCollection 实例。
Memory manager for handling multiple types of memory collections.
    """
    

    def __init__(self):
        self.collections: Dict[str, BaseMemoryCollection] = {}
        self.all_collection: Dict[str, Dict[str, str]] = {}
        self._scan_disk()

    def _scan_disk(self):
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        for subdir in STORAGE_ROOT.iterdir():
            if not subdir.is_dir():
                continue
            name = subdir.name
            backend_type = "VDB" if (subdir / "vec.npy").exists() else "KV"
            self.all_collection[name] = {
                "description": f"autoload from {subdir}",
                "backend_type": backend_type,
            }

    def create_collection(
        self,
        name: str,
        backend_type: str,
        description: str = "",
        embedding_model: Optional[Any] = None,
        dim: Optional[int] = None,
    ) -> Any:
        """
        创建一个新的 collection。
        Create a new collection.
        """
        if name in self.collections:
            raise ValueError(f"Collection with '{name}' already loaded.")
        if name in self.all_collection:
            raise ValueError(f"Collection with '{name}' already exists on disk.")

        if backend_type == "VDB":
            if embedding_model is None or dim is None:
                raise ValueError("VDB requires 'embedding_model' and 'dim'")
            collection = VDBMemoryCollection(name, embedding_model, dim, description=description)
        elif backend_type == "KV":
            collection = KVMemoryCollection(name, description=description)
        elif backend_type == "GRAPH":
            collection = GraphMemoryCollection(name, description=description)
        else:
            raise ValueError(f"Unsupported backend_type: {backend_type}")

        self.collections[name] = collection
        self.all_collection[name] = {
            "description": description,
            "backend_type": backend_type,
        }
        return collection

    def delete_collection(self, name: str):
        """
        删除一个 collection。
        Delete a collection.
        """
        self.release_collection(name, allow_missing=True)
        if name in self.all_collection:
            shutil.rmtree(STORAGE_ROOT / name, ignore_errors=True)
            del self.all_collection[name]
        else:
            raise KeyError(f"Collection '{name}' not found on disk.")

    def load_collection(self, name: str) -> BaseMemoryCollection:
        if name in self.collections:
            return self.collections[name]
        if name not in self.all_collection:
            raise KeyError(f"Collection '{name}' not found on disk.")

        meta = self.all_collection[name]
        backend = meta["backend_type"]
        from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder

        if backend == "VDB":
            coll = VDBMemoryCollection(name, MockTextEmbedder(fixed_dim=128), 128)
        elif backend == "KV":
            coll = KVMemoryCollection(name)
        elif backend == "GRAPH":
            coll = GraphMemoryCollection(name)
        else:
            raise ValueError(f"Unsupported backend: {backend}")

        coll.load()
        self.collections[name] = coll
        return coll

    connect_collection = load_collection

    def release_collection(self, name: str, allow_missing: bool = False):
        coll = self.collections.pop(name, None)
        if not coll:
            if allow_missing:
                return
            raise KeyError(f"Collection '{name}' not loaded.")
        coll.flush()
        coll.release()

    def save_all(self):
        for coll in self.collections.values():
            if getattr(coll, "dirty", False):
                coll.flush()

    def list_collection(self, name: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        列出一个或所有 collection 的基本信息。
        List basic info of one or all collections.
        """
        if name:
            if name not in self.all_collection:
                raise KeyError(f"Collection '{name}' not found.")
            return {"name": name, **self.all_collection[name]}
        return [
            {"name": n, **meta} for n, meta in self.all_collection.items()
        ]

    def rename(self, old: str, new: str, new_description: Optional[str] = None):
        if old not in self.collections:
            raise KeyError(f"Collection '{old}' not loaded")
        if new in self.all_collection or new in self.collections:
            raise ValueError(f"Collection '{new}' already exists")

        coll = self.collections.pop(old)
        coll.flush()
        coll.release()

        os.rename(STORAGE_ROOT / old, STORAGE_ROOT / new)
        coll.name = new
        self.collections[new] = coll

        meta = self.all_collection.pop(old)
        meta["description"] = new_description or meta["description"]
        self.all_collection[new] = meta

        