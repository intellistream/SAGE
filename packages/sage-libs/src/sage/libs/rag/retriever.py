import re
from typing import Tuple, List, Optional, Dict, Any
import time
import os
import json
import numpy as np


from sage.core.api.function.map_function import MapFunction
from sage.libs.utils.chroma import ChromaBackend, ChromaUtils

# ChromaDB 密集检索器
class ChromaRetriever(MapFunction):
    def __init__(self, config, enable_profile=False, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.enable_profile = enable_profile
        
        # 只支持 ChromaDB 后端
        self.backend_type = "chroma"
        
        # 通用配置
        self.vector_dimension = config.get("dimension", 384)
        self.top_k = config.get("top_k", 10)
        self.embedding_config = config.get("embedding", {})
        
        # 初始化 ChromaDB 后端
        self.chroma_config = config.get("chroma", {})
        self._init_chroma_backend()
        
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
    
    def _init_chroma_backend(self):
        """初始化 ChromaDB 后端"""
        try:
            # 检查 ChromaDB 是否可用
            if not ChromaUtils.check_chromadb_availability():
                raise ImportError("ChromaDB dependencies not available. Install with: pip install chromadb")
            
            # 验证配置
            if not ChromaUtils.validate_chroma_config(self.chroma_config):
                raise ValueError("Invalid ChromaDB configuration")
            
            # 创建 ChromaDB 后端实例
            self.chroma_backend = ChromaBackend(self.chroma_config, self.logger)
            
            # 自动加载知识库文件
            knowledge_file = self.chroma_config.get("knowledge_file")
            if knowledge_file and os.path.exists(knowledge_file):
                self._load_knowledge_from_file(knowledge_file)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
        
    def _load_knowledge_from_file(self, file_path: str):
        """从文件加载知识库"""
        try:
            # 使用 ChromaDB 后端加载
            success = self.chroma_backend.load_knowledge_from_file(file_path, self.embedding_model)
            if not success:
                self.logger.error(f"Failed to load knowledge from file: {file_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to load knowledge from file {file_path}: {e}")
    
    def _init_embedding_model(self):
        """初始化 embedding 模型"""
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
        添加文档到索引中
        Args:
            documents: 文档内容列表
            doc_ids: 文档ID列表，如果为None则自动生成
        Returns:
            添加的文档ID列表
        """
        if not documents:
            return []
            
        # 生成文档ID
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
        
        # 使用 ChromaDB 后端添加文档
        return self.chroma_backend.add_documents(documents, embeddings, doc_ids)

    def _save_data_record(self, query, retrieved_docs):
        """保存检索数据记录"""
        if not self.enable_profile:
            return

        record = {
            'timestamp': time.time(),
            'query': query,
            'retrieved_docs': retrieved_docs,
            'backend_type': self.backend_type,
            'backend_config': getattr(self, f"{self.backend_type}_config", {}),
            'embedding_config': self.embedding_config
        }
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        """将数据记录持久化到文件"""
        if not self.enable_profile or not self.data_records:
            return

        timestamp = int(time.time())
        filename = f"retriever_data_{timestamp}.json"
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
        is_dict_input = isinstance(data, dict)
        if is_dict_input:
            input_query = data.get("query", "")
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
            query_embedding = self.embedding_model.embed(input_query)
            query_vector = np.array(query_embedding, dtype=np.float32)

            # 使用 ChromaDB 执行检索
            retrieved_docs = self.chroma_backend.search(query_vector, input_query, self.top_k)

            self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Retrieved {len(retrieved_docs)} documents from ChromaDB\033[0m")
            self.logger.debug(f"Retrieved documents: {retrieved_docs[:3]}...")  # 只显示前3个文档的预览

            print(f"Query: {input_query}")
            print(f"Configured top_k: {self.top_k}")
            print(f"Retrieved {len(retrieved_docs)} documents from ChromaDB")
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
            self.logger.error(f"ChromaDB retrieval failed: {str(e)}")
            if is_dict_input:
                data["results"] = []
                return data
            else:
                return {"query": input_query, "results": [], "input": data}
    
    def save_index(self, save_path: str) -> bool:
        """
        保存索引到磁盘
        Args:
            save_path: 保存路径
        Returns:
            是否保存成功
        """
        return self.chroma_backend.save_config(save_path)
    
    def load_index(self, load_path: str) -> bool:
        """
        从磁盘加载索引
        Args:
            load_path: 加载路径
        Returns:
            是否加载成功
        """
        return self.chroma_backend.load_config(load_path)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        return self.chroma_backend.get_collection_info()

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, 'enable_profile') and self.enable_profile:
            try:
                self._persist_data_records()
            except:
                pass

class BM25sRetriever(MapFunction): # 目前runtime context还只支持ltm
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.bm25s_collection = self.config.get("bm25s_collection")
        self.bm25s_config = self.config.get("bm25s_config", {})


    def execute(self, data: str) -> Tuple[str, List[str]]:
        input_query = data
        chunks = []
        self.logger.debug(f"Starting BM25s retrieval for query: {input_query}")

        if not self.bm25s_collection:
            raise ValueError("BM25s collection is not configured.")

        try:
            # 使用BM25s配置和输入查询调用检索
            bm25s_results = self.ctx.retrieve(
                # self.bm25s_collection,
                query=input_query,
                collection_config=self.bm25s_config
            )
            chunks.extend(bm25s_results)
            self.logger.info(f"\033[32m[ {self.__class__.__name__}]:Query: {input_query} Retrieved {len(bm25s_results)} from BM25s\033[0m ")
            print(input_query)
            print(bm25s_results)
        except Exception as e:
            self.logger.error(f"BM25s retrieval failed: {str(e)}")

        return (input_query, chunks)