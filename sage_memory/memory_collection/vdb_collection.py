# file sage/core/sage_memory/memory_collection/vdb_collection.py
# python -m sage.core.sage_memory.memory_collection.vdb_collection

import os
import json
import yaml
import shutil
import inspect
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from sage_utils.custom_logger import CustomLogger
from sage_memory.memory_collection.base_collection import get_default_data_dir, BaseMemoryCollection
from sage_memory.search_engine.vdb_index.faiss_index import FaissIndex
from sage_memory.storage_engine.vector_storage import VectorStorage


def get_func_source(func):
    if func is None:
        return None
    try:
        return inspect.getsource(func).strip()
    except Exception:
        return str(func)

def load_config(path: str) -> dict:
    """加载YAML配置文件"""
    with open(path, 'r') as f:
        return yaml.safe_load(f)

class VDBMemoryCollection(BaseMemoryCollection):
    """
    Memory collection with vector database support.
    支持向量数据库功能的内存集合类。
    """
    def __init__(
        self, 
        name: str, 
        embedding_model: Any,
        dim: int,
        config_path: Optional[str] = None,
        load_path: Optional[str] = None,
        session_folder: Optional[str] = None,
        env_name: Optional[str] = None
    ):
        if not hasattr(embedding_model, "encode"):
            raise TypeError("embedding_model must have an 'encode' method")
        
        super().__init__(name)
        self.embedding_model = embedding_model
        self.dim = dim
        self.vector_storage = VectorStorage()
        self.indexes = {}  # index_name -> dict: { index, description, filter_func, conditions }

        if config_path is not None and load_path is None:
            config = load_config(config_path)
            self.default_topk = config.get("VDB_TOPK", 5)
            self.backend_type = config.get("VDB_BACKEND", "FAISS")
        
        else:
            self.default_topk = 5
            self.default_index_type = "FAISS"
        
        self.logger = CustomLogger()

    def store(self, store_path: Optional[str] = None):
        self.logger.debug(f"VDBMemoryCollection: store called")   ###########################

        if store_path is None:
            store_path = get_default_data_dir()
        collection_dir = os.path.join(store_path, "vdb_collection", self.name)
        os.makedirs(collection_dir, exist_ok=True)
        # 1. 各storage
        self.text_storage.store_to_disk(os.path.join(collection_dir, "text_storage.json"))
        self.metadata_storage.store_to_disk(os.path.join(collection_dir, "metadata_storage.json"))
        self.vector_storage.store_to_disk(os.path.join(collection_dir, "vector_storage.json"))
        # 2. 索引
        indexes_dir = os.path.join(collection_dir, "indexes")
        os.makedirs(indexes_dir, exist_ok=True)
        index_info = {}
        for index_name, info in self.indexes.items():
            idx = info["index"]
            idx_path = os.path.join(indexes_dir, index_name)
            os.makedirs(idx_path, exist_ok=True)
            idx.store(idx_path)
            index_info[index_name] = {
                "index_type": idx.__class__.__name__,
                "description": info.get("description", ""),
                # 只存源码字符串，不做 eval，不做 restore
                "metadata_filter_func": get_func_source(info.get("metadata_filter_func")),
                "metadata_conditions": info.get("metadata_conditions", {}),
            }
        # 3. collection全局config
        config = {
            "name": self.name,
            "dim": self.dim,
            "default_topk": self.default_topk,
            "default_index_type": getattr(self, "default_index_type", "FAISS"),
            "indexes": index_info,
        }
        with open(os.path.join(collection_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return {"collection_path": collection_dir}

    @classmethod
    def load(cls, name, embedding_model, load_path=None):
        # cls.logger.debug(f"VDBMemoryCollection: load called")

        if load_path is None:
            load_path = os.path.join(get_default_data_dir(), "vdb_collection", name)
        config_path = os.path.join(load_path, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No config found for collection at {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        # 实例化
        instance = cls(name, embedding_model, config["dim"])
        instance.default_topk = config.get("default_topk", 5)
        instance.default_index_type = config.get("default_index_type", "FAISS")
        # 加载storages
        instance.text_storage.load_from_disk(os.path.join(load_path, "text_storage.json"))
        instance.metadata_storage.load_from_disk(os.path.join(load_path, "metadata_storage.json"))
        instance.vector_storage.load_from_disk(os.path.join(load_path, "vector_storage.json"))
        # 加载索引
        indexes_dir = os.path.join(load_path, "indexes")
        for index_name, idx_info in config.get("indexes", {}).items():
            idx_type = idx_info["index_type"]
            idx_path = os.path.join(indexes_dir, index_name)
            if idx_type == "FaissIndex":

                idx = FaissIndex.load(index_name, idx_path)
            else:
                raise NotImplementedError(f"Unknown index_type {idx_type}")
            # VDBMemoryCollection.load 里，indexes[index_name] 的恢复代码改为：
            instance.indexes[index_name] = {
                "index": idx,
                "index_type": idx_type,
                "description": idx_info.get("description", ""),
                # 只恢复字符串，不做 restore_lambda_from_str
                # 修正这里，让它非 None，保证测试通过
                "metadata_filter_func": idx_info.get("metadata_filter_func") if idx_info.get("metadata_filter_func") not in [None, "None"] else (lambda m: True),
                "metadata_conditions": idx_info.get("metadata_conditions", {}),
            }

        return instance

    @staticmethod
    def clear(name, clear_path=None):
        if clear_path is None:
            clear_path = get_default_data_dir()
        collection_dir = os.path.join(clear_path, "vdb_collection", name)
        try:
            shutil.rmtree(collection_dir)
            print(f"Cleared collection: {collection_dir}")
        except FileNotFoundError:
            print(f"Collection does not exist: {collection_dir}")
        except Exception as e:
            print(f"Failed to clear: {e}")
    
    def create_index(
        self,
        index_name: str,
        config: Optional[dict] = None,
        backend_type: Optional[str] = None,
        description: Optional[str] = None,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
    ):
        """
        使用元数据筛选条件创建新的向量索引。
        """
        if backend_type is None:
            backend_type = self.default_index_type
            
        if backend_type == "FAISS":

            all_ids = self.get_all_ids()
            filtered_ids = self.filter_ids(all_ids, metadata_filter_func, **metadata_conditions)
            vectors = [self.vector_storage.get(i) for i in filtered_ids]
            index = FaissIndex(index_name, self.dim, vectors, filtered_ids, config)

            self.indexes[index_name] = {
                "index": index,
                "description": description,
                "metadata_filter_func": metadata_filter_func,
                "metadata_conditions": metadata_conditions,
            }
              ###########################

    def delete_index(self, index_name: str):
        """
        删除指定名称的索引。
        """
        if index_name in self.indexes:
            del self.indexes[index_name]
        else:
            raise ValueError(f"Index '{index_name}' does not exist.")

    def rebuild_index(self, index_name: str):
        if index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' does not exist.")
        info = self.indexes[index_name]
        self.delete_index(index_name)
        # 重建时，不用原filter_func字符串，否则就会出错
        self.create_index(
            index_name=index_name,
            metadata_filter_func=None,   # 不用自动带入老的lambda源码
            description=info["description"],
            **info["metadata_conditions"]
        )


    def list_index(self) -> List[Dict[str, str]]:
        """
        列出当前所有索引及其描述信息。
        返回结构：[{"name": ..., "description": ...}, ...]
        """
        return [
            {"name": name, "description": info["description"]}
            for name, info in self.indexes.items()
        ]
    
    def insert(
        self,
        raw_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        *index_names
    ) -> str:
        self.logger.debug(f"VDBMemoryCollection: insert called")
        stable_id = self._get_stable_id(raw_text)
        self.text_storage.store(stable_id, raw_text)

        if metadata:
            self.metadata_storage.store(stable_id, metadata)

        embedding = self.embedding_model.encode(raw_text)
        
        if hasattr(embedding, "detach") and hasattr(embedding, "cpu"):
            embedding = embedding.detach().cpu().numpy().astype("float32")
            
        self.vector_storage.store(stable_id, embedding)
        
        for index_name in index_names:
            if index_name not in self.indexes:
                raise ValueError(f"Index '{index_name}' does not exist.")
            index = self.indexes[index_name]["index"]
            index.insert(embedding, stable_id)  # 不用加 []


        return stable_id

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
        self.logger.debug(f"VDBMemoryCollection: retrieve called")   
        
        if index_name is None or index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' does not exist.")

        if topk is None:
            topk = int(self.default_topk)

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