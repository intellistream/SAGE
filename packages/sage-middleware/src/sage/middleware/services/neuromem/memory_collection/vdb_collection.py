# file sage/service/memory/memory_collection/vdb_collection.py
# python -m sage.middleware.services.neuromem.memory_collection.vdb_collection

import os
import json
import yaml
import shutil
import inspect
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.middleware.services.neuromem.memory_collection.base_collection import BaseMemoryCollection
from sage.middleware.services.neuromem.search_engine.vdb_index.faiss_index import FaissIndex
from sage.middleware.services.neuromem.storage_engine.vector_storage import VectorStorage
from sage.middleware.services.neuromem.utils.path_utils import get_default_data_dir

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
        self.logger.debug(f"VDBMemoryCollection: store called")

        if store_path is None:
            # 使用默认数据目录
            base_dir = get_default_data_dir()
        else:
            # 使用传入的数据目录（通常来自MemoryManager）
            base_dir = store_path
            
        collection_dir = os.path.join(base_dir, "vdb_collection", self.name)
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
            # 如果没有指定路径，使用默认路径结构
            base_dir = get_default_data_dir()
            load_path = os.path.join(base_dir, "vdb_collection", name)
        
        # 此时 load_path 应该是指向具体collection的完整路径
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
            # 自动注册所有未知的元数据字段
            for field_name in metadata.keys():
                if not self.metadata_storage.has_field(field_name):
                    self.metadata_storage.add_field(field_name)
            self.metadata_storage.store(stable_id, metadata)

        embedding = self.embedding_model.encode(raw_text)
        
        # 统一处理不同格式的embedding结果
        if hasattr(embedding, "detach") and hasattr(embedding, "cpu"):
            # PyTorch tensor
            embedding = embedding.detach().cpu().numpy()
        if isinstance(embedding, list):
            # Python list
            embedding = np.array(embedding)
        if not isinstance(embedding, np.ndarray):
            # 其他类型，尝试转换为numpy数组
            embedding = np.array(embedding)
            
        # 确保数据类型是float32
        embedding = embedding.astype(np.float32)
            
        self.vector_storage.store(stable_id, embedding)
        
        # 确保数据被添加到指定的索引和全局索引中
        index_names_set = set(index_names)
        
        # 如果存在全局索引，且不在指定的索引列表中，添加到全局索引
        if "global_index" in self.indexes and "global_index" not in index_names_set:
            index_names_set.add("global_index")
        elif "global_index" not in self.indexes and not index_names_set:
            # 如果没有全局索引且没有指定其他索引，创建全局索引
            self.logger.info(f"Creating global index: global_index")
            self.create_index("global_index")
            index_names_set.add("global_index")
            
        # 添加到所有需要的索引中
        for index_name in index_names_set:
            if index_name not in self.indexes:
                if index_name == "global_index":
                    # 如果是全局索引不存在，创建它
                    self.logger.info(f"Creating global index: {index_name}")
                    self.create_index(index_name)
                else:
                    raise ValueError(f"Index '{index_name}' does not exist.")
            
            index = self.indexes[index_name]["index"]
            index.insert(embedding, stable_id)

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
        
        # 如果没有指定索引，使用或创建全局索引
        if index_name is None:
            index_name = "global_index"
            if index_name not in self.indexes:
                self.logger.info(f"Creating global index: {index_name}")
                # 创建全局索引时，需要考虑元数据过滤条件
                self.create_index(index_name, metadata_filter_func=metadata_filter_func, **metadata_conditions)

        if index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' does not exist.")

        if topk is None:
            topk = int(self.default_topk)

        query_embedding = self.embedding_model.encode(raw_text)

        # 统一处理不同格式的embedding结果
        if hasattr(query_embedding, "detach") and hasattr(query_embedding, "cpu"):
            # PyTorch tensor
            query_embedding = query_embedding.detach().cpu().numpy()
        if isinstance(query_embedding, list):
            # Python list
            query_embedding = np.array(query_embedding)
        if not isinstance(query_embedding, np.ndarray):
            # 其他类型，尝试转换为numpy数组
            query_embedding = np.array(query_embedding)
            
        # 确保数据类型是float32
        query_embedding = query_embedding.astype(np.float32)
            
        sub_index = self.indexes[index_name]["index"]
        # 增加检索数量以补偿过滤后可能的损失
        search_topk = topk * 2  # 检索更多结果以确保过滤后有足够的结果
        top_k_ids, _ = sub_index.search(query_embedding, topk=search_topk)

        if top_k_ids and isinstance(top_k_ids[0], (list, np.ndarray)):
            top_k_ids = top_k_ids[0]
        top_k_ids = [str(i) for i in top_k_ids]

        # 应用元数据过滤
        if metadata_filter_func or metadata_conditions:
            filtered_ids = self.filter_ids(top_k_ids, metadata_filter_func, **metadata_conditions)
        else:
            filtered_ids = top_k_ids

        # 截取需要的数量
        filtered_ids = filtered_ids[:topk]

        # 如果过滤后的结果数量小于请求的topk，记录warning
        if len(filtered_ids) < topk:
            self.logger.warning(f"Retrieved results ({len(filtered_ids)}) are less than requested top-k ({topk})")

        if with_metadata:
            return [{"text": self.text_storage.get(i), "metadata": self.metadata_storage.get(i)} for i in filtered_ids]
        else:
            return [self.text_storage.get(i) for i in filtered_ids]

if __name__ == "__main__":
    import torch
    from transformers import AutoTokenizer, AutoModel
    import shutil
    import tempfile

    def colored(text, color):
        colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "reset": "\033[0m"}
        return colors.get(color, "") + str(text) + colors["reset"]

    class MockEmbeddingModel:
        def encode(self, text):
            # 模拟embedding，将文本长度作为特征
            return torch.tensor([float(len(text))] * 4)  # 4维向量

    def run_test():
        print(colored("\n=== 开始VDBMemoryCollection测试 ===", "yellow"))
        
        # 准备测试环境
        test_name = "test_collection"
        test_dir = tempfile.mkdtemp()
        embedding_model = MockEmbeddingModel()
        dim = 4

        try:
            # 1. 初始化测试
            print(colored("\n1. 测试初始化", "yellow"))
            collection = VDBMemoryCollection(test_name, embedding_model, dim)
            print(colored("✓ 初始化成功", "green"))

            # 2. 测试插入
            print(colored("\n2. 测试数据插入", "yellow"))
            texts = [
                "这是第一条测试文本",
                "这是第二条测试文本，带有metadata",
                "这是第三条测试文本"
            ]
            metadata = {"type": "test", "priority": "high"}
            
            # 插入文本，不指定索引（应该会使用global_index）
            id1 = collection.insert(texts[0])
            # 插入文本，带metadata
            id2 = collection.insert(texts[1], metadata=metadata)
            # 插入文本到指定索引
            collection.create_index("custom_index", description="自定义测试索引")
            id3 = collection.insert(texts[2], None, "custom_index")
            
            print(colored("✓ 数据插入成功", "green"))

            # 3. 测试检索
            print(colored("\n3. 测试检索功能", "yellow"))
            
            # 测试全局索引检索
            results = collection.retrieve("测试文本", topk=2)
            print(f"全局索引检索结果数量: {len(results)}")
            assert len(results) > 0, "全局索引检索失败"
            
            # 测试指定索引检索
            results = collection.retrieve("测试文本", topk=2, index_name="custom_index")
            print(f"自定义索引检索结果数量: {len(results)}")
            assert len(results) > 0, "自定义索引检索失败"
            
            # 测试带metadata的检索
            results = collection.retrieve(
                "测试文本",
                topk=2,
                with_metadata=True,
                metadata_filter_func=lambda m: m and m.get("priority") == "high"
            )
            assert any(r["metadata"].get("priority") == "high" for r in results), "metadata过滤失败"
            
            print(colored("✓ 检索功能测试通过", "green"))

            # 4. 测试更新和删除
            print(colored("\n4. 测试更新和删除", "yellow"))
            
            # 测试更新
            new_text = "这是更新后的文本"
            collection.update(texts[0], new_text)
            results = collection.retrieve(new_text, topk=1)
            assert results[0] == new_text, "更新操作失败"
            
            # 测试删除
            collection.delete(texts[1])
            try:
                collection.retrieve(texts[1], topk=1)
                raise AssertionError("删除操作失败")
            except:
                pass
            
            print(colored("✓ 更新和删除功能测试通过", "green"))

            # 5. 测试持久化
            print(colored("\n5. 测试持久化", "yellow"))
            
            # 保存
            save_path = os.path.join(test_dir, "save_test")
            collection.store(save_path)
            
            # 加载
            collection_dir = os.path.join(save_path, "vdb_collection", test_name)
            loaded_collection = VDBMemoryCollection.load(test_name, embedding_model, collection_dir)
            results = loaded_collection.retrieve("测试文本", topk=1)
            assert len(results) > 0, "持久化后检索失败"
            
            print(colored("✓ 持久化功能测试通过", "green"))

            print(colored("\n=== 所有测试通过！===", "green"))

        except Exception as e:
            print(colored(f"\n测试失败: {str(e)}", "red"))
            raise
        finally:
            # 清理测试数据
            try:
                shutil.rmtree(test_dir)
            except:
                pass

    run_test()