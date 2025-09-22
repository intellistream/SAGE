"""
VDB Service - 向量数据库微服务
提供向量存储和相似性搜索功能的服务任务，集成到SAGE DAG中
使用嵌入式FAISS引擎，不依赖外部数据库
"""
from typing import Dict, Any, Optional, List, Union, Tuple, TYPE_CHECKING
from dataclasses import dataclass
import numpy as np
import logging
import time
import uuid

from sage.core.api.service.base_service import BaseService

if TYPE_CHECKING:
    from sage.core.factory.service_factory import ServiceFactory
    from sage.kernel import ServiceContext


@dataclass
class VDBConfig:
    """VDB服务配置"""
    embedding_dimension: int = 384
    index_type: str = "IndexFlatL2"  # FAISS索引类型
    max_vectors: int = 1000000
    similarity_threshold: float = 0.8
    # FAISS索引配置
    faiss_config: Dict[str, Any] = None


@dataclass
class VectorDocument:
    """向量文档"""
    id: str
    vector: List[float]
    metadata: Dict[str, Any]
    text: Optional[str] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class FaissVDBBackend:
    """基于FAISS的向量数据库后端"""
    
    def __init__(self, embedding_dimension: int = 384, index_type: str = "IndexFlatL2", 
                 faiss_config: Optional[Dict[str, Any]] = None):
        self.embedding_dimension = embedding_dimension
        self.index_type = index_type
        self.faiss_config = faiss_config or {}
        self.logger = logging.getLogger(__name__)
        
        # 导入FaissIndex
        try:
            from sage.middleware.services.vdb.search_engine.faiss_index import FaissIndex

            # 初始化FAISS索引（使用我们内部的 FaissIndex 实现）
            self.faiss_index = FaissIndex(
                name="vdb_index",
                dim=embedding_dimension,
                config={
                    "index_type": index_type,
                    **self.faiss_config,
                },
            )

            # 文档存储 (id -> VectorDocument)
            self.documents: Dict[str, VectorDocument] = {}

            self.logger.info(
                f"FaissVDBBackend initialized with {index_type}, dim={embedding_dimension}"
            )

        except ImportError as e:
            self.logger.error(f"Failed to import FaissIndex: {e}")
            raise ImportError("FAISS dependencies not available. Install with: pip install faiss-cpu")
    
    def add_vectors(self, vectors: List[VectorDocument]) -> List[str]:
        """添加向量文档"""
        try:
            if not vectors:
                return []
            
            # 准备向量和ID
            vector_arrays = []
            vector_ids = []
            
            for doc in vectors:
                # 如果没有ID，生成一个
                if not doc.id:
                    doc.id = str(uuid.uuid4())
                
                # 验证向量维度
                if len(doc.vector) != self.embedding_dimension:
                    self.logger.warning(f"Vector dimension mismatch: expected {self.embedding_dimension}, got {len(doc.vector)}")
                    continue
                
                vector_arrays.append(np.array(doc.vector, dtype=np.float32))
                vector_ids.append(doc.id)
                
                # 存储文档
                self.documents[doc.id] = doc
            
            if vector_arrays:
                # 添加到FAISS索引（使用 batch_insert 接口）
                self.faiss_index.batch_insert(vector_arrays, vector_ids)

                self.logger.debug(f"Added {len(vector_ids)} vectors to FAISS index")
                return vector_ids
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error adding vectors: {e}")
            return []
    
    def search_vectors(self, query_vector: List[float], top_k: int = 5,
                      metadata_filter: Optional[Dict[str, Any]] = None) -> List[Tuple[VectorDocument, float]]:
        """搜索相似向量"""
        try:
            if len(query_vector) != self.embedding_dimension:
                raise ValueError(
                    f"Query vector dimension mismatch: expected {self.embedding_dimension}, got {len(query_vector)}"
                )

            # 转换查询向量（FaissIndex.search 接受 1D np.ndarray）
            query_np = np.array(query_vector, dtype=np.float32)

            # 在FAISS中搜索（返回 string_ids 和 distances）
            ids, distances = self.faiss_index.search(query_np, top_k)

            results: List[Tuple[VectorDocument, float]] = []
            for doc_id, distance in zip(ids, distances):
                if doc_id in self.documents:
                    doc = self.documents[doc_id]

                    # 应用元数据过滤
                    if metadata_filter and not self._matches_filter(doc.metadata, metadata_filter):
                        continue

                    results.append((doc, float(distance)))
                else:
                    self.logger.warning(
                        f"Document {doc_id} found in index but not in storage"
                    )

            self.logger.debug(f"Search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching vectors: {e}")
            return []
    
    def get_vector(self, doc_id: str) -> Optional[VectorDocument]:
        """获取向量文档"""
        return self.documents.get(doc_id)
    
    def delete_vectors(self, doc_ids: List[str]) -> int:
        """删除向量文档"""
        try:
            deleted_count = 0

            for doc_id in doc_ids:
                if doc_id in self.documents:
                    del self.documents[doc_id]
                    try:
                        # 从FAISS索引中删除（逐个删除）
                        self.faiss_index.delete(doc_id)
                    except Exception as e:
                        self.logger.warning(
                            f"Error deleting id {doc_id} from FAISS: {e}"
                        )
                    deleted_count += 1
            
            self.logger.debug(f"Deleted {deleted_count} vectors")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error deleting vectors: {e}")
            return 0
    
    def list_vectors(self, metadata_filter: Optional[Dict[str, Any]] = None) -> List[VectorDocument]:
        """列出向量文档"""
        if metadata_filter is None:
            return list(self.documents.values())
        
        return [doc for doc in self.documents.values() 
                if self._matches_filter(doc.metadata, metadata_filter)]
    
    def count(self) -> int:
        """获取向量数量"""
        return len(self.documents)
    
    def clear(self) -> None:
        """清空所有向量"""
        self.documents.clear()
        # 重新初始化FAISS索引
        try:
            from sage.middleware.services.vdb.search_engine.faiss_index import FaissIndex
            self.faiss_index = FaissIndex(
                name="vdb_index",
                dim=self.embedding_dimension,
                config={
                    "index_type": self.index_type,
                    **self.faiss_config,
                },
            )
        except Exception as e:
            self.logger.error(f"Error reinitializing FAISS index: {e}")
    
    def save_index(self, path: str) -> bool:
        """保存索引到磁盘"""
        try:
            self.faiss_index.store(path)
            return True
        except Exception as e:
            self.logger.error(f"Error saving index: {e}")
            return False
    
    def load_index(self, path: str) -> bool:
        """从磁盘加载索引"""
        try:
            from sage.middleware.services.vdb.search_engine.faiss_index import FaissIndex
            # 使用类方法 load 恢复索引
            self.faiss_index = FaissIndex.load(name="vdb_index", load_path=path)
            return True
        except Exception as e:
            self.logger.error(f"Error loading index: {e}")
            return False
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """检查元数据是否匹配过滤条件"""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            return {
                "total_vectors": self.count(),
                "index_type": self.index_type,
                "embedding_dimension": self.embedding_dimension,
                "faiss_index_ntotal": getattr(self.faiss_index.index, 'ntotal', 0) if self.faiss_index.index else 0,
                "max_vectors": getattr(self, 'max_vectors', -1)
            }
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}


class VDBService(BaseService):
    """
    VDB服务任务
    
    提供向量存储和相似性搜索功能，可以在SAGE DAG中作为服务节点使用
    使用嵌入式FAISS引擎，高性能的本地向量检索
    """
    
    def __init__(self, service_factory: 'ServiceFactory', ctx: 'ServiceContext' = None):
        super().__init__(service_factory, ctx)
        
        # 从service_factory获取配置
        self.config: VDBConfig = getattr(service_factory, 'config', VDBConfig())
        
        # 初始化FAISS后端
        self.backend = FaissVDBBackend(
            embedding_dimension=self.config.embedding_dimension,
            index_type=self.config.index_type,
            faiss_config=self.config.faiss_config or {}
        )
        
        self.logger.info(f"VDB Service '{self.service_name}' initialized with FAISS backend")
        self.logger.info(f"Index type: {self.config.index_type}, Dimension: {self.config.embedding_dimension}")
    
    def _start_service_instance(self):
        """启动VDB服务实例"""
        self.logger.info(f"VDB Service '{self.service_name}' started")
    
    def _stop_service_instance(self):
        """停止VDB服务实例"""
        self.logger.info(f"VDB Service '{self.service_name}' stopped")
    
    # VDB操作方法 - 这些方法可以通过服务调用机制被调用
    
    def add_vectors(self, vectors: List[Dict[str, Any]]) -> List[str]:
        """添加向量文档"""
        self.logger.debug(f"Adding {len(vectors)} vectors")
        
        # 转换输入格式
        docs = []
        for v in vectors:
            doc = VectorDocument(
                id=v.get('id', ''),
                vector=v['vector'],
                metadata=v.get('metadata', {}),
                text=v.get('text')
            )
            docs.append(doc)
        
        result = self.backend.add_vectors(docs)
        self.logger.debug(f"Added {len(result)} vectors successfully")
        return result
    
    def search_vectors(self, query_vector: List[float], top_k: int = 5,
                      metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        self.logger.debug(f"Searching vectors with top_k={top_k}")
        
        results = self.backend.search_vectors(query_vector, top_k, metadata_filter)
        
        # 转换输出格式
        formatted_results = []
        for doc, distance in results:
            formatted_results.append({
                'id': doc.id,
                'vector': doc.vector,
                'metadata': doc.metadata,
                'text': doc.text,
                'distance': distance,
                'created_at': doc.created_at
            })
        
        self.logger.debug(f"Search returned {len(formatted_results)} results")
        return formatted_results
    
    def get_vector(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取向量文档"""
        self.logger.debug(f"Getting vector: {doc_id}")
        
        doc = self.backend.get_vector(doc_id)
        if doc:
            return {
                'id': doc.id,
                'vector': doc.vector,
                'metadata': doc.metadata,
                'text': doc.text,
                'created_at': doc.created_at
            }
        return None
    
    def delete_vectors(self, doc_ids: List[str]) -> int:
        """删除向量文档"""
        self.logger.debug(f"Deleting {len(doc_ids)} vectors")
        result = self.backend.delete_vectors(doc_ids)
        self.logger.debug(f"Deleted {result} vectors successfully")
        return result
    
    def list_vectors(self, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """列出向量文档"""
        self.logger.debug("Listing vectors")
        
        docs = self.backend.list_vectors(metadata_filter)
        results = []
        for doc in docs:
            results.append({
                'id': doc.id,
                'vector': doc.vector,
                'metadata': doc.metadata,
                'text': doc.text,
                'created_at': doc.created_at
            })
        
        self.logger.debug(f"Listed {len(results)} vectors")
        return results
    
    def count(self) -> int:
        """获取向量数量"""
        result = self.backend.count()
        self.logger.debug(f"Vector count: {result}")
        return result
    
    def clear(self) -> None:
        """清空所有向量"""
        self.logger.debug("Clearing all vectors")
        self.backend.clear()
    
    def save_index(self, path: str) -> bool:
        """保存索引到磁盘"""
        self.logger.debug(f"Saving index to: {path}")
        return self.backend.save_index(path)
    
    def load_index(self, path: str) -> bool:
        """从磁盘加载索引"""
        self.logger.debug(f"Loading index from: {path}")
        return self.backend.load_index(path)
    
    def stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        base_stats = self.get_statistics()
        vdb_stats = self.backend.get_stats()
        base_stats.update(vdb_stats)
        return base_stats


# 工厂函数，用于在DAG中创建VDB服务
def create_vdb_service_factory(
    service_name: str = "vdb_service",
    embedding_dimension: int = 384,
    index_type: str = "IndexFlatL2",
    max_vectors: int = 1000000,
    similarity_threshold: float = 0.8,
    faiss_config: Optional[Dict[str, Any]] = None
):
    """
    创建VDB服务工厂
    
    Args:
        service_name: 服务名称
        embedding_dimension: 向量维度
        index_type: FAISS索引类型 ("IndexFlatL2", "IndexHNSWFlat", "IndexIVFFlat", etc.)
        max_vectors: 最大向量数量
        similarity_threshold: 相似度阈值
        faiss_config: FAISS索引配置
    
    Returns:
        ServiceFactory: 可以用于注册到环境的服务工厂
    """
    from sage.core.factory.service_factory import ServiceFactory
    
    config = VDBConfig(
        embedding_dimension=embedding_dimension,
        index_type=index_type,
        max_vectors=max_vectors,
        similarity_threshold=similarity_threshold,
        faiss_config=faiss_config or {}
    )
    
    factory = ServiceFactory(service_name, VDBService)
    factory.config = config
    return factory
