"""
ChromaDB 后端管理工具
提供 ChromaDB 向量数据库的初始化、文档管理和检索功能
"""

from typing import List, Dict, Any, Optional
import time
import os
import json
import numpy as np
import logging


class ChromaBackend:
    """ChromaDB 后端管理器"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger = None):
        """
        初始化 ChromaDB 后端
        
        Args:
            config: ChromaDB 配置字典
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # ChromaDB 基本配置
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 8000)
        self.persistence_path = config.get("persistence_path", "./chroma_db")
        self.collection_name = config.get("collection_name", "dense_retriever_collection")
        self.use_embedding_query = config.get("use_embedding_query", True)
        self.metadata_config = config.get("metadata", {"hnsw:space": "cosine"})
        
        # 初始化客户端和集合
        self.client = None
        self.collection = None
        self._init_client()
        self._init_collection()
    
    def _init_client(self):
        """初始化 ChromaDB 客户端"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # 判断使用本地还是远程模式
            if self.host in ["localhost", "127.0.0.1"] and not self.config.get("force_http", False):
                # 本地持久化模式
                self.client = chromadb.PersistentClient(path=self.persistence_path)
                self.logger.info(f"Initialized ChromaDB persistent client at: {self.persistence_path}")
            else:
                # 远程服务器模式
                full_host = f"http://{self.host}:{self.port}" if not self.host.startswith("http") else self.host
                
                # 处理认证
                auth_config = self.config.get("auth", {})
                if auth_config:
                    # 如果需要认证，可以在这里添加认证逻辑
                    pass
                
                self.client = chromadb.HttpClient(host=full_host)
                self.logger.info(f"Initialized ChromaDB HTTP client at: {full_host}")
                
        except ImportError as e:
            self.logger.error(f"Failed to import ChromaDB: {e}")
            raise ImportError("ChromaDB dependencies not available. Install with: pip install chromadb")
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    def _init_collection(self):
        """初始化或获取 ChromaDB 集合"""
        try:
            # 尝试获取已存在的集合
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                self.logger.info(f"Retrieved existing ChromaDB collection: {self.collection_name}")
            except Exception:
                # 集合不存在，创建新集合
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata=self.metadata_config
                )
                self.logger.info(f"Created new ChromaDB collection: {self.collection_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB collection: {e}")
            raise
    
    def add_documents(self, documents: List[str], embeddings: List[np.ndarray], 
                     doc_ids: List[str]) -> List[str]:
        """
        添加文档到 ChromaDB 集合
        
        Args:
            documents: 文档内容列表
            embeddings: 向量嵌入列表
            doc_ids: 文档ID列表
            
        Returns:
            成功添加的文档ID列表
        """
        try:
            # 转换 embedding 格式（ChromaDB 需要 list 格式）
            embeddings_list = [embedding.tolist() for embedding in embeddings]
            
            # 准备元数据
            metadatas = []
            for i, doc_id in enumerate(doc_ids):
                metadata = {
                    "doc_id": doc_id,
                    "length": len(documents[i]),
                    "added_time": time.time()
                }
                metadatas.append(metadata)
            
            # 添加到 ChromaDB
            self.collection.add(
                embeddings=embeddings_list,
                documents=documents,
                metadatas=metadatas,
                ids=doc_ids
            )
            
            self.logger.info(f"Added {len(documents)} documents to ChromaDB collection")
            return doc_ids
            
        except Exception as e:
            self.logger.error(f"Error adding documents to ChromaDB: {e}")
            return []
    
    def search(self, query_vector: np.ndarray, query_text: str, top_k: int) -> List[str]:
        """
        在 ChromaDB 中执行搜索
        
        Args:
            query_vector: 查询向量
            query_text: 查询文本
            top_k: 返回的文档数量
            
        Returns:
            检索到的文档内容列表
        """
        try:
            print(f"ChromaBackend.search: using top_k = {top_k}")
            
            if self.use_embedding_query:
                # 使用向量查询
                results = self.collection.query(
                    query_embeddings=[query_vector.tolist()],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                # 使用文本查询（如果 ChromaDB 支持内建的 embedding 函数）
                results = self.collection.query(
                    query_texts=[query_text],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
            
            # 提取文档内容
            if results['documents'] and len(results['documents']) > 0:
                documents = results['documents'][0]  # 返回第一个查询的结果
                print(f"ChromaBackend.search: returned {len(documents)} documents")
                return documents
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error executing ChromaDB search: {e}")
            return []
    
    def delete_collection(self):
        """删除当前集合"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.logger.info(f"Deleted ChromaDB collection: {self.collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting ChromaDB collection: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息
        
        Returns:
            包含集合信息的字典
        """
        try:
            return {
                "backend": "chroma",
                "collection_name": self.collection.name,
                "document_count": self.collection.count(),
                "metadata": self.metadata_config,
                "persistence_path": self.persistence_path if hasattr(self, 'persistence_path') else None
            }
        except Exception as e:
            self.logger.error(f"Failed to get ChromaDB collection info: {e}")
            return {"backend": "chroma", "error": str(e)}
    
    def save_config(self, save_path: str) -> bool:
        """
        保存 ChromaDB 配置信息
        
        Args:
            save_path: 保存路径
            
        Returns:
            是否保存成功
        """
        try:
            os.makedirs(save_path, exist_ok=True)
            
            # ChromaDB 本身会处理持久化，这里只需要保存配置信息
            config_path = os.path.join(save_path, "chroma_config.json")
            config_info = {
                "collection_name": self.collection.name,
                "collection_count": self.collection.count(),
                "backend_type": "chroma",
                "chroma_config": self.config,
                "saved_time": time.time()
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_info, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Successfully saved ChromaDB config to: {save_path}")
            self.logger.info(f"ChromaDB collection '{self.collection.name}' contains {config_info['collection_count']} documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save ChromaDB config: {e}")
            return False
    
    def load_config(self, load_path: str) -> bool:
        """
        从配置文件重新连接到 ChromaDB 集合
        
        Args:
            load_path: 配置文件路径
            
        Returns:
            是否加载成功
        """
        try:
            config_path = os.path.join(load_path, "chroma_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_info = json.load(f)
                
                collection_name = config_info.get("collection_name")
                if collection_name:
                    # 尝试连接到已存在的集合
                    self.collection = self.client.get_collection(name=collection_name)
                    self.collection_name = collection_name
                    self.logger.info(f"Successfully connected to ChromaDB collection: {collection_name}")
                    self.logger.info(f"Collection contains {self.collection.count()} documents")
                    return True
                else:
                    self.logger.error("No collection name found in config")
                    return False
            else:
                self.logger.error(f"ChromaDB config not found at: {config_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to load ChromaDB config: {e}")
            return False
    
    def load_knowledge_from_file(self, file_path: str, embedding_model) -> bool:
        """
        从文件加载知识库到 ChromaDB
        
        Args:
            file_path: 知识库文件路径
            embedding_model: 嵌入模型实例
            
        Returns:
            是否加载成功
        """
        try:
            self.logger.info(f"Loading knowledge from file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 将知识库按段落分割
            documents = [doc.strip() for doc in content.split('\n\n') if doc.strip()]
            
            if documents:
                # 生成文档ID
                doc_ids = [f"doc_{int(time.time() * 1000)}_{i}" for i in range(len(documents))]
                
                # 生成 embedding
                embeddings = []
                for doc in documents:
                    embedding = embedding_model.embed(doc)
                    embeddings.append(np.array(embedding, dtype=np.float32))
                
                # 添加到 ChromaDB
                added_ids = self.add_documents(documents, embeddings, doc_ids)
                
                if added_ids:
                    self.logger.info(f"Loaded {len(added_ids)} documents from {file_path}")
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
        """
        清空集合中的所有文档
        
        Returns:
            是否清空成功
        """
        try:
            # 获取所有文档ID
            all_docs = self.collection.get()
            if all_docs['ids']:
                # 删除所有文档
                self.collection.delete(ids=all_docs['ids'])
                self.logger.info(f"Cleared {len(all_docs['ids'])} documents from collection")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear collection: {e}")
            return False
    
    def update_document(self, doc_id: str, new_content: str, new_embedding: np.ndarray) -> bool:
        """
        更新指定文档
        
        Args:
            doc_id: 文档ID
            new_content: 新的文档内容
            new_embedding: 新的向量嵌入
            
        Returns:
            是否更新成功
        """
        try:
            # ChromaDB 的 update 方法
            self.collection.update(
                ids=[doc_id],
                documents=[new_content],
                embeddings=[new_embedding.tolist()],
                metadatas=[{
                    "doc_id": doc_id,
                    "length": len(new_content),
                    "updated_time": time.time()
                }]
            )
            
            self.logger.info(f"Updated document: {doc_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """
        删除指定文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        try:
            self.collection.delete(ids=[doc_id])
            self.logger.info(f"Deleted document: {doc_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete document {doc_id}: {e}")
            return False


class ChromaUtils:
    """ChromaDB 工具类，提供常用的辅助方法"""
    
    @staticmethod
    def create_chroma_config(persistence_path: str = "./chroma_db",
                           collection_name: str = "default_collection",
                           distance_metric: str = "cosine",
                           host: str = "localhost",
                           port: int = 8000) -> Dict[str, Any]:
        """
        创建标准的 ChromaDB 配置
        
        Args:
            persistence_path: 持久化路径
            collection_name: 集合名称
            distance_metric: 距离度量方法
            host: 服务器地址
            port: 服务器端口
            
        Returns:
            ChromaDB 配置字典
        """
        return {
            "host": host,
            "port": port,
            "persistence_path": persistence_path,
            "collection_name": collection_name,
            "use_embedding_query": True,
            "metadata": {
                "hnsw:space": distance_metric,
                "hnsw:M": 16,
                "hnsw:ef_construction": 200,
                "hnsw:ef": 10
            }
        }
    
    @staticmethod
    def validate_chroma_config(config: Dict[str, Any]) -> bool:
        """
        验证 ChromaDB 配置的有效性
        
        Args:
            config: ChromaDB 配置字典
            
        Returns:
            配置是否有效
        """
        required_keys = ["collection_name"]
        
        for key in required_keys:
            if key not in config:
                return False
        
        # 验证距离度量
        if "metadata" in config and "hnsw:space" in config["metadata"]:
            valid_metrics = ["cosine", "l2", "ip"]
            if config["metadata"]["hnsw:space"] not in valid_metrics:
                return False
        
        return True
    
    @staticmethod
    def check_chromadb_availability() -> bool:
        """
        检查 ChromaDB 是否可用
        
        Returns:
            ChromaDB 是否已安装并可用
        """
        try:
            import chromadb
            return True
        except ImportError:
            return False
