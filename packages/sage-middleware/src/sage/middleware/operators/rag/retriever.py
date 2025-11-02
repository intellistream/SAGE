import json
import os
import time
from typing import Any, List

import numpy as np
from sage.common.components.sage_embedding.embedding_model import EmbeddingModel
from sage.common.config.output_paths import get_states_file
from sage.kernel.operators import MapOperator
from sage.libs.integrations.chroma import ChromaBackend, ChromaUtils
from sage.libs.integrations.milvus import MilvusBackend, MilvusUtils


# ChromaDB 密集检索器
class ChromaRetriever(MapOperator):
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

        # 先初始化 embedding 模型
        self._init_embedding_model()

        # 再初始化 ChromaDB 后端（这样知识库加载时embedding模型已可用）
        self.chroma_config = config.get("chroma", {})
        self._init_chroma_backend()

        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            # Use unified output path system
            self.data_base_path = str(get_states_file("dummy", "retriever_data").parent)
            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _init_chroma_backend(self):
        """初始化 ChromaDB 后端"""
        try:
            # 检查 ChromaDB 是否可用
            if not ChromaUtils.check_chromadb_availability():
                raise ImportError(
                    "ChromaDB dependencies not available. Install with: pip install chromadb"
                )

            # 验证配置
            if not ChromaUtils.validate_chroma_config(self.chroma_config):
                raise ValueError("Invalid ChromaDB configuration")

            # 创建 ChromaDB 后端实例
            self.chroma_backend = ChromaBackend(self.chroma_config, self.logger)

            # 自动加载知识库文件
            knowledge_file = self.chroma_config.get("knowledge_file")
            if knowledge_file:
                # 如果是相对路径，尝试从当前工作目录和项目根目录解析
                if not os.path.isabs(knowledge_file):
                    # 尝试从当前目录
                    if os.path.exists(knowledge_file):
                        resolved_path = knowledge_file
                    else:
                        # 尝试从项目根目录解析
                        project_root = os.getcwd()
                        while project_root != "/" and not os.path.exists(
                            os.path.join(project_root, "pyproject.toml")
                        ):
                            project_root = os.path.dirname(project_root)

                        potential_path = os.path.join(project_root, knowledge_file)
                        if os.path.exists(potential_path):
                            resolved_path = potential_path
                        else:
                            resolved_path = knowledge_file
                else:
                    resolved_path = knowledge_file

                if os.path.exists(resolved_path):
                    self._load_knowledge_from_file(resolved_path)
                else:
                    self.logger.warning(f"Knowledge file not found: {resolved_path}")

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
        embedding_method = self.embedding_config.get("method", "default")
        model = self.embedding_config.get("model", "sentence-transformers/all-MiniLM-L6-v2")

        self.logger.info(f"Initializing embedding model with method: {embedding_method}")
        self.embedding_model = EmbeddingModel(method=embedding_method, model=model)

        # 验证向量维度
        if hasattr(self.embedding_model, "get_dim"):
            model_dim = self.embedding_model.get_dim()
            if model_dim != self.vector_dimension:
                self.logger.warning(
                    f"Embedding model dimension ({model_dim}) != configured dimension ({self.vector_dimension})"
                )
                # 更新向量维度以匹配模型
                self.vector_dimension = model_dim

    def add_documents(self, documents: list[str], doc_ids: list[str] | None = None) -> list[str]:
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
            # print(embedding)
            embeddings.append(np.array(embedding, dtype=np.float32))

        # 使用 ChromaDB 后端添加文档
        return self.chroma_backend.add_documents(documents, embeddings, doc_ids)

    def _save_data_record(self, query, retrieved_docs):
        """保存检索数据记录"""
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "query": query,
            "retrieved_docs": retrieved_docs,
            "backend_type": self.backend_type,
            "backend_config": getattr(self, f"{self.backend_type}_config", {}),
            "embedding_config": self.embedding_config,
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
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def execute(self, data: str) -> dict[str, Any]:
        """
        执行检索
        Args:
            data: 查询字符串或字典
        Returns:
            dict: {"query": ..., "retrieval_results": ..., "retrieval_docs": ..., "input": 原始输入}
        """
        is_dict_input = isinstance(data, dict)
        if is_dict_input:
            input_query = data.get("query", "")
        else:
            input_query = data

        if not isinstance(input_query, str):
            self.logger.error(f"Invalid input query type: {type(input_query)}")
            if is_dict_input:
                data.update({
                    "retrieval_results": [],
                    "retrieval_docs": []
                })
                return data
            else:
                return {
                    "query": str(input_query),
                    "retrieval_results": [],
                    "retrieval_docs": [],
                    "input": data
                }

        self.logger.info(
            f"[ {self.__class__.__name__}]: Starting {self.backend_type.upper()} retrieval for query: {input_query}"
        )
        self.logger.info(f"[ {self.__class__.__name__}]: Using top_k = {self.top_k}")

        try:
            # 生成查询向量
            query_embedding = self.embedding_model.embed(input_query)
            query_vector = np.array(query_embedding, dtype=np.float32)

            # 使用 ChromaDB 执行检索
            retrieved_docs = self.chroma_backend.search(query_vector, input_query, self.top_k)

            self.logger.info(
                f"\033[32m[ {self.__class__.__name__}]: Retrieved {len(retrieved_docs)} documents from ChromaDB\033[0m"
            )
            self.logger.debug(
                f"Retrieved documents: {retrieved_docs[:3]}..."
            )  # 只显示前3个文档的预览

            # 将字符串列表转换为标准化的字典格式，以便后续组件使用
            standardized_docs = []
            for doc in retrieved_docs:
                if isinstance(doc, str):
                    standardized_docs.append({"text": doc})
                elif isinstance(doc, dict):
                    # 如果已经是字典，确保有text字段
                    if "text" not in doc and "content" in doc:
                        doc["text"] = doc["content"]
                    elif "text" not in doc:
                        # 将整个字典内容作为text
                        doc["text"] = str(doc)
                    standardized_docs.append(doc)
                else:
                    # 其他类型转为字符串
                    standardized_docs.append({"text": str(doc)})

            # 保存数据记录（只有enable_profile=True时才保存）
            if self.enable_profile:
                self._save_data_record(input_query, standardized_docs)

            # 提取所有原始文档的text字段，供retrieval_docs使用
            retrieval_texts = [
                doc.get("text", doc.get("content", str(doc)))
                for doc in standardized_docs
            ]

            if is_dict_input:
                data.update({
                    "retrieval_results": standardized_docs,
                    "retrieval_docs": retrieval_texts
                })
                return data
            else:
                return {
                    "query": input_query,
                    "retrieval_results": standardized_docs,
                    "retrieval_docs": retrieval_texts,
                    "input": data,
                }

        except Exception as e:
            self.logger.error(f"ChromaDB retrieval failed: {str(e)}")
            if is_dict_input:
                data.update({
                    "retrieval_results": [],
                    "retrieval_docs": []
                })
                return data
            else:
                return {
                    "query": input_query,
                    "retrieval_results": [],
                    "retrieval_docs": [],
                    "input": data
                }

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

    def get_collection_info(self) -> dict[str, Any]:
        """获取集合信息"""
        return self.chroma_backend.get_collection_info()

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except Exception:
                pass


# Milvus稠密向量检索
class MilvusDenseRetriever(MapOperator):
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
            if self.ctx is not None and hasattr(self.ctx, "env_base_dir") and self.ctx.env_base_dir:
                self.data_base_path = os.path.join(
                    self.ctx.env_base_dir, ".sage_states", "retriever_data"
                )
            else:
                # 使用默认路径
                self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "retriever_data")

            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _init_milvus_backend(self):
        """初始化milvus后端"""
        try:
            # 检查 milvus 是否可用
            if not MilvusUtils.check_milvus_available():
                raise ImportError(
                    "Milvus dependencies not available. Install with: pip install pymilvus"
                )

            # 验证配置
            if not MilvusUtils.validate_milvus_config(self.milvus_config):
                raise ValueError("Invalid Milvus configuration")

            # 初始化后端
            self.milvus_backend = MilvusBackend(config=self.milvus_config, logger=self.logger)

            # 自动加载知识库文件
            knowledge_file = self.milvus_config.get("knowledge_file")
            if knowledge_file and os.path.exists(knowledge_file):
                self._load_knowledge_from_file_dense(knowledge_file)

        except Exception as e:
            self.logger.error(f"Failed to initialize milvus: {e}")
            raise

    def _load_knowledge_from_file_dense(self, file_path: str):
        """从文件中加载知识库"""
        try:
            # 使用Milvus后端加载
            success = self.milvus_backend.load_knowledge_from_file_dense(
                file_path, self.embedding_model
            )
            if not success:
                self.logger.error(f"Failed to load knowledge from file: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to load knowledge from file: {e}")

    def _init_embedding_model(self):
        """初始化embedding模型"""
        embedding_method = self.embedding_config.get("method", "sentence_transformers")
        model = self.embedding_config.get("model", "all-MiniLM-L6-v2")

        self.logger.info(f"Initializing embedding model with method: {embedding_method}")
        self.embedding_model = EmbeddingModel(method=embedding_method, model=model)

        # 验证向量维度
        if hasattr(self.embedding_model, "get_dim"):
            model_dim = self.embedding_model.get_dim()
            if model_dim != self.vector_dimension:
                self.logger.warning(
                    f"Embedding model dimension ({model_dim}) != configured dimension ({self.vector_dimension})"
                )
                # 更新向量维度以匹配模型
                self.vector_dimension = model_dim

    def add_documents(self, documents: list[str], doc_ids: list[str] | None = None) -> list[str]:
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
            "timestamp": time.time(),
            "query": query,
            "retrieved_docs": retrieved_docs,
            "backend_type": self.backend_type,
            "backend_config": getattr(self, f"{self.backend_type}_config", {}),
            "embedding_config": self.embedding_config,
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
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def execute(self, data: str) -> dict[str, Any]:
        """
        执行检索
        Args:
            data: 查询字符串、元组或字典
        Returns:
            dict: {"query": ..., "retrieved_docs": ..., "input": 原始输入, ...}
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
                data["retrieved_docs"] = []
                return data
            else:
                return {
                    "query": str(input_query),
                    "retrieved_docs": [],
                    "input": data,
                }

        self.logger.info(
            f"[ {self.__class__.__name__}]: Starting {self.backend_type.upper()} retrieval for query: {input_query}"
        )
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

            self.logger.info(
                f"\033[32m[ {self.__class__.__name__}]: Retrieved {len(retrieved_docs)} documents from Milvus\033[0m"
            )
            self.logger.debug(
                f"Retrieved documents: {retrieved_docs[:3]}..."
            )  # 只显示前3个文档的预览

            print(f"Query: {input_query}")
            print(f"Configured top_k: {self.top_k}")
            print(f"Retrieved {len(retrieved_docs)} documents from Milvus")
            print(retrieved_docs)

            # 保存数据记录（只有enable_profile=True时才保存）
            if self.enable_profile:
                self._save_data_record(input_query, retrieved_docs)

            if is_dict_input:
                data["retrieved_docs"] = retrieved_docs
                # 兼容测试期望的字段名
                data["retrieved_documents"] = retrieved_docs
                return data
            else:
                return {
                    "query": input_query,
                    "retrieved_docs": retrieved_docs,
                    "retrieved_documents": retrieved_docs,
                    "input": data,
                }

        except Exception as e:
            self.logger.error(f" retrieval failed: {str(e)}")
            if is_dict_input:
                data["retrieved_docs"] = []
                data["retrieved_documents"] = []
                return data
            else:
                return {
                    "query": input_query,
                    "retrieved_docs": [],
                    "retrieved_documents": [],
                    "input": data,
                }

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

    def get_collection_info(self) -> dict[str, Any]:
        """
        获取集合信息
        """
        return self.milvus_backend.get_collection_info()

    def delete_collection(self, collection_name: str) -> bool:
        """
        删除集合
        """
        return self.milvus_backend.delete_collection(collection_name)

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except Exception:
                pass


# Milvus稀疏向量检索
class MilvusSparseRetriever(MapOperator):
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
        self._init_embedding_model()

        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            if self.ctx is not None and hasattr(self.ctx, "env_base_dir") and self.ctx.env_base_dir:
                self.data_base_path = os.path.join(
                    self.ctx.env_base_dir, ".sage_states", "retriever_data"
                )
            else:
                # 使用默认路径
                self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "retriever_data")

            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _init_milvus_backend(self):
        """初始化milvus后端"""
        try:
            # 检查 milvus 是否可用
            if not MilvusUtils.check_milvus_available():
                raise ImportError(
                    "Milvus dependencies not available. Install with: pip install pymilvus"
                )

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

    def _init_embedding_model(self):
        """初始化embedding模型"""
        try:
            # 尝试新的导入路径（PyMilvus 2.6.0+）
            try:
                from pymilvus.model.hybrid import (
                    BGEM3EmbeddingFunction,  # type: ignore[import-not-found]
                )
            except ImportError:
                # 如果失败，尝试直接从 model 导入
                try:
                    from pymilvus.model import (
                        BGEM3EmbeddingFunction,  # type: ignore[import-not-found]
                    )
                except ImportError:
                    # 最后尝试安装单独的包
                    self.logger.error(
                        "Please install: pip install 'pymilvus[model]' or pip install pymilvus.model"
                    )
                    raise ImportError("Embedding model dependencies not available")

            self.embedding_model = BGEM3EmbeddingFunction(use_fp16=False, device="cpu")

        except ImportError as e:
            self.logger.error(f"Failed to import EmbeddingModel: {e}")
            raise ImportError("Embedding model dependencies not available")

    def _load_knowledge_from_file(self, file_path: str):
        """从文件中加载知识库"""
        try:
            # 使用Milvus后端加载
            success = self.milvus_backend.load_knowledge_from_file_sparse(file_path)
            self.logger.info(f"Loaded {success} documents from {file_path}")
            if not success:
                self.logger.error(f"Failed to load knowledge from file: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to load knowledge from file: {e}")

    def add_documents(self, documents: list[str], doc_ids: list[str] | None = None) -> list[str]:
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

        # 生成 embedding
        embedding = self.embedding_model.encode_documents(documents)
        embeddings = embedding["sparse"]

        if doc_ids is None:
            doc_ids = [f"doc_{int(time.time() * 1000)}_{i}" for i in range(len(documents))]
        elif len(doc_ids) != len(documents):
            raise ValueError("doc_ids length must match documents length")

        # 使用 milvus 后端添加文档
        return self.milvus_backend.add_sparse_documents(documents, embeddings, doc_ids)

    def _save_data_record(self, query, retrieved_docs):
        """
        保存检索数据记录
        """
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "query": query,
            "retrieved_docs": retrieved_docs,
            "backend_type": self.backend_type,
            "backend_config": getattr(self, f"{self.backend_type}_config", {}),
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
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

    def execute(self, data: str) -> dict[str, Any]:
        """
        执行检索
        Args:
            data: 查询字符串、元组或字典
        Returns:
            dict: {"query": ..., "retrieved_docs": ..., "input": 原始输入, ...}
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
                data["retrieved_docs"] = []
                return data
            else:
                return {
                    "query": str(input_query),
                    "retrieved_docs": [],
                    "input": data,
                }

        self.logger.info(
            f"[ {self.__class__.__name__}]: Starting {self.backend_type.upper()} retrieval for query: {input_query}"
        )
        self.logger.info(f"[ {self.__class__.__name__}]: Using top_k = {self.top_k}")

        try:
            # 使用Milvus执行稀疏检索 - 直接传递查询文本，让sparse_search方法处理向量生成
            retrieved_docs = self.milvus_backend.sparse_search(
                query_text=input_query,
                top_k=self.top_k,
            )

            self.logger.info(
                f"\033[32m[ {self.__class__.__name__}]: Retrieved {len(retrieved_docs)} documents from Milvus\033[0m"
            )
            self.logger.debug(
                f"Retrieved documents: {retrieved_docs[:3]}..."
            )  # 只显示前3个文档的预览

            print(f"Query: {input_query}")
            print(f"Configured top_k: {self.top_k}")
            print(f"Retrieved {len(retrieved_docs)} documents from Milvus")
            print(retrieved_docs)

            # 保存数据记录（只有enable_profile=True时才保存）
            if self.enable_profile:
                self._save_data_record(input_query, retrieved_docs)

            if is_dict_input:
                data["retrieved_docs"] = retrieved_docs
                data["retrieved_documents"] = retrieved_docs
                return data
            else:
                return {
                    "query": input_query,
                    "retrieved_docs": retrieved_docs,
                    "retrieved_documents": retrieved_docs,
                    "input": data,
                }

        except Exception as e:
            self.logger.error(f" retrieval failed: {str(e)}")
            if is_dict_input:
                data["retrieved_docs"] = []
                data["retrieved_documents"] = []
                return data
            else:
                return {
                    "query": input_query,
                    "retrieved_docs": [],
                    "retrieved_documents": [],
                    "input": data,
                }

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

    def get_collection_info(self) -> dict[str, Any]:
        """
        获取集合信息
        """
        return self.milvus_backend.get_collection_info()

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except Exception:
                pass


# Wiki18 FAISS 检索器（LongRAG MaxP方法）
class Wiki18FAISSRetriever(MapOperator):
    """
    基于FAISS的Wiki18数据集检索器，实现LongRAG的MaxP方法
    
    参考: 
    - MaxP方法: Dai and Callan (2019) "Deeper Text Understanding for IR with Contextual Neural Language Modeling"
    - LongRAG实现: TIGER-Lab/LongRAG
    
    配置要求:
    - 模型: BAAI/bge-large-en-v1.5 (1024维)
    - Passage长度: 100 words (stride 50)
    - 编码截断: 512 tokens
    - 向量归一化: True
    
    MaxP策略:
    1. 将每个文档分割成多个passages（100 words，stride 50）
    2. 每个passage独立编码（截断到512 tokens）
    3. 检索时计算query与所有passages的相似度
    4. 文档得分 = max(该文档所有passage分数)
    5. 返回Top-K完整文档
    """

    def __init__(self, config, enable_profile=False, skip_index_loading=False, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.enable_profile = enable_profile

        # 配置参数
        self.top_k = config.get("top_k", 8)  # LongRAG默认Top-8
        self.embedding_config = config.get("embedding", {})
        self.faiss_config = config.get("faiss", {})
        
        # MaxP相关配置（LongRAG标准参数）
        self.passage_length = self.faiss_config.get("passage_length", 100)  # words
        self.passage_stride = self.faiss_config.get("passage_stride", 50)   # words
        self.max_length = self.faiss_config.get("max_length", 512)  # tokens，编码截断长度
        self.normalize = self.faiss_config.get("normalize", True)  # 向量归一化
        
        # passage到文档的映射
        self.passage_to_doc = []  # List[int]: passage_id -> document_id

        # 初始化BGE embedding模型
        self._init_bge_model()

        # 初始化FAISS索引（构建索引时可跳过）
        if not skip_index_loading:
            self._init_faiss_index()
        else:
            self.logger.info("跳过索引加载（构建索引模式）")
            self.faiss_index = None
            self.documents = []

        # Profile数据存储
        if self.enable_profile:
            if self.ctx is not None and hasattr(self.ctx, "env_base_dir") and self.ctx.env_base_dir:
                self.data_base_path = os.path.join(
                    self.ctx.env_base_dir, ".sage_states", "retriever_data"
                )
            else:
                self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "retriever_data")

            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _init_bge_model(self):
        """初始化BGE嵌入模型（LongRAG使用bge-large-en-v1.5）"""
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            # 从配置获取模型路径，默认使用LongRAG的bge-large-en-v1.5
            model_path = self.embedding_config.get("model", "BAAI/bge-large-en-v1.5")

            # 检查是否已经通过 CUDA_VISIBLE_DEVICES 设置了 GPU
            import os
            cuda_visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES", None)
            
            if cuda_visible_devices is not None:
                # 如果已设置 CUDA_VISIBLE_DEVICES，使用 cuda（让系统自动选择）
                if torch.cuda.is_available():
                    device = "cuda"
                    self.logger.info(f"BGE模型将使用 CUDA_VISIBLE_DEVICES={cuda_visible_devices} 指定的GPU")
                else:
                    device = "cpu"
                    self.logger.info("BGE模型将使用CPU")
            else:
                # 从配置获取GPU设备，默认使用GPU 0
                gpu_device = self.embedding_config.get("gpu_device", 0)

                # 明确指定GPU设备
                if torch.cuda.is_available():
                    device = f"cuda:{gpu_device}"
                    self.logger.info(f"BGE模型将使用GPU {gpu_device}")
                else:
                    device = "cpu"
                    self.logger.info("BGE模型将使用CPU")

            # 初始化BGE模型（与LongRAG一致）
            self.embedding_model = SentenceTransformer(model_path, device=device)
            
            # LongRAG使用512作为最大序列长度
            self.embedding_model.max_seq_length = self.max_length

            self.logger.info(f"BGE模型初始化成功: {model_path} 在设备 {device}")
            self.logger.info(f"MaxP配置: passage_length={self.passage_length} words, "
                           f"stride={self.passage_stride} words, "
                           f"max_seq_length={self.max_length} tokens, "
                           f"normalize={self.normalize}")

        except ImportError as e:
            self.logger.error(f"无法导入sentence-transformers: {e}")
            self.logger.error("请安装: pip install sentence-transformers")
            raise
        except Exception as e:
            self.logger.error(f"BGE模型初始化失败: {e}")
            raise

    def _init_faiss_index(self):
        """初始化FAISS索引（MaxP模式）"""
        try:
            import faiss

            # FAISS配置 - 从配置文件读取路径
            index_path = self.faiss_config.get("index_path")
            documents_path = self.faiss_config.get("documents_path")

            # 检查必需的配置项
            if not index_path:
                raise ValueError("faiss.index_path 配置项是必需的")
            if not documents_path:
                raise ValueError("faiss.documents_path 配置项是必需的")

            # MaxP模式需要特殊的索引和映射文件
            mapping_path = index_path.replace(".index", "_maxp_mapping.json")
            if os.path.exists(index_path) and os.path.exists(mapping_path):
                self.logger.info(f"加载MaxP模式FAISS索引: {index_path}")
                self.faiss_index = faiss.read_index(index_path)
                
                # 加载passage到文档的映射
                with open(mapping_path, "r") as f:
                    self.passage_to_doc = json.load(f)
                
                self.logger.info(f"MaxP模式: 加载了 {len(self.passage_to_doc)} 个passages，映射到 {len(set(self.passage_to_doc))} 个文档")
            else:
                self.logger.warning(f"未找到MaxP模式索引: {index_path}")
                self.logger.warning("需要先使用 build_maxp_index_from_wiki18() 构建索引")
                # BGE-large-en-v1.5 的维度是 1024
                dimension = 1024
                self.faiss_index = faiss.IndexFlatIP(dimension)
                self.passage_to_doc = []
            
            # 加载文档数据
            if os.path.exists(documents_path):
                self.documents = []
                try:
                    with open(documents_path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    doc = json.loads(line)
                                    self.documents.append(doc)
                                except json.JSONDecodeError as e:
                                    self.logger.warning(
                                        f"跳过无效的JSON行: {line[:100]}... 错误: {e}"
                                    )

                except Exception as e:
                    self.logger.error(f"加载文档文件失败: {e}")
                    self.documents = []

                self.logger.info(f"加载了 {len(self.documents)} 个文档")
            else:
                self.logger.warning(f"未找到文档文件: {documents_path}")
                self.documents = []

        except ImportError as e:
            self.logger.error(f"无法导入FAISS: {e}")
            self.logger.error("请安装FAISS: pip install faiss-cpu 或 pip install faiss-gpu")
            raise
        except Exception as e:
            self.logger.error(f"FAISS索引初始化失败: {e}")
            raise

    def _split_text_to_passages(self, text: str) -> List[str]:
        """
        将文本分割成固定长度的passages（基于空格分词的简单实现）

        Args:
            text: 输入文本

        Returns:
            passages列表
        """
        # 简单的分词（按空格）
        words = text.split()
        passages = []
        
        i = 0
        while i < len(words):
            # 取 passage_length 个词
            passage_words = words[i:i + self.passage_length]
            if len(passage_words) > 0:
                passages.append(" ".join(passage_words))
            
            # 移动窗口（使用stride）
            i += self.passage_stride
            
            # 如果剩余词数少于stride，直接跳到末尾避免重复太多
            if i + self.passage_stride > len(words) and i < len(words):
                i = len(words) - self.passage_length
                if i < 0:
                    break
        
        # 确保至少有一个passage
        if not passages and text.strip():
            passages = [text]
        
        return passages

    def _encode_query(self, query: str) -> np.ndarray:
        """
        使用BGE模型编码查询（LongRAG配置）

        Args:
            query: 查询文本

        Returns:
            查询的向量表示（归一化后）
        """
        try:
            # 使用sentence-transformers的encode方法
            # normalize_embeddings=True 与 LongRAG 的 --normalize True 一致
            embeddings = self.embedding_model.encode(
                [query], 
                normalize_embeddings=self.normalize
            )
            return embeddings[0]  # 返回第一个查询的向量

        except Exception as e:
            self.logger.error(f"查询编码失败: {e}")
            raise

    def _search_faiss(self, query_vector: np.ndarray, top_k: int) -> tuple[list[float], list[int]]:
        """
        在FAISS索引中搜索（MaxP方法）

        Args:
            query_vector: 查询向量
            top_k: 返回top k个结果

        Returns:
            (scores, indices): 相似度分数和文档索引
        """
        try:
            if self.faiss_index.ntotal == 0:
                self.logger.warning("FAISS索引为空，无法检索")
                return [], []

            query_vector = query_vector.reshape(1, -1).astype("float32")
            
            # MaxP模式：检索更多passages，然后聚合到文档级别
            # 检索 top_k * 20 个passages（确保每个文档有足够的passages被考虑）
            k_passages = min(top_k * 20, self.faiss_index.ntotal)
            scores, indices = self.faiss_index.search(query_vector, k_passages)
            
            # 聚合passage分数到文档级别（取每个文档的最大分数）
            doc_scores = {}  # {doc_id: max_score}
            for score, passage_idx in zip(scores[0], indices[0]):
                if passage_idx >= 0 and passage_idx < len(self.passage_to_doc):
                    doc_id = self.passage_to_doc[passage_idx]
                    if doc_id not in doc_scores or score > doc_scores[doc_id]:
                        doc_scores[doc_id] = score
            
            # 按分数排序并返回top-k文档
            sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
            doc_indices = [doc_id for doc_id, _ in sorted_docs]
            doc_scores_list = [score for _, score in sorted_docs]
            
            self.logger.info(f"MaxP: 从 {k_passages} 个passages中聚合得到 {len(doc_indices)} 个文档")
            return doc_scores_list, doc_indices

        except Exception as e:
            self.logger.error(f"FAISS搜索失败: {e}")
            return [], []

    def _format_retrieved_documents(
        self, scores: list[float], indices: list[int]
    ) -> list[dict[str, Any]]:
        """
        格式化检索到的文档

        Args:
            scores: 相似度分数列表
            indices: 文档索引列表

        Returns:
            格式化后的文档列表
        """
        retrieved_docs = []

        for score, idx in zip(scores, indices, strict=False):
            if idx >= 0 and idx < len(self.documents):
                original_doc = self.documents[idx]

                # 创建标准化的文档格式，与ChromaRetriever保持一致
                standardized_doc = {
                    "text": original_doc.get(
                        "contents", str(original_doc)
                    ),  # 将contents字段映射为text
                    "similarity_score": float(score),
                    "document_index": int(idx),
                }

                # 保留其他有用的元数据
                if "title" in original_doc:
                    standardized_doc["title"] = original_doc["title"]
                if "id" in original_doc:
                    standardized_doc["id"] = original_doc["id"]
                if "doc_size" in original_doc:
                    standardized_doc["doc_size"] = original_doc["doc_size"]

                retrieved_docs.append(standardized_doc)

        return retrieved_docs

    def _save_data_record(self, query: str, retrieved_docs: list[dict[str, Any]]):
        """保存检索记录用于分析"""
        if not self.enable_profile:
            return

        record = {
            "timestamp": time.time(),
            "query": query,
            "retrieved_count": len(retrieved_docs),
            "documents": retrieved_docs,
        }

        self.data_records.append(record)

        # 每100条记录持久化一次
        if len(self.data_records) >= 100:
            self._persist_data_records()

    def _persist_data_records(self):
        """持久化数据记录"""
        if not self.enable_profile or not self.data_records:
            return

        try:
            timestamp = int(time.time())
            filename = f"wiki18_faiss_retrieval_records_{timestamp}.json"
            filepath = os.path.join(self.data_base_path, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)

            self.logger.info(f"保存了 {len(self.data_records)} 条检索记录到 {filepath}")
            self.data_records = []  # 清空缓存

        except Exception as e:
            self.logger.error(f"保存检索记录失败: {e}")

    def execute(self, data: str | dict[str, Any] | tuple) -> dict[str, Any]:
        """
        执行检索
        Args:
            data: 查询字符串或字典
        Returns:
            dict: 符合RAG统一数据格式的字典
        """
        # 解析输入
        is_dict_input = isinstance(data, dict)
        if is_dict_input:
            input_query = data.get("query", "")
            if not input_query:
                self.logger.error("输入字典必须包含 'query' 字段")
                data["retrieval_results"] = []
                data["retrieval_docs"] = []
                data["retrieval_time"] = 0.0
                return data
        else:
            input_query = str(data)

        if not input_query.strip():
            self.logger.error("查询不能为空")
            if is_dict_input:
                data["retrieval_results"] = []
                data["retrieval_docs"] = []
                data["retrieval_time"] = 0.0
                return data
            else:
                return {
                    "query": "",
                    "retrieval_results": [],
                    "retrieval_docs": []
                }

        input_query = input_query.strip()
        self.logger.info(
            f"[ {self.__class__.__name__}]: Starting FAISS retrieval for query: {input_query}"
        )
        self.logger.info(f"[ {self.__class__.__name__}]: Using top_k = {self.top_k}")

        try:
            # 编码查询
            query_vector = self._encode_query(input_query)

            # FAISS搜索
            scores, indices = self._search_faiss(query_vector, self.top_k)

            # 格式化结果
            retrieved_docs = self._format_retrieved_documents(scores, indices)

            # 记录检索时间
            self.logger.info(
                f"\033[32m[ {self.__class__.__name__}]: Retrieved {len(retrieved_docs)} documents from FAISS\033[0m"
            )

            # 保存数据记录（只有enable_profile=True时才保存）
            if self.enable_profile:
                self._save_data_record(input_query, retrieved_docs)

            # 提取文档文本
            retrieved_texts = [doc["text"] for doc in retrieved_docs if "text" in doc]

            # 构造输出（使用统一字段名）
            if is_dict_input:
                data["retrieval_results"] = retrieved_docs
                data["retrieval_docs"] = retrieved_texts
                return data
            else:
                return {
                    "query": input_query,
                    "retrieval_results": retrieved_docs,
                    "retrieval_docs": retrieved_texts
                }

        except Exception as e:
            self.logger.error(f"FAISS retrieval failed: {str(e)}")
            if is_dict_input:
                data["retrieval_results"] = []
                data["retrieval_docs"] = []
                data["retrieval_time"] = 0.0
                return data
            else:
                return {
                    "query": input_query,
                    "retrieval_results": [],
                    "retrieval_docs": []
                }

    def build_maxp_index_from_wiki18(self, wiki18_data_path: str, save_path: str = None, batch_size: int = 128):
        """
        从Wiki18数据集构建MaxP模式的FAISS索引（LongRAG配置）
        
        实现MaxP (Dai and Callan, 2019) 方法：
        1. 将每个文档分割成passages（100 words，stride 50）
        2. 为每个passage生成嵌入向量（512 tokens截断，归一化）
        3. 构建FAISS索引用于检索

        Args:
            wiki18_data_path: Wiki18数据集路径（JSONL格式）
            save_path: 索引保存路径（不含扩展名）
            batch_size: 批处理大小（默认128，与LongRAG一致）
        """
        try:
            import faiss

            self.logger.info(f"开始从Wiki18数据构建MaxP模式FAISS索引: {wiki18_data_path}")
            self.logger.info(f"MaxP配置（LongRAG标准）:")
            self.logger.info(f"  - passage_length: {self.passage_length} words")
            self.logger.info(f"  - passage_stride: {self.passage_stride} words")
            self.logger.info(f"  - max_seq_length: {self.max_length} tokens")
            self.logger.info(f"  - normalize: {self.normalize}")
            self.logger.info(f"  - batch_size: {batch_size}")

            # 加载Wiki18数据
            documents = []
            with open(wiki18_data_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        doc = json.loads(line)
                        documents.append(doc)

            self.logger.info(f"加载了 {len(documents)} 个文档")

            # 分割文档为passages并收集
            all_passages = []
            passage_to_doc_map = []
            
            self.logger.info("开始分割文档为passages...")
            for doc_idx, doc in enumerate(documents):
                if doc_idx % 1000 == 0:
                    self.logger.info(f"处理进度: {doc_idx}/{len(documents)}")
                
                # 获取文档内容
                doc_text = doc.get("contents", doc.get("text", ""))
                
                # 分割成passages
                passages = self._split_text_to_passages(doc_text)
                
                # 记录每个passage对应的文档ID
                for passage in passages:
                    all_passages.append(passage)
                    passage_to_doc_map.append(doc_idx)
            
            self.logger.info(f"总共生成了 {len(all_passages)} 个passages（平均每个文档 {len(all_passages)/len(documents):.1f} 个）")

            # 批量编码passages（LongRAG配置：normalize=True）
            # 优化：预分配内存避免 all_embeddings 列表累积和 vstack 双倍内存占用
            self.logger.info("开始批量编码passages...")
            
            # 预分配内存（避免动态增长和 vstack 的双倍内存峰值）
            num_passages = len(all_passages)
            embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            passage_vectors = np.zeros((num_passages, embedding_dim), dtype="float32")
            self.logger.info(f"预分配向量数组: {passage_vectors.shape}, 内存占用: {passage_vectors.nbytes / 1024**3:.2f} GB")
            
            for i in range(0, len(all_passages), batch_size):
                if i % (batch_size * 10) == 0:
                    self.logger.info(f"编码进度: {i}/{len(all_passages)}")
                
                batch_passages = all_passages[i:i + batch_size]
                # normalize_embeddings=True 与 LongRAG 的 --normalize True 一致
                batch_embeddings = self.embedding_model.encode(
                    batch_passages, 
                    normalize_embeddings=self.normalize
                )
                # 直接写入预分配的数组，避免中间列表积累
                passage_vectors[i:i + len(batch_embeddings)] = batch_embeddings
            
            self.logger.info(f"编码完成，向量维度: {passage_vectors.shape}")

            # 创建FAISS索引
            dimension = passage_vectors.shape[1]
            self.faiss_index = faiss.IndexFlatIP(dimension)  # 内积相似度
            
            # 添加向量到索引
            self.faiss_index.add(passage_vectors)
            self.passage_to_doc = passage_to_doc_map
            self.documents = documents

            self.logger.info(f"MaxP FAISS索引构建完成，包含 {self.faiss_index.ntotal} 个passage向量")

            # 保存索引、映射和文档
            if save_path:
                index_path = save_path if save_path.endswith(".index") else save_path + ".index"
                mapping_path = index_path.replace(".index", "_maxp_mapping.json")
                docs_path = save_path.replace(".index", "_documents.jsonl")

                # 保存FAISS索引
                faiss.write_index(self.faiss_index, index_path)
                self.logger.info(f"索引已保存到: {index_path}")
                
                # 保存passage到文档的映射
                with open(mapping_path, "w") as f:
                    json.dump(self.passage_to_doc, f)
                self.logger.info(f"映射已保存到: {mapping_path}")
                
                # 保存文档数据（JSONL格式）
                with open(docs_path, "w", encoding="utf-8") as f:
                    for doc in self.documents:
                        f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                self.logger.info(f"文档已保存到: {docs_path}")

        except Exception as e:
            self.logger.error(f"构建MaxP FAISS索引失败: {e}")
            raise

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, "enable_profile") and self.enable_profile:
            try:
                self._persist_data_records()
            except Exception:
                pass
