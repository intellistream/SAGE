# file: sage/core/neuromem/memory_collection/vdb_collection.py
# python -m sage.core.neuromem.memory_collection.vdb_collection

import os
import hashlib
import numpy as np
from dotenv import load_dotenv
from typing import Dict, Optional, Callable, Any, List
from pathlib import Path
import json
import datetime

from sage.core.neuromem.storage_engine.text_storage import TextStorage
from sage.core.neuromem.storage_engine.metadata_storage import MetadataStorage
from sage.core.neuromem.storage_engine.vector_storage import VectorStorage

from sage.core.neuromem.storage_engine.storage_engine_locked import (
    MetadataStorageLocked,
    TextStorageLocked,
    VectorStorageLocked
    )

from sage.core.neuromem.memory_collection.base_collection import BaseMemoryCollection

#TODO:
# 让 VDBMemoryCollection.load() 自动挂载索引（重要）

# 加载工程根目录下 sage/.env 配置
# Load configuration from .env file under the sage directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../.env'))

def get_stable_id(text: str) -> str:
    """
    生成稳定的唯一ID，基于文本内容的SHA256哈希。
    Generate a stable unique ID based on the SHA256 hash of the text content.
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

class VDBMemoryCollection(BaseMemoryCollection):
    """
    Memory collection with vector database support.
    支持向量数据库功能的内存集合类。
    """
    def __init__(self, 
                 name: str, 
                 embedding_model: Any, 
                 dim: int,
                 storage_root: str = "./memory_storage",
                 description: str = ""
                 )-> None:
        
        if not hasattr(embedding_model, "encode"):
            raise TypeError("embedding_model must have an 'encode' method")
        
        super().__init__(name)
        self.embedding_model = embedding_model
        self.dim = dim
        self.description = description or ""

        self.dirty = False  # 是否需要保存
        self.is_loaded = False  # 是否已加载
        self._root = Path(storage_root) / name
        self._root.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self._root / "manifest.json"
        self.text_storage = TextStorageLocked(self._root / "text.jsonl")
        self.metadata_storage = MetadataStorageLocked(self._root / "metadata.jsonl")
        self.vector_storage = VectorStorageLocked(
            Path(self._root) / "vec.npy", Path(self._root) / "vec_ids.jsonl", dim
        )


        self.default_topk = int(os.getenv("VDB_TOPK", 3))
        self.backend_type = os.getenv("VDB_BACKEND", "FAISS")
        self.indexes = {}  # index_name -> dict: { index, index_description, filter_func, conditions }
        

    def create_index(
        self,
        index_name: str,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        index_description: str = "",
        **metadata_conditions
    ):
        """
        使用元数据筛选条件创建新的向量索引。
        """
        if self.backend_type == "FAISS":
            from sage.core.neuromem.search_engine.vdb_index.faiss_index import FaissBackend

            all_ids = self.get_all_ids()
            filtered_ids = self.filter_ids(all_ids, metadata_filter_func, **metadata_conditions)

            self.vector_storage.load()  # 确保向量存储已加载

            vectors = [self.vector_storage.get(i) for i in filtered_ids]
            index = FaissBackend(index_name, self.dim, vectors, filtered_ids)

            self.indexes[index_name] = {
                "index": index,
                "index_description": index_description,
                "metadata_filter_func": metadata_filter_func,
                "metadata_conditions": metadata_conditions,
            }

    def delete_index(self, index_name: str):
        """
        删除指定名称的索引。
        """
        if index_name in self.indexes:
            del self.indexes[index_name]
        else:
            raise ValueError(f"Index '{index_name}' does not exist.")

    def rebuild_index(self, index_name: str):
        """
        使用原始创建条件重建指定索引。
        """
        if index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' does not exist.")
        
        info = self.indexes[index_name]
        self.delete_index(index_name)  # 删除旧索引以避免冲突
        self.create_index(
            index_name=index_name,
            metadata_filter_func=info["metadata_filter_func"],
            index_description=info["index_description"],
            **info["metadata_conditions"]
        )

    def list_index(self) -> List[Dict[str, str]]:
        """
        列出当前所有索引及其描述信息。
        返回结构：[{"name": ..., "index_description": ...}, ...]
        """
        return [
            {"name": name, "index_description": info["index_description"]}
            for name, info in self.indexes.items()
        ]
    
    def insert(self, raw_text: str, metadata: Optional[Dict[str, Any]] = None, *index_names: str) -> str:
        item_id = self._get_stable_id(raw_text)
        self.text_storage.append(item_id, raw_text)
        if metadata:
            self.metadata_storage.append(item_id, metadata)

        embedding = self.embedding_model.encode(raw_text)
        if hasattr(embedding, "detach") and hasattr(embedding, "cpu"):
            embedding = embedding.detach().cpu().numpy().astype("float32")
        self.vector_storage.append(item_id, embedding)

        for idx_name in index_names:
            if idx_name not in self.indexes:
                raise ValueError(f"Index '{idx_name}' not found")
            self.indexes[idx_name]["index"].insert(embedding, item_id)
        self.stats["count"] += 1
        self.stats["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
        self.dirty = True
        return item_id
        

    def update(
        self,
        former_text: str,
        new_text: str,
        new_metadata: Optional[Dict[str, Any]] = None,
        *index_names: str
    ) -> str:
        old_id = self._get_stable_id(former_text)
        if not self.text_storage.has(old_id):
            raise ValueError("Original text not found.")

        self.text_storage.delete(old_id)
        self.metadata_storage.delete(old_id)
        self.vector_storage.delete(old_id)

        for index in self.indexes.values():
            index["index"].delete(old_id)

        return self.insert(new_text, new_metadata, *index_names)

    def delete(self, raw_text: str):
        stable_id = self._get_stable_id(raw_text)
        self.text_storage.delete(stable_id)
        self.metadata_storage.delete(stable_id)
        self.vector_storage.delete(stable_id)

        for index in self.indexes.values():
            index["index"].delete(stable_id)

    def retrieve(
        self,
        raw_text: str,
        topk: Optional[int] = None,
        index_name: Optional[str] = None,
        with_metadata: bool = False,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
    ) :
        if index_name is None or index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' does not exist.")

        if topk is None:
            topk = self.default_topk

        query_embedding = self.embedding_model.encode(raw_text)

        if hasattr(query_embedding, "detach") and hasattr(query_embedding, "cpu"):
            query_embedding = query_embedding.detach().cpu().numpy()
        elif isinstance(query_embedding, list):
            # 处理 Python 列表
            query_embedding = np.array(query_embedding, dtype=np.float32)
        sub_index = self.indexes[index_name]["index"]
        top_k_ids, _ = sub_index.search(query_embedding, topk=topk)

        if top_k_ids and isinstance(top_k_ids[0], (list, np.ndarray)):
            top_k_ids = top_k_ids[0]
        top_k_ids = [str(i) for i in top_k_ids]

        filtered_ids = self.filter_ids(top_k_ids, metadata_filter_func, **metadata_conditions)

        # 检查是否返回数量不足，自动重建索引并重试
        if len(filtered_ids) < topk:
            self.rebuild_index(index_name)
            sub_index = self.indexes[index_name]["index"]
            top_k_ids, _ = sub_index.search(query_embedding, topk=topk * 2)
            if top_k_ids and isinstance(top_k_ids[0], (list, np.ndarray)):
                top_k_ids = top_k_ids[0]
            top_k_ids = [str(i) for i in top_k_ids]
            filtered_ids = self.filter_ids(top_k_ids, metadata_filter_func, **metadata_conditions)
            filtered_ids = filtered_ids[:topk]

        if with_metadata:
            return [{"text": self.text_storage.get(i), "metadata": self.metadata_storage.get(i)}for i in filtered_ids]
        else:
            return [self.text_storage.get(i) for i in filtered_ids]
        
    def flush(self):
        if not self.dirty:
            return
         # 1) 持久化所有 faiss 索引到 {index_name}.index
        for name, info in self.indexes.items():
            try:
                path = self._root / f"{name}.index"
                info["index"].write_index(str(path))
            except Exception:
                pass  # 可根据需要输出日志       
        self.save_manifest()

    

    def save_manifest(self):
        """
        为 VDBMemoryCollection 保存 manifest.json 文件。
        """
        manifest = {
            "name": self.name,
            "backend_type": self.backend_type,
            "embedding": {
                "model": self.embedding_model.__class__.__name__,
                "dim": self.dim
            },
            "files": {
                "text": "text.jsonl",
                "metadata": "meta.jsonl",
                "vector": "vec.npy",
                "vector_ids": "vec_ids.jsonl",
                "index": {n: f"{n}.index" for n in self.indexes.keys()},
            },
            "description": self.description,
            "stats": {
                "count": self.stats.get("count", 0),
                "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
            },
            "schema_ver": 2  # 明确区分 VDB 版本
        }

        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        self.dirty = False

