"""
Milvus 后端管理工具
提供 Milvus / Milvus Lite 的初始化、文档管理和检索功能
"""

import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from pymilvus import MilvusClient  # noqa: F401


class MilvusBackend:
    """Milvus 后端管理器（支持本地 Milvus Lite 与远程 Milvus）"""

    def __init__(self, config: dict[str, Any], logger: logging.Logger | Any = None):
        """
        初始化 Milvus 后端

        Args:
            config: Milvus 配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # 连接与集合配置
        self.host: str = self.config.get("host", "localhost")
        self.port: int = int(self.config.get("port", 19530))
        self.persistence_path: str | None = self.config.get(
            "persistence_path", "./milvus_db"
        )  # 可选，优先级高于 host/port

        self.collection_name: str = self.config.get("collection_name", "retriever_collection")
        self.dim: int | None = self.config.get("dim", 1024)  # 稠密向量维度
        raw_metric_type = self.config.get("metric_type")
        if not raw_metric_type:
            # 未提供则默认 COSINE，不做校验
            metric_type_value: str = "COSINE"
        else:
            # 提供了则严格校验，仅支持 IP/COSINE/L2（大小写不敏感，统一为大写）
            allowed_metric_types = {"IP", "COSINE", "L2"}
            metric_upper = str(raw_metric_type).upper()
            if metric_upper not in allowed_metric_types:
                raise ValueError(
                    f"Invalid metric_type: {raw_metric_type}. Allowed: {sorted(allowed_metric_types)}"
                )
            metric_type_value = metric_upper
        self.metric_type: str = metric_type_value
        self.drop_ratio_search = self.config.get(
            "drop_ratio_search", 0.2
        )  # 稀疏向量搜索时，drop 比例
        self.search_type = self.config.get("search_type", "sparse")  # 搜索类型，sparse 或 dense
        self.dense_insert_batch_size = self.config.get(
            "dense_insert_batch_size", 128
        )  # 稠密向量插入批次大小

        # 客户端
        self.client: Any = None  # Will be initialized by _init_client
        self._init_client()
        self._init_collection()

    def _init_client(self):
        """初始化 Milvus 客户端，支持 Milvus Lite（本地 .db 文件）与远程服务"""
        try:
            from pymilvus import MilvusClient

            # 判断使用本地还是远程模式
            if self.host in ["localhost", "127.0.0.1"] and not self.config.get("force_http", False):
                self.client = MilvusClient(self.persistence_path or "./milvus.db")
                self.logger.info(
                    f"Initialized Milvus persistent client at: {self.persistence_path}"
                )
            else:
                # 远程服务器模式
                full_host = (
                    f"http://{self.host}:{self.port}"
                    if not self.host.startswith("http")
                    else self.host
                )

                self.client = MilvusClient(full_host)
                self.logger.info(
                    f"Initialized Milvus HTTP client at: http://{self.host}:{self.port}"
                )

        except ImportError as e:
            self.logger.error(f"Failed to import pymilvus: {e}")
            raise ImportError(
                "Milvus dependencies not available. Install with: pip install pymilvus"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize Milvus client: {e}")
            raise

    def _ensure_client(self):
        """Ensure client is initialized"""
        if self.client is None:
            raise RuntimeError("Milvus client is not initialized")

    def _init_collection(self):
        """初始化或获取 Milvus 集合，必要时创建索引"""
        self._ensure_client()
        try:
            # 尝试直接获取已存在的集合
            try:
                # 通过检查集合是否能正常查询来验证集合存在
                self.client.load_collection(collection_name=self.collection_name)  # type: ignore
                self.logger.info(f"Retrieved existing Milvus collection: {self.collection_name}")
                return
            except Exception:
                # 集合不存在，需要创建新集合
                self.logger.debug(
                    f"Collection '{self.collection_name}' does not exist, creating new one"
                )
                # 创建集合 - 导入必要的数据类型
                try:
                    from pymilvus import DataType
                except Exception as e:
                    self.logger.error(f"Failed to import PyMilvus schema classes: {e}")
                    raise

                try:
                    schema = self.client.create_schema(auto_id=False)
                    index_params = self.client.prepare_index_params()
                    schema.add_field(
                        "id",
                        DataType.VARCHAR,
                        max_length=2000,
                        is_primary=True,
                        auto_id=False,
                    )
                    schema.add_field("text", DataType.VARCHAR, max_length=2000)  # 文本字段
                    self.logger.info(self.search_type + "=" * 60)
                    if self.search_type == "sparse":
                        schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)  # 稀疏向量字段

                        index_params.add_index(
                            field_name="sparse",
                            index_type="SPARSE_INVERTED_INDEX",
                            metric_type="IP",
                        )

                    if self.search_type == "dense":
                        schema.add_field("dense", DataType.FLOAT_VECTOR, dim=self.dim)  # 稠密向量

                        index_params.add_index(
                            field_name="dense",
                            index_type="AUTOINDEX",
                            metric_type=self.metric_type,
                        )

                    self.client.create_collection(
                        collection_name=self.collection_name,
                        schema=schema,
                        index_params=index_params,
                    )

                    # 创建集合后，立即加载以确保可以使用
                    self.client.load_collection(collection_name=self.collection_name)

                    self.logger.info(
                        f"Created and loaded new Milvus collection {self.collection_name} successfully!"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to create Milvus collection: {e}")
                    raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Milvus collection: {e}")
            raise

    def add_dense_documents(
        self,
        documents: list[str],
        dense_embeddings: list[np.ndarray],
        doc_ids: list[str],
    ) -> list[str]:
        """
        添加稠密向量文档，防止内存溢出，分批插入

        Args:
            documents: 文本列表
            embeddings: 向量列表（list[float] 或可转 list）
            doc_ids: 文档 ID 列表
        Returns:
            成功插入的文档 ID 列表
        """
        try:
            # 转换 embedding 格式（milvus 需要 list 格式）
            dense_embeddings_list = [embedding.tolist() for embedding in dense_embeddings]
            docs = []
            # 生成文档ID
            doc_ids = [f"doc_{int(time.time() * 1000)}_{i}" for i in range(len(documents))]
            for i in range(len(documents)):
                docs.append(
                    {
                        "id": doc_ids[i],
                        "text": documents[i],
                        "dense": dense_embeddings_list[i],
                    }
                )

            if len(docs) > self.dense_insert_batch_size:
                for i in range(0, len(docs), self.dense_insert_batch_size):
                    self.client.insert(
                        collection_name=self.collection_name,
                        data=docs[i : i + self.dense_insert_batch_size],
                    )
            else:
                self.client.insert(collection_name=self.collection_name, data=docs)

            self.logger.info(
                f"Added {len(docs)} documents to Milvus collection {self.collection_name}"
            )
            return doc_ids
        except Exception as e:
            self.logger.error(f"Error adding dense documents to Milvus: {e}")
            return []

    def add_sparse_documents(
        self, documents: list[str], sparse_embeddings, doc_ids: list[str]
    ) -> list[str]:
        """
        添加稀疏向量文档

        Args:
            documents: 文本列表
            sparse_embeddings: 稀疏向量列表（来自BGEM3EmbeddingFunction）
            doc_ids: 文档 ID 列表
        Returns:
            成功插入的文档 ID 列表
        """
        try:
            docs = []
            for i in range(len(documents)):
                # 处理稀疏向量格式
                sparse_vector = sparse_embeddings[i]

                # 如果是scipy稀疏矩阵（csr_array/csr_matrix），转换为字典格式
                if hasattr(sparse_vector, "tocoo"):
                    # scipy sparse matrix to dict
                    coo = sparse_vector.tocoo()
                    sparse_dict = {
                        int(idx): float(val) for idx, val in zip(coo.col, coo.data, strict=False)
                    }
                elif hasattr(sparse_vector, "indices") and hasattr(sparse_vector, "data"):
                    # 处理 csr_array 格式
                    sparse_dict = {
                        int(idx): float(val)
                        for idx, val in zip(sparse_vector.indices, sparse_vector.data, strict=False)
                    }
                elif isinstance(sparse_vector, dict):
                    # 已经是字典格式
                    sparse_dict = sparse_vector
                else:
                    # 尝试转换为字典
                    self.logger.warning(f"Unknown sparse vector format: {type(sparse_vector)}")
                    sparse_dict = dict(sparse_vector) if hasattr(sparse_vector, "__iter__") else {}

                docs.append({"id": doc_ids[i], "text": documents[i], "sparse": sparse_dict})

            # 插入数据
            self.client.insert(collection_name=self.collection_name, data=docs)
            self.logger.info(
                f"Added {len(docs)} documents to Milvus collection {self.collection_name}"
            )

            return doc_ids
        except Exception as e:
            self.logger.error(f"Error adding sparse documents to Milvus: {e}")
            return []

    def sparse_search(self, query_text: str, top_k: int) -> list[str]:
        """
        在 Milvus 中执行稀疏向量搜索

        Args:
            query_text: 查询文本
            top_k: 返回的文档数量

        Returns:
            文本结果列表
        """
        try:
            # 使用 BGEM3EmbeddingFunction 生成查询向量
            try:
                from pymilvus.model.hybrid import (
                    BGEM3EmbeddingFunction,  # type: ignore[import-not-found]
                )
            except ImportError:
                try:
                    from pymilvus.model import (
                        BGEM3EmbeddingFunction,  # type: ignore[import-not-found]
                    )
                except ImportError:
                    self.logger.error(
                        "Please install: pip install 'pymilvus[model]' or pip install pymilvus.model"
                    )
                    return []

            embedding_model = BGEM3EmbeddingFunction(use_fp16=False, device="cpu")
            query_embeddings = embedding_model.encode_queries([query_text])

            # 提取稀疏向量
            if isinstance(query_embeddings, dict) and "sparse" in query_embeddings:
                sparse_vector = query_embeddings["sparse"][0]
            else:
                sparse_vector = query_embeddings[0]

            # 处理稀疏向量格式转换为字典
            if hasattr(sparse_vector, "tocoo"):
                # scipy sparse matrix to dict
                coo = sparse_vector.tocoo()
                query_vector = {
                    int(idx): float(val) for idx, val in zip(coo.col, coo.data, strict=False)
                }
            elif hasattr(sparse_vector, "indices") and hasattr(sparse_vector, "data"):
                # 处理 csr_array 格式
                query_vector = {
                    int(idx): float(val)
                    for idx, val in zip(sparse_vector.indices, sparse_vector.data, strict=False)
                }
            elif isinstance(sparse_vector, dict):
                # 已经是字典格式
                query_vector = sparse_vector
            else:
                # 尝试转换为字典
                self.logger.warning(f"Unknown sparse vector format: {type(sparse_vector)}")
                query_vector = dict(sparse_vector) if hasattr(sparse_vector, "__iter__") else {}

            # 执行搜索
            hits = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                anns_field="sparse",
                search_params={"metric_type": "IP", "params": {}},
                limit=top_k,
                output_fields=["text"],
            )

            results = hits[0]
            sparse_results = []

            if results and len(results) > 0:
                for r in results:
                    sparse_results.append(r.entity.get("text"))  # type: ignore[union-attr]
            return sparse_results
        except Exception as e:
            self.logger.error(f"Error executing Milvus sparse search: {e}")
            return []

    def dense_search(self, query_vector: np.ndarray, top_k: int) -> list[str]:
        """
        在 Milvus 中执行稠密向量搜索

        Args:
            query_vector: 查询向量
            top_k: 返回的文档数量

        Returns:
            文本结果列表
        """
        try:
            print(f"MilvusBackend.search: using top_k = {top_k}")

            hits = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                anns_field="dense",
                search_params={"metric_type": self.metric_type, "params": {}},
                limit=top_k,
                output_fields=["text"],
            )

            results = hits[0]
            dense_results = []
            if results and len(results) > 0:
                for r in results:
                    dense_results.append(r.entity.get("text"))  # type: ignore[union-attr]
            return dense_results
        except Exception as e:
            self.logger.error(f"Error executing Milvus search: {e}")
            return []

    def delete_collection(self, collection_name: str) -> bool:
        """删除当前集合"""
        try:
            self.client.drop_collection(collection_name)
            self.logger.info(f"Deleted Milvus collection: {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting Milvus collection: {e}")
            return False

    def get_collection_info(self) -> dict[str, Any]:
        """
        获取集合信息

        Returns:
            包含集合信息的字典
        """
        try:
            count = None
            try:
                stats = self.client.get_collection_stats(self.collection_name)
                count = stats.get("row_count") if isinstance(stats, dict) else None
            except Exception:
                pass
            return {
                "backend": "milvus",
                "collection_name": self.collection_name,
                "document_count": count,
                "persistence_path": (
                    self.persistence_path if hasattr(self, "persistence_path") else None
                ),
            }
        except Exception as e:
            self.logger.error(f"Failed to get Milvus collection info: {e}")
            return {"backend": "milvus", "error": str(e)}

    def save_config(self, save_path: str) -> bool:
        """
        保存 milvus 配置信息

        Args:
            save_path: 保存路径

        Returns:
            是否保存成功
        """
        try:
            os.makedirs(save_path, exist_ok=True)
            config_path = os.path.join(save_path, "milvus_config.json")
            stats = self.client.get_collection_stats(self.collection_name)
            count = stats.get("row_count") if isinstance(stats, dict) else None
            config_info = {
                "collection_name": self.collection_name,
                "collection_count": count,
                "backend_type": "milvus",
                "milvus_config": self.config,
                "saved_time": time.time(),
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_info, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Successfully saved Milvus config to: {save_path}")
            self.logger.info(
                f"Milvus collection '{self.collection_name}' contains {config_info['collection_count']} documents"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to save Milvus config: {e}")
            return False

    def load_config(self, load_path: str) -> bool:
        """
        从配置文件重新连接到 Milvus 集合

        Args:
            load_path: 配置文件路径

        Returns:
            是否加载成功
        """
        try:
            config_path = os.path.join(load_path, "milvus_config.json")
            if os.path.exists(config_path):
                with open(config_path, encoding="utf-8") as f:
                    config_info = json.load(f)
                collection_name = config_info.get("collection_name")
                if collection_name:
                    self.collection_name = collection_name
                    self.client.load_collection(collection_name=self.collection_name)
                    stats = self.client.get_collection_stats(self.collection_name)
                    count = stats.get("row_count") if isinstance(stats, dict) else None
                    self.logger.info(
                        f"Reloaded Milvus collection name from config: {self.collection_name}"
                    )
                    self.logger.info(f"Collection contains {count} documents")
                    return True
                else:
                    self.logger.error("No collection name found in Milvus config")
                    return False
            else:
                self.logger.error(f"Milvus config not found at: {config_path}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to load Milvus config: {e}")
            return False

    def load_knowledge_from_file_dense(self, file_path: str, embedding_model) -> bool:
        """
        从文件加载知识库到 Milvus

        Args:
            file_path: 知识库文件路径
            embedding_model: 嵌入模型实例

        Returns:
            是否加载成功
        """
        try:
            self.logger.info(f"Loading knowledge from file: {file_path}")
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 将知识库按段落分割
            documents = [doc.strip() for doc in content.split("\n\n") if doc.strip()]

            if documents:
                # 生成文档ID
                doc_ids = [f"doc_{int(time.time() * 1000)}_{i}" for i in range(len(documents))]

                # 生成 embedding
                embeddings = []
                for doc in documents:
                    embedding = embedding_model.embed(doc)
                    embeddings.append(np.array(embedding, dtype=np.float32))

                # dense 向量添加到 Milvus
                added_dense_ids = self.add_dense_documents(documents, embeddings, doc_ids)

                if added_dense_ids:
                    self.logger.info(
                        f"Loaded {len(added_dense_ids)} dense documents from {file_path}"
                    )
                    return True
                else:
                    self.logger.error(f"Failed to add documents from {file_path}")
                    return False
            else:
                self.logger.warning(f"No valid documents found in {file_path}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to load knowledge from file {file_path}: {e}")
            return False

    def load_knowledge_from_file_sparse(self, file_path: str) -> bool:
        """
        从文件加载知识库到 Milvus

        Args:
            file_path: 知识库文件路径

        Returns:
            是否加载成功
        """
        try:
            self.logger.info(f"Loading knowledge from file: {file_path}")
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 将知识库按段落分割
            documents = [doc.strip() for doc in content.split("\n\n") if doc.strip()]

            if documents:
                # 生成文档ID
                doc_ids = [f"doc_{int(time.time() * 1000)}_{i}" for i in range(len(documents))]

                try:
                    from pymilvus.model.hybrid import BGEM3EmbeddingFunction

                    embedding_model = BGEM3EmbeddingFunction(use_fp16=False, device="cpu")

                    # 生成 sparse embedding
                    sparse_embeddings = embedding_model.encode_documents(documents)

                    # 提取稀疏向量部分
                    if isinstance(sparse_embeddings, dict) and "sparse" in sparse_embeddings:
                        embeddings = sparse_embeddings["sparse"]
                    else:
                        # 如果返回格式不同，直接使用
                        embeddings = sparse_embeddings

                except Exception as e:
                    self.logger.error(f"Failed to import or use BGEM3EmbeddingFunction: {e}")
                    raise

                # sparse 向量添加到 Milvus
                added_sparse_ids = self.add_sparse_documents(documents, embeddings, doc_ids)

                if added_sparse_ids:
                    self.logger.info(
                        f"Loaded {len(added_sparse_ids)} sparse documents from {file_path}"
                    )
                    return True
                else:
                    self.logger.error(f"Failed to add documents from {file_path}")
                    return False
            else:
                self.logger.warning(f"No valid documents found in {file_path}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to load knowledge from file {file_path}: {e}")
            return False

    def clear_collection(self) -> bool:
        """清空集合中的所有文档，保留集合结构与索引"""
        try:
            # 通过过滤条件删除全部实体（匹配所有非空字符串id）
            self.client.delete(collection_name=self.collection_name, filter='id != ""')
            self.logger.info(f"Cleared documents in Milvus collection '{self.collection_name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear Milvus collection: {e}")
            return False

    def update_document(self, doc_id: str, new_content: str, new_embedding: np.ndarray) -> bool:
        """
        更新指定文档
        """
        try:
            self.client.upsert(  # type: ignore[attr-defined]
                collection_name=self.collection_name,
                data=[{"id": doc_id, "text": new_content, "dense": new_embedding.tolist()}],
            )
            self.logger.info(
                f"Updated document {doc_id} in Milvus collection '{self.collection_name}'"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to update document {doc_id} in Milvus collection '{self.collection_name}': {e}"
            )
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        删除指定文档
        """
        try:
            self.client.delete(collection_name=self.collection_name, filter=f'id == "{doc_id}"')
            self.logger.info(
                f"Deleted document {doc_id} in Milvus collection '{self.collection_name}'"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to delete document {doc_id} in Milvus collection '{self.collection_name}': {e}"
            )
            return False


class MilvusUtils:
    """Milvus 工具类"""

    @staticmethod
    def check_milvus_available() -> bool:
        """
        检查 MilvusDB 是否可用
        """
        try:
            import pymilvus  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def validate_milvus_config(config: dict[str, Any]) -> bool:
        """
        验证 Milvus 配置的有效性
        """
        required_keys = ["collection_name"]

        for key in required_keys:
            if key not in config:
                return False

        return True
