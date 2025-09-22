import os
import json
import yaml
import shutil
import inspect
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.middleware.components.neuromem.memory_collection.base_collection import BaseMemoryCollection
from sage.middleware.components.neuromem.search_engine.vdb_index import index_factory
from sage.middleware.components.neuromem.utils.path_utils import get_default_data_dir
from sage.middleware.utils.embedding.embedding_api import apply_embedding_model


class VDBMemoryCollection(BaseMemoryCollection):
    """
    Memory collection with vector database support.
    支持向量数据库功能的内存集合类。
    
    支持两种初始化方式：
    1. 通过声明VDBMemoryCollection(config, corpus)创建
    2. 通过VDBMemoryCollection.load(name, vdb_path)恢复式创建
    """
    def __init__(
        self, 
        config: Dict[str, Any]
    ):
        """
        初始化VDBMemoryCollection
        
        Args:
            config: 配置字典，必须包含name等参数
        """
        # 初始化CustomLogger
        self.logger = CustomLogger()
        
        if "name" not in config:
            self.logger.error("config中必须包含'name'字段")
            raise ValueError("config中必须包含'name'字段")
        
        self.name = config["name"]
        super().__init__(self.name)
        
        # 使用新的参数命名规范，删除向后兼容的代码
        self.default_embedding_model_name = config.get("default_embedding_model", "default")
        self.default_embedding_model = apply_embedding_model(self.default_embedding_model_name)
        self.default_dim = config.get("default_dim", self.default_embedding_model.get_dim())
        self.default_topk = config.get("default_topk", 5)
        self.default_backend_type = config.get("default_vdb_backend", "FAISS")
        
        self.index_info = {}  # index_name -> dict: { embedding_model_name, dim, index, backend_type, topk, description, metadata_filter_func, metadata_conditions }
        self.index_embedding_model = {} # index_name -> embedding_model 以供随时使用
        
        # 创建全局索引，优先使用config中的global_index配置，否则使用默认配置
        global_index_config = config.get("global_index", {})
        if "name" not in global_index_config:
            global_index_config["name"] = "global_index"
        if "embedding_model" not in global_index_config:
            global_index_config["embedding_model"] = self.default_embedding_model_name
        if "dim" not in global_index_config:
            global_index_config["dim"] = self.default_dim
        if "backend_type" not in global_index_config:
            global_index_config["backend_type"] = self.default_backend_type
        if "topk" not in global_index_config:
            global_index_config["topk"] = self.default_topk
        
        self.create_index(config=global_index_config)
    
    def batch_insert_data(self, data: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
        """
        批量插入数据到collection中（仅存储，不创建索引）
        
        Args:
            data: 数据列表（文本、图片等）
            metadatas: 对应的元数据列表，可选
        """
        self.logger.info(f"Batch inserting {len(data)} data items to storage")
        
        if metadatas is not None and len(metadatas) != len(data):
            raise ValueError("metadatas length must match data length")
        
        for i, item in enumerate(data):
            stable_id = self._get_stable_id(item)
            self.text_storage.store(stable_id, item)
            
            if metadatas and metadatas[i]:
                metadata = metadatas[i]
                # 自动注册所有未知的元数据字段
                for field_name in metadata.keys():
                    if not self.metadata_storage.has_field(field_name):
                        self.metadata_storage.add_field(field_name)
                self.metadata_storage.store(stable_id, metadata)
    
    def _serialize_func(self, func):
        """
        改善lambda序列化管理
        """
        if func is None:
            return None
        try:
            return inspect.getsource(func).strip()
        except Exception:
            return str(func)
    
    def _deserialize_func(self, func_str):
        """
        反序列化函数字符串
        """
        if func_str is None or func_str == "None" or func_str == "":
            return lambda m: True
        
        # 简单的lambda函数恢复，实际生产环境中需要更安全的方式
        try:
            # 这里只是一个简单的示例，实际应该使用更安全的方式
            if func_str.startswith("lambda"):
                return eval(func_str)
            else:
                return lambda m: True
        except Exception:
            return lambda m: True

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

        # 1. 存储text和metadata
        self.text_storage.store_to_disk(os.path.join(collection_dir, "text_storage.json"))
        self.metadata_storage.store_to_disk(os.path.join(collection_dir, "metadata_storage.json"))

        # 2. 索引和index_info
        indexes_dir = os.path.join(collection_dir, "indexes")
        os.makedirs(indexes_dir, exist_ok=True)
        saved_index_info = {}
        for index_name, info in self.index_info.items():
            idx = info["index"]
            idx_path = os.path.join(indexes_dir, index_name)
            os.makedirs(idx_path, exist_ok=True)
            idx.store(idx_path)
            saved_index_info[index_name] = {
                "embedding_model_name": info.get("embedding_model_name", "default"),
                "dim": info.get("dim", self.default_dim),
                "backend_type": info.get("backend_type", "FAISS"),
                "topk": info.get("topk", self.default_topk),
                "description": info.get("description", ""),
                "index_type": idx.__class__.__name__,
                "metadata_filter_func": self._serialize_func(info.get("metadata_filter_func")),
                "metadata_conditions": info.get("metadata_conditions", {}),
            }

        # 3. collection全局config
        config = {
            "name": self.name,
            "default_embedding_model_name": self.default_embedding_model_name,
            "default_dim": self.default_dim,
            "default_topk": self.default_topk,
            "default_backend_type": self.default_backend_type,
            "indexes": saved_index_info,
        }
        with open(os.path.join(collection_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return {"collection_path": collection_dir}

    @classmethod
    def load(cls, name: str, vdb_path: Optional[str] = None):
        """
        从磁盘加载VDBMemoryCollection实例
        
        Args:
            name: 集合名称
            vdb_path: 加载路径，如果为None则使用默认路径
        """
        if vdb_path is None:
            # 如果没有指定路径，使用默认路径结构
            base_dir = get_default_data_dir()
            load_path = os.path.join(base_dir, "vdb_collection", name)
        else:
            load_path = vdb_path
        
        # 此时 load_path 应该是指向具体collection的完整路径
        config_path = os.path.join(load_path, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No config found for collection at {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 使用新的初始化方式创建实例
        instance = cls(
            config={
                "name": name,
                "default_embedding_model": config.get("default_embedding_model_name", config.get("embedding_model_name", "mockembedder")),
                "default_dim": config.get("default_dim", config.get("dim", 128)),
                "default_topk": config.get("default_topk", 5),
                "default_vdb_backend": config.get("default_backend_type", config.get("backend_type", "FAISS"))
            }
        )
        
        # 加载storages (不再加载vector_storage)
        instance.text_storage.load_from_disk(os.path.join(load_path, "text_storage.json"))
        instance.metadata_storage.load_from_disk(os.path.join(load_path, "metadata_storage.json"))
        
        # 清空在初始化时创建的默认索引
        instance.index_info.clear()
        
        # 加载索引和index_info
        indexes_dir = os.path.join(load_path, "indexes")
        for index_name, idx_info in config.get("indexes", {}).items():
            idx_type = idx_info["index_type"]
            idx_path = os.path.join(indexes_dir, index_name)
            
            try:
                # 使用工厂类加载索引
                if idx_type == "FaissIndex":
                    idx = index_factory.load_index(index_name, "FAISS", idx_path)
                else:
                    # 尝试通过工厂类加载其他类型的索引
                    backend_type = idx_type.replace("Index", "").upper()
                    idx = index_factory.load_index(index_name, backend_type, idx_path)
                    
            except Exception as e:
                raise NotImplementedError(f"Unknown index_type {idx_type}")
            
            # 恢复index_info
            instance.index_info[index_name] = {
                "embedding_model_name": idx_info.get("embedding_model_name", "default"),
                "dim": idx_info.get("dim", config.get("default_dim", config.get("dim", 128))),
                "index": idx,
                "backend_type": idx_info.get("backend_type", "FAISS"),
                "topk": idx_info.get("topk", 5),
                "description": idx_info.get("description", ""),
                "metadata_filter_func": instance._deserialize_func(idx_info.get("metadata_filter_func")),
                "metadata_conditions": idx_info.get("metadata_conditions", {}),
            }
            
            # 恢复embedding模型
            embedding_model_name = idx_info.get("embedding_model_name", "default")
            instance.index_embedding_model[index_name] = apply_embedding_model(embedding_model_name)

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
        config: Optional[dict] = None,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
    ):
        """
        使用元数据筛选条件创建新的向量索引。
        """
        # 检查1: config必须不为空且包含name字段
        if config is None:
            self.logger.warning("config不能为空，无法创建索引")
            return 0
            
        if "name" not in config:
            self.logger.warning("config中必须包含'name'字段，无法创建索引")
            return 0
            
        index_name = config["name"]
        
        # 检查2: 如果索引已存在，不允许创建
        if index_name in self.index_info:
            self.logger.warning(f"索引 '{index_name}' 已存在，无法重复创建")
            return 0
        
        # 从config中解包Collection级别的参数，如果没有则使用默认值
        backend_type = config.get("backend_type", self.default_backend_type)
        description = config.get("description", f"Index for {index_name}")
        embedding_model_name = config.get("embedding_model", self.default_embedding_model_name)
        dim = config.get("dim", self.default_dim)
        topk = config.get("topk", self.default_topk)
        
        # 创建embedding模型
        embedding_model = apply_embedding_model(embedding_model_name)
        
        # 准备传递给工厂的Index级别配置参数
        # Collection负责参数检查和分离，工厂只负责创建索引
        index_config = {
            "name": index_name,
            "dim": dim
        }
        # 将其他Index级别的配置参数传递给工厂
        for key, value in config.items():
            if key not in ["backend_type", "description", "embedding_model", "topk"]:
                index_config[key] = value
        
        # 使用工厂类创建空索引，现在直接传递config
        try:
            # 使用新的基于config的创建方法，简化接口
            index = index_factory.create_index_from_config(
                config=index_config
            )
            
            # 存储到index_info中
            self.index_info[index_name] = {
                "embedding_model_name": embedding_model_name,
                "dim": dim,
                "index": index,
                "backend_type": backend_type,
                "topk": topk,
                "description": description,
                "metadata_filter_func": metadata_filter_func,
                "metadata_conditions": metadata_conditions,
            }
            
            # 存储embedding模型到index_embedding_model中
            self.index_embedding_model[index_name] = embedding_model
            
            self.logger.info(f"成功创建索引 '{index_name}'，后端类型: {backend_type}")
            return 1  # 成功创建返回1
            
        except Exception as e:
            self.logger.error(f"Failed to create index {index_name} with backend {backend_type}: {e}")
            raise

    # 直接删除某个索引
    def delete_index(self, index_name: str):
        """
        删除指定名称的索引。
        """
        if index_name in self.index_info:
            del self.index_info[index_name]
        else:
            raise ValueError(f"Index '{index_name}' does not exist.")
            
        # 同时删除embedding模型
        if index_name in self.index_embedding_model:
            del self.index_embedding_model[index_name]

    # 列举索引信息
    def list_index(self, *index_names) -> List[Dict[str, str]]:
        """
        列出指定的索引或所有索引及其描述信息。
        
        Args:
            *index_names: 可选的索引名称，如果不指定则返回所有索引
            
        Returns:
            List[Dict]: [{"name": ..., "description": ...}, ...]
        """
        if index_names:
            # 如果指定了索引名称，只返回这些索引的信息
            result = []
            for name in index_names:
                if name in self.index_info:
                    result.append({"name": name, "description": self.index_info[name]["description"]})
                else:
                    self.logger.warning(f"索引 '{name}' 不存在")
            return result
        else:
            # 如果没有指定，返回所有索引信息
            return [
                {"name": name, "description": info["description"]}
                for name, info in self.index_info.items()
            ]

    # 单条文本插入（指定索引，否则全局）
    def insert(
        self,
        raw_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        *index_names
    ) -> str:
        self.logger.debug(f"VDBMemoryCollection: insert called")
        
        # 首先存储数据到storage
        stable_id = self._get_stable_id(raw_text)
        self.text_storage.store(stable_id, raw_text)

        if metadata:
            # 自动注册所有未知的元数据字段
            for field_name in metadata.keys():
                if not self.metadata_storage.has_field(field_name):
                    self.metadata_storage.add_field(field_name)
            self.metadata_storage.store(stable_id, metadata)

        # 如果没有指定索引，插入到全局索引
        if not index_names:
            if "global_index" not in self.index_info:
                # 如果全局索引不存在，创建它
                self.logger.info(f"创建全局索引: global_index")
                self.create_index(config={"name": "global_index"})
            index_names = ("global_index",)
        
        # 检查指定的索引是否存在
        index_names_set = set(index_names)
        for index_name in index_names_set:
            if index_name not in self.index_info:
                self.logger.warning(f"指定的索引 '{index_name}' 不存在，插入操作失败")
                return "0"  # 返回0表示失败

        # 修正插入逻辑：为每个索引使用对应的embedding模型
        for index_name in index_names_set:
            # 获取该索引对应的embedding模型
            if index_name in self.index_embedding_model:
                embedding_model = self.index_embedding_model[index_name]
            else:
                # 如果索引没有对应的embedding模型，使用默认模型
                self.logger.warning(f"索引 '{index_name}' 没有对应的embedding模型，使用默认模型")
                embedding_model = self.default_embedding_model
            
            # 使用对应的embedding模型编码文本
            embedding = embedding_model.encode(raw_text)
            
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
            
            # 检查embedding维度是否与索引要求一致
            expected_dim = self.index_info[index_name]["dim"]
            if embedding.shape[-1] != expected_dim:
                self.logger.warning(f"索引 '{index_name}' 要求维度 {expected_dim}，但embedding维度为 {embedding.shape[-1]}，跳过插入")
                continue
            
            # 插入到对应的索引中
            index = self.index_info[index_name]["index"]
            index.insert(embedding, stable_id)

        return stable_id

    # 单条文本更新（指定索引更新）
    def update(
        self,
        former_data: str,
        new_data: str,
        new_metadata: Optional[Dict[str, Any]] = None,
        *index_names: str
    ) -> str:
        old_id = self._get_stable_id(former_data)
        if not self.text_storage.has(old_id):
            raise ValueError("Original data not found.")

        self.text_storage.delete(old_id)
        self.metadata_storage.delete(old_id)

        for index_info in self.index_info.values():
            index_info["index"].delete(old_id)

        return self.insert(new_data, new_metadata, *index_names)

    # 单条文本删除（全索引删除）
    def delete(self, raw_text: str):
        stable_id = self._get_stable_id(raw_text)
        self.text_storage.delete(stable_id)
        self.metadata_storage.delete(stable_id)

        for index_info in self.index_info.values():
            index_info["index"].delete(stable_id)

    def retrieve(
        self,
        raw_data: str,
        topk: Optional[int] = None,
        index_name: Optional[str] = None,
        threshold: Optional[float] = None,
        with_metadata: bool = False,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
    ):
        self.logger.debug(f"VDBMemoryCollection: retrieve called")   
        
        # 如果没有指定索引，使用或创建全局索引
        if index_name is None:
            index_name = "global_index"
            if index_name not in self.index_info:
                self.logger.info(f"Creating global index: {index_name}")
                # 创建全局索引时，需要考虑元数据过滤条件
                config = {"name": index_name}
                self.create_index(config=config, metadata_filter_func=metadata_filter_func, **metadata_conditions)

        if index_name not in self.index_info:
            raise ValueError(f"Index '{index_name}' does not exist.")

        if topk is None:
            topk = int(self.default_topk)

        # 使用对应索引的embedding模型
        if index_name in self.index_embedding_model:
            embedding_model = self.index_embedding_model[index_name]
        else:
            self.logger.warning(f"索引 '{index_name}' 没有对应的embedding模型，使用默认模型")
            embedding_model = self.default_embedding_model

        query_embedding = embedding_model.encode(raw_data)

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
            
        sub_index = self.index_info[index_name]["index"]
        # 增加检索数量以补偿过滤后可能的损失
        search_topk = topk * 2  # 检索更多结果以确保过滤后有足够的结果
        top_k_ids, distances = sub_index.search(query_embedding, topk=search_topk, threshold=threshold)

        if top_k_ids and isinstance(top_k_ids[0], (list, np.ndarray)):
            top_k_ids = top_k_ids[0]
        if distances and isinstance(distances[0], (list, np.ndarray)):
            distances = distances[0]
        top_k_ids = [str(i) for i in top_k_ids]

        # 应用元数据过滤
        if metadata_filter_func or metadata_conditions:
            filtered_ids = self.filter_ids(top_k_ids, metadata_filter_func, **metadata_conditions)
        else:
            filtered_ids = top_k_ids

        # 截取需要的数量，检索到几个就返回几个
        final_ids = filtered_ids[:topk]

        # 如果检索结果少于请求数量，记录信息但不警告
        if len(final_ids) < topk:
            self.logger.info(f"Retrieved {len(final_ids)} results (requested {topk})")

        if with_metadata:
            return [{"text": self.text_storage.get(i), "metadata": self.metadata_storage.get(i)} for i in final_ids]
        else:
            return [self.text_storage.get(i) for i in final_ids]

    def update_index(self, index_name: str):
        """
        更新指定索引：删除当前索引，保留config，重新创建索引并批量插入数据
        
        Args:
            index_name: 要更新的索引名称
        """
        if index_name not in self.index_info:
            raise ValueError(f"Index '{index_name}' does not exist.")
        
        # 保存原始配置信息
        info = self.index_info[index_name]
        original_config = {
            "name": index_name,
            "backend_type": info["backend_type"],
            "description": info["description"],
            "embedding_model": info["embedding_model_name"],
            "dim": info["dim"],
            "topk": info["topk"]
        }
        original_metadata_filter_func = info.get("metadata_filter_func")
        original_metadata_conditions = info.get("metadata_conditions", {})
        
        self.logger.info(f"开始更新索引: {index_name}")
        
        # 删除当前索引
        self.delete_index(index_name)
        
        # 重新创建索引
        self.create_index(
            config=original_config,
            metadata_filter_func=original_metadata_filter_func,
            **original_metadata_conditions
        )
        
        # 从storage中获取所有数据
        all_ids = self.get_all_ids()
        
        if not all_ids:
            self.logger.warning("storage中没有数据，索引更新完成但为空")
            return
        
        # 应用元数据过滤（如果index_info中有规则）
        filtered_ids = []
        if original_metadata_filter_func or original_metadata_conditions:
            for item_id in all_ids:
                metadata = self.metadata_storage.get(item_id)
                # 应用过滤函数
                if original_metadata_filter_func and not original_metadata_filter_func(metadata or {}):
                    continue
                # 应用条件过滤
                if original_metadata_conditions:
                    match = True
                    for key, value in original_metadata_conditions.items():
                        if not metadata or metadata.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                filtered_ids.append(item_id)
        else:
            filtered_ids = all_ids
        
        # 获取对应的embedding模型
        embedding_model = self.index_embedding_model[index_name]
        
        # 批量编码和插入
        vectors = []
        valid_ids = []
        
        for item_id in filtered_ids:
            text = self.text_storage.get(item_id)
            if text:
                embedding = embedding_model.encode(text)
                
                # 统一处理不同格式的embedding结果
                if hasattr(embedding, "detach") and hasattr(embedding, "cpu"):
                    embedding = embedding.detach().cpu().numpy()
                if isinstance(embedding, list):
                    embedding = np.array(embedding)
                if not isinstance(embedding, np.ndarray):
                    embedding = np.array(embedding)
                embedding = embedding.astype(np.float32)
                
                vectors.append(embedding)
                valid_ids.append(item_id)
        
        # 使用底层的batch_insert方法批量插入
        if vectors and valid_ids:
            index = self.index_info[index_name]["index"]
            result = index.batch_insert(vectors, valid_ids)
            self.logger.info(f"索引 '{index_name}' 更新完成，插入了 {result} 条数据")
        else:
            self.logger.warning(f"索引 '{index_name}' 更新完成，但没有找到符合条件的数据")

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

        try:
            # 1. 测试新的初始化方式
            print(colored("\n1. 测试新的初始化方式", "yellow"))
            
            # 方式1：通过config创建，使用mockembedder确保维度一致
            config = {
                "name": test_name,
                "default_embedding_model": "mockembedder",
                "default_dim": 128,  # 与mockembedder的固定维度一致
                "default_topk": 5,
                "default_vdb_backend": "FAISS"
            }
            collection = VDBMemoryCollection(config=config)
            print(colored("✓ 通过config初始化成功", "green"))
            
            # 方式2：测试batch_insert_data
            corpus = ["第一条文本", "第二条文本", "第三条文本"]
            config_with_corpus = {
                "name": f"{test_name}_corpus",
                "default_embedding_model": "mockembedder",
                "default_dim": 128,
                "default_topk": 5,
                "default_vdb_backend": "FAISS"
            }
            collection_with_corpus = VDBMemoryCollection(config=config_with_corpus)
            collection_with_corpus.batch_insert_data(corpus)
            # batch_insert_data 只存储数据，需要手动插入到索引
            for text in corpus:
                collection_with_corpus.insert(text)
            print(colored("✓ 通过batch_insert_data成功", "green"))

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
            collection.create_index(config={"name": "custom_index", "description": "自定义测试索引"})
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
            assert any(r.get("metadata", {}).get("priority") == "high" for r in results if isinstance(r, dict)), "metadata过滤失败"
            
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
            
            print(colored("✓ 更新和删除功能测试通过", "green"))

            # 5. 测试持久化
            print(colored("\n5. 测试持久化", "yellow"))
            
            # 保存
            save_path = os.path.join(test_dir, "save_test")
            collection.store(save_path)
            
            # 测试新的load方式
            collection_dir = os.path.join(save_path, "vdb_collection", test_name)
            loaded_collection = VDBMemoryCollection.load(test_name, collection_dir)
            results = loaded_collection.retrieve("测试文本", topk=1)
            assert len(results) > 0, "持久化后检索失败"
            
            print(colored("✓ 持久化功能测试通过", "green"))

            # 6. 测试batch_insert_data功能
            print(colored("\n6. 测试batch_insert_data功能", "yellow"))
            corpus_results = collection_with_corpus.retrieve("文本", topk=3)
            print(f"从batch_insert_data的集合检索结果数量: {len(corpus_results)}")
            assert len(corpus_results) > 0, "batch_insert_data集合检索失败"
            print(colored("✓ batch_insert_data功能测试通过", "green"))

            # 7. 测试update_index功能
            print(colored("\n7. 测试update_index功能", "yellow"))
            # 向collection中添加更多数据
            collection.insert("测试update_index的文本1")
            collection.insert("测试update_index的文本2")
            # 更新global_index
            collection.update_index("global_index")
            results = collection.retrieve("update_index", topk=5)
            print(f"update_index后检索结果数量: {len(results)}")
            print(colored("✓ update_index功能测试通过", "green"))

            # 8. 测试lambda函数在持久化后的工作情况
            print(colored("\n8. 测试lambda函数持久化", "yellow"))
            
            # 创建一个新的collection专门测试lambda
            lambda_test_name = "lambda_test_collection"
            lambda_config = {
                "name": lambda_test_name,
                "default_embedding_model": "mockembedder",
                "default_dim": 128,
                "default_topk": 5,
                "default_vdb_backend": "FAISS"
            }
            lambda_collection = VDBMemoryCollection(config=lambda_config)
            
            # 添加测试数据
            test_data = [
                ("重要文档1", {"priority": "high", "category": "important"}),
                ("普通文档2", {"priority": "low", "category": "normal"}),
                ("重要文档3", {"priority": "high", "category": "important"}),
                ("普通文档4", {"priority": "medium", "category": "normal"}),
            ]
            
            for text, metadata in test_data:
                lambda_collection.insert(text, metadata)
            
            # 创建一个带有lambda函数的索引
            high_priority_filter = lambda m: m and m.get("priority") == "high"
            lambda_collection.create_index(
                config={
                    "name": "high_priority_index",
                    "description": "只包含高优先级文档的索引"
                },
                metadata_filter_func=high_priority_filter
            )
            
            # 向带lambda的索引插入数据
            for text, metadata in test_data:
                if high_priority_filter(metadata):
                    lambda_collection.insert(text, metadata, "high_priority_index")
            
            # 测试保存前的lambda过滤效果
            print("保存前测试lambda过滤...")
            before_save_results = lambda_collection.retrieve(
                "文档", 
                topk=10, 
                index_name="high_priority_index"
            )
            print(f"保存前高优先级索引检索到 {len(before_save_results)} 条结果")
            assert len(before_save_results) == 2, f"预期2条高优先级结果，实际得到{len(before_save_results)}条"
            
            # 保存collection
            lambda_save_path = os.path.join(test_dir, "lambda_save_test")
            lambda_collection.store(lambda_save_path)
            print("lambda collection保存完成")
            
            # 加载collection
            lambda_collection_dir = os.path.join(lambda_save_path, "vdb_collection", lambda_test_name)
            loaded_lambda_collection = VDBMemoryCollection.load(lambda_test_name, lambda_collection_dir)
            print("lambda collection加载完成")
            
            # 测试加载后的lambda过滤效果
            print("加载后测试lambda过滤...")
            after_load_results = loaded_lambda_collection.retrieve(
                "文档", 
                topk=10, 
                index_name="high_priority_index"
            )
            print(f"加载后高优先级索引检索到 {len(after_load_results)} 条结果")
            
            # 验证结果是否一致
            assert len(after_load_results) == len(before_save_results), \
                f"加载后结果数量不一致：保存前{len(before_save_results)}条，加载后{len(after_load_results)}条"
            
            # 测试lambda函数在检索时的工作情况
            print("测试加载后lambda函数在检索时的过滤效果...")
            filtered_results = loaded_lambda_collection.retrieve(
                "文档",
                topk=10,
                with_metadata=True,
                metadata_filter_func=lambda m: m and m.get("priority") == "high"
            )
            
            high_priority_count = sum(1 for r in filtered_results 
                                    if isinstance(r, dict) and 
                                       r.get("metadata", {}).get("priority") == "high")
            print(f"通过lambda过滤检索到 {high_priority_count} 条高优先级结果")
            assert high_priority_count > 0, "lambda函数在加载后没有正确工作"
            
            # 测试update_index是否能正确处理lambda函数
            print("测试update_index对lambda函数的处理...")
            loaded_lambda_collection.insert("新增重要文档", {"priority": "high", "category": "new"})
            loaded_lambda_collection.update_index("high_priority_index")
            
            updated_results = loaded_lambda_collection.retrieve(
                "文档", 
                topk=10, 
                index_name="high_priority_index"
            )
            print(f"update_index后高优先级索引检索到 {len(updated_results)} 条结果")
            # 应该包含新增的重要文档，所以结果应该增加
            assert len(updated_results) >= len(after_load_results), \
                "update_index后lambda函数没有正确处理新数据"
            
            print(colored("✓ lambda函数持久化测试通过", "green"))
            print("  - lambda函数序列化/反序列化正常")
            print("  - 持久化后检索过滤功能正常")
            print("  - update_index正确处理lambda函数")

            print(colored("\n=== 所有测试通过！===", "green"))

        except Exception as e:
            print(colored(f"\n测试失败: {str(e)}", "red"))
            import traceback
            traceback.print_exc()
            raise
        finally:
            # 清理测试数据
            try:
                shutil.rmtree(test_dir)
            except:
                pass

    run_test()