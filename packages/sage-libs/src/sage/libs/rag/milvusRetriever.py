import json
from typing import Tuple, List, Optional, Any, Dict
import os
import time
import numpy as np

from sage.core.api.function.map_function import MapFunction
from sage.libs.utils.milvus import MilvusBackend, MilvusUtils

# Milvus稠密向量检索
class MilvusDenseRetriever(MapFunction):
    """
    使用 Milvus 后端进行稠密向量检索。
    """
    def __init__(self, config, enable_profile=False, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.enable_profile = enable_profile

        # 只支持Milvus后端
        self.backend_type = "milvus"

        # 通用配置
        self.vector_dimension = self.config.get("dimension", 384)
        self.top_k = self.config.get("top_k", 5)
        self.embedding_config = self.config.get("embedding", {})

        # 初始化Milvus后端
        self.milvus_config = config.get("milvus_dense", {})
        self._init_milvus_backend()

        # 初始化 embedding 模型
        self._init_embedding_model()
        
        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            if hasattr(self.ctx, 'env_base_dir') and self.ctx.env_base_dir:
                self.data_base_path = os.path.join(self.ctx.env_base_dir, ".sage_states", "retriever_data")
            else:
                # 使用默认路径
                self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "retriever_data")

            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _init_milvus_backend(self):
        """ 初始化milvus后端"""
        try:
            # 检查 milvus 是否可用
            if not MilvusUtils.check_milvus_available():
                raise ImportError("Milvus dependencies not available. Install with: pip install pymilvus")
            
            # 验证配置
            if not MilvusUtils.validate_milvus_config(self.milvus_config):
                raise ValueError("Invalid Milvus configuration")
            
            # 初始化后端
            self.milvus_backend = MilvusBackend(config=self.milvus_config, logger=self.logger)

            # 自动加载知识库文件
            knowledge_file = self.milvus_config.get("knowledge_file")
            if knowledge_file and os.path.exists(knowledge_file):
                self._load_knowledge_from_file(knowledge_file)

        except Exception as e:
            self.logger.error(f"Failed to initialize milvus: {e}")
            raise

    def _load_knowledge_from_file(self, file_path: str):
        """ 从文件中加载知识库 """
        try:
            # 使用Milvus后端加载
            success = self.milvus_backend.load_knowledge_from_file(file_path, self.embedding_model)
            if not success:
                self.logger.error(f"Failed to load knowledge from file: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to load knowledge from file: {e}")


    def _init_embedding_model(self):
        """ 初始化embedding模型"""
        try:
            from sage.middleware.utils.embedding.embedding_model import EmbeddingModel
            
            embedding_method = self.embedding_config.get("method", "default")
            model = self.embedding_config.get("model", "sentence-transformers/all-MiniLM-L6-v2")

            self.logger.info(f"Initializing embedding model with method: {embedding_method}")
            self.embedding_model = EmbeddingModel(
                method=embedding_method,
                model=model
            )

            # 验证向量维度
            if hasattr(self.embedding_model, 'get_dim'):
                model_dim = self.embedding_model.get_dim()
                if model_dim != self.vector_dimension:
                    self.logger.warning(f"Embedding model dimension ({model_dim}) != configured dimension ({self.vector_dimension})")
                    # 更新向量维度以匹配模型
                    self.vector_dimension = model_dim
        except ImportError as e:
            self.logger.error(f"Failed to import EmbeddingModel: {e}")
            raise ImportError("Embedding model dependencies not available")

    def add_documents(self, documents: List[str], doc_ids: Optional[List[str]] = None) -> List[str]:
        """ 
        添加文档到milvus 
        Args:
            documents: 文档内容列表
            doc_ids: 文档ID列表，如果为None则自动生成
        Returns:
            添加的文档ID列表
        """
        if not documents:
            self.logger.warning("No documents to add")
            return []

        if doc_ids is None:
            doc_ids = [f"doc_{int(time.time() * 1000)}_{i}" for i in range(len(documents))]
        elif len(doc_ids) != len(documents):
            raise ValueError("doc_ids length must match documents length")

        # 生成 embedding
        embeddings = []
        for doc in documents:
            embedding = self.embedding_model.embed(doc)
            print(embedding)
            embeddings.append(np.array(embedding, dtype=np.float32))

        # 使用 milvus 后端添加文档
        return self.milvus_backend.add_dense_documents(documents, embeddings, doc_ids)

    def _save_data_record(self, query, retrieved_docs):
        """
        保存检索数据记录
        """
        if not self.enable_profile:
            return
        
        record = {
            'timestamp': time.time(),
            'query': query,
            'retrieved_docs': retrieved_docs,
            'backend_type': self.backend_type,
            'backend_config': getattr(self, f"{self.backend_type}_config", {}),
            'embedding_config': self.embedding_config,
        }
        
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        """
        将数据记录持久化到文件
        """
        if not self.enable_profile or not self.data_records:
            return
        
        timestamp = int(time.time())
        filename = f"milvus_dense_retriever_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def execute(self, data: str) -> Dict[str, Any]:
        """
        执行检索
        Args:
            data: 查询字符串、元组或字典
        Returns:
            dict: {"query": ..., "results": ..., "input": 原始输入, ...}
        """
                # 支持字典类型输入，优先取 question 字段
        is_dict_input = isinstance(data, dict)
        if is_dict_input:
            input_query = data.get("question", "")
        elif isinstance(data, tuple) and len(data) > 0:
            input_query = data[0]
        else:
            input_query = data

        if not isinstance(input_query, str):
            self.logger.error(f"Invalid input query type: {type(input_query)}")
            if is_dict_input:
                data["results"] = []
                return data
            else:
                return {"query": str(input_query), "results": [], "input": data}

        self.logger.info(f"[ {self.__class__.__name__}]: Starting {self.backend_type.upper()} retrieval for query: {input_query}")
        self.logger.info(f"[ {self.__class__.__name__}]: Using top_k = {self.top_k}")

        try:
            # 生成查询向量
            query_embedding = self.embedding_model.encode(input_query)
            query_vector = np.array(query_embedding, dtype=np.float32)

            # 使用Milvus执行稠密检索
            retrieved_docs = self.milvus_backend.dense_search(
                query_vector=query_vector,
                top_k=self.top_k,
            )

            self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Retrieved {len(retrieved_docs)} documents from Milvus\033[0m")
            self.logger.debug(f"Retrieved documents: {retrieved_docs[:3]}...")  # 只显示前3个文档的预览

            print(f"Query: {input_query}")
            print(f"Configured top_k: {self.top_k}")
            print(f"Retrieved {len(retrieved_docs)} documents from Milvus")
            print(retrieved_docs)

            # 保存数据记录（只有enable_profile=True时才保存）
            if self.enable_profile:
                self._save_data_record(input_query, retrieved_docs)

            if is_dict_input:
                data["results"] = retrieved_docs
                return data
            else:
                return {"query": input_query, "results": retrieved_docs, "input": data}

        except Exception as e:
            self.logger.error(f" retrieval failed: {str(e)}")
            if is_dict_input:
                data["results"] = []
                return data
            else:
                return {"query": input_query, "results": [], "input": data}

    def save_config(self, save_path: str) -> bool:
        """
        保存配置到磁盘
        Args:
            save_path: 保存路径
        Returns:
            是否保存成功
        """
        return self.milvus_backend.save_config(save_path)

    def load_config(self, load_path: str) -> bool:
        """
        从磁盘加载配置
        Args:
            load_path: 加载路径
        Returns:
            是否加载成功
        """
        return self.milvus_backend.load_config(load_path)

    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息
        """
        return self.milvus_backend.get_collection_info()

    def delete_collection(self) -> bool:
        """
        删除集合
        """
        return self.milvus_backend.delete_collection()

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, 'enable_profile') and self.enable_profile:
            try:
                self._persist_data_records()
            except:
                pass


# Milvus稀疏向量检索
class MilvusSparseRetriever(MapFunction):
    """
    使用 Milvus 后端进行稀疏向量检索。
    """
    def __init__(self, config, enable_profile=False, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.enable_profile = enable_profile

        # 只支持Milvus后端
        self.backend_type = "milvus"

        # 通用配置
        self.top_k = self.config.get("top_k", 10)

        # 初始化Milvus后端
        self.milvus_config = config.get("milvus_sparse", {})
        self._init_milvus_backend()
        
        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            if hasattr(self.ctx, 'env_base_dir') and self.ctx.env_base_dir:
                self.data_base_path = os.path.join(self.ctx.env_base_dir, ".sage_states", "retriever_data")
            else:
                # 使用默认路径
                self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "retriever_data")

            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _init_milvus_backend(self):
        """ 初始化milvus后端"""
        try:
            # 检查 milvus 是否可用
            if not MilvusUtils.check_vilvusdb_availability():
                raise ImportError("Milvus dependencies not available. Install with: pip install pymilvus")
            
            # 验证配置
            if not MilvusUtils.validate_milvus_config(self.milvus_config):
                raise ValueError("Invalid Milvus configuration")
            
            # 初始化后端
            self.milvus_backend = MilvusBackend(config=self.milvus_config, logger=self.logger)

            # 自动加载知识库文件
            knowledge_file = self.milvus_config.get("knowledge_file")
            if knowledge_file and os.path.exists(knowledge_file):
                self._load_knowledge_from_file(knowledge_file)

        except Exception as e:
            self.logger.error(f"Failed to initialize milvus: {e}")
            raise

    def _load_knowledge_from_file(self, file_path: str):
        """ 从文件中加载知识库 """
        try:
            # 使用Milvus后端加载
            success = self.milvus_backend.load_knowledge_from_file(file_path, self.embedding_model)
            if not success:
                self.logger.error(f"Failed to load knowledge from file: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to load knowledge from file: {e}")

    def add_documents(self, documents: List[str], doc_ids: Optional[List[str]] = None) -> List[str]:
        """ 
        添加文档到milvus 
        Args:
            documents: 文档内容列表
            doc_ids: 文档ID列表，如果为None则自动生成
        Returns:
            添加的文档ID列表
        """
        if not documents:
            self.logger.warning("No documents to add")
            return []

        if doc_ids is None:
            doc_ids = [f"doc_{int(time.time() * 1000)}_{i}" for i in range(len(documents))]
        elif len(doc_ids) != len(documents):
            raise ValueError("doc_ids length must match documents length")

        # 使用 milvus 后端添加文档
        return self.milvus_backend.add_sparse_documents(documents, doc_ids)

    def _save_data_record(self, query, retrieved_docs):
        """
        保存检索数据记录
        """
        if not self.enable_profile:
            return
        
        record = {
            'timestamp': time.time(),
            'query': query,
            'retrieved_docs': retrieved_docs,
            'backend_type': self.backend_type,
            'backend_config': getattr(self, f"{self.backend_type}_config", {}),
        }
        
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        """
        将数据记录持久化到文件
        """
        if not self.enable_profile or not self.data_records:
            return
        
        timestamp = int(time.time())
        filename = f"milvus_dense_retriever_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def execute(self, data: str) -> Dict[str, Any]:
        """
        执行检索
        Args:
            data: 查询字符串、元组或字典
        Returns:
            dict: {"query": ..., "results": ..., "input": 原始输入, ...}
        """
                # 支持字典类型输入，优先取 question 字段
        is_dict_input = isinstance(data, dict)
        if is_dict_input:
            input_query = data.get("question", "")
        elif isinstance(data, tuple) and len(data) > 0:
            input_query = data[0]
        else:
            input_query = data

        if not isinstance(input_query, str):
            self.logger.error(f"Invalid input query type: {type(input_query)}")
            if is_dict_input:
                data["results"] = []
                return data
            else:
                return {"query": str(input_query), "results": [], "input": data}

        self.logger.info(f"[ {self.__class__.__name__}]: Starting {self.backend_type.upper()} retrieval for query: {input_query}")
        self.logger.info(f"[ {self.__class__.__name__}]: Using top_k = {self.top_k}")

        try:
            # 使用Milvus执行稀疏检索
            retrieved_docs = self.milvus_backend.sparse_search(
                query_text=input_query,
                top_k=self.top_k,
            )

            self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Retrieved {len(retrieved_docs)} documents from Milvus\033[0m")
            self.logger.debug(f"Retrieved documents: {retrieved_docs[:3]}...")  # 只显示前3个文档的预览

            print(f"Query: {input_query}")
            print(f"Configured top_k: {self.top_k}")
            print(f"Retrieved {len(retrieved_docs)} documents from Milvus")
            print(retrieved_docs)

            # 保存数据记录（只有enable_profile=True时才保存）
            if self.enable_profile:
                self._save_data_record(input_query, retrieved_docs)

            if is_dict_input:
                data["results"] = retrieved_docs
                return data
            else:
                return {"query": input_query, "results": retrieved_docs, "input": data}

        except Exception as e:
            self.logger.error(f" retrieval failed: {str(e)}")
            if is_dict_input:
                data["results"] = []
                return data
            else:
                return {"query": input_query, "results": [], "input": data}

    def save_config(self, save_path: str) -> bool:
        """
        保存配置到磁盘
        Args:
            save_path: 保存路径
        Returns:
            是否保存成功
        """
        return self.milvus_backend.save_config(save_path)

    def load_config(self, load_path: str) -> bool:
        """
        从磁盘加载配置
        Args:
            load_path: 加载路径
        Returns:
            是否加载成功
        """
        return self.milvus_backend.load_config(load_path)

    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息
        """
        return self.milvus_backend.get_collection_info()

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, 'enable_profile') and self.enable_profile:
            try:
                self._persist_data_records()
            except:
                pass