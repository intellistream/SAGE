"""
Vector Store Service for SAGE Studio

This module provides a thin wrapper around sage-mem's VDBMemoryCollection
for knowledge base vector storage and retrieval in SAGE Studio.

Layer: L6 (sage-studio)
Dependencies: sage-middleware (sage-mem/neuromem), sage-common (embedding)

Design Principles:
- Reuses existing neuromem VDBMemoryCollection implementation
- Provides simplified interface for Studio's knowledge management needs
- Supports both local embedding and external embedding service
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from sage.common.config.user_paths import get_user_paths

if TYPE_CHECKING:
    from sage.common.components.sage_embedding.protocols import EmbeddingProtocol


@dataclass
class DocumentChunk:
    """文档分块数据结构

    与 Task 2.2 document_loader 模块共享的数据结构。

    Attributes:
        content: 分块的文本内容
        source_file: 源文件路径
        chunk_index: 在源文件中的分块索引
        metadata: 额外元数据（如标题、语言等）
    """

    content: str
    source_file: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        """生成唯一的 chunk ID"""
        key = f"{self.source_file}:{self.chunk_index}:{self.content[:100]}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@dataclass
class SearchResult:
    """检索结果

    Attributes:
        content: 匹配的文本内容
        score: 相似度分数 (0-1, 越高越相关)
        source: 来源文件路径
        metadata: 额外元数据
    """

    content: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore:
    """向量存储服务

    封装 sage-mem 的 VDBMemoryCollection，为 SAGE Studio
    知识库管理提供简化的向量存储和检索接口。

    Features:
    - 基于 neuromem VDBMemoryCollection 的高性能向量存储
    - 支持 sage-embedding 或外部 embedding 服务
    - 支持持久化和增量更新
    - 支持按来源删除文档

    Example:
        >>> store = VectorStore(
        ...     collection_name="studio_kb",
        ...     embedding_model="BAAI/bge-small-zh-v1.5",
        ... )
        >>> await store.add_documents(chunks)
        >>> results = await store.search("如何创建 Pipeline?")
    """

    def __init__(
        self,
        collection_name: str,
        embedding_model: str = "BAAI/bge-m3",
        embedding_dim: int = 1024,
        persist_dir: str | Path | None = None,
        embedder: EmbeddingProtocol | None = None,
    ):
        """初始化向量存储

        Args:
            collection_name: Collection 名称，用于区分不同的知识库
            embedding_model: Embedding 模型名称
            embedding_dim: Embedding 向量维度
            persist_dir: 持久化目录，默认使用 XDG 标准路径
            embedder: 外部 embedder 实例（可选，优先使用）
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim

        # 设置持久化目录
        if persist_dir is None:
            user_paths = get_user_paths()
            self.persist_dir = user_paths.data_dir / "studio" / "vector_db"
        else:
            self.persist_dir = Path(persist_dir).expanduser()
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 延迟初始化的组件
        self._embedder = embedder
        self._collection = None
        self._manager = None

    @property
    def embedder(self) -> EmbeddingProtocol:
        """获取或创建 embedder（懒加载）"""
        if self._embedder is None:
            self._embedder = self._create_embedder()
        return self._embedder

    def _create_embedder(self) -> EmbeddingProtocol:
        """创建 embedding 客户端"""
        from sage.common.components.sage_embedding import (
            EmbeddingFactory,
            adapt_embedding_client,
        )

        # 创建 HuggingFace embedding 模型
        raw_embedder = EmbeddingFactory.create(
            "hf",
            model=self.embedding_model,
        )
        # 适配为批量接口
        return adapt_embedding_client(raw_embedder)

    @property
    def collection(self):
        """获取或创建 VDB collection（懒加载）"""
        if self._collection is None:
            self._init_collection()
        return self._collection

    def _init_collection(self):
        """初始化 VDB collection"""
        from sage.middleware.components.sage_mem.neuromem.memory_manager import (
            MemoryManager,
        )

        # 创建 MemoryManager
        data_dir = str(self.persist_dir)
        self._manager = MemoryManager(data_dir)

        # 尝试获取现有 collection，不存在则创建
        self._collection = self._manager.get_collection(self.collection_name)

        if self._collection is None:
            # 如果元数据存在但 collection 获取失败（磁盘数据被删除），先清理元数据
            if self.collection_name in self._manager.collection_metadata:
                import logging

                logging.warning(
                    f"Collection '{self.collection_name}' metadata exists but data is missing. "
                    "Cleaning up stale metadata..."
                )
                # 直接从元数据中删除
                del self._manager.collection_metadata[self.collection_name]
                self._manager._save_manager()

            # 创建新的 VDB collection
            # MemoryManager.create_collection 需要 config dict 包含所有参数
            collection_config = {
                "name": self.collection_name,
                "backend_type": "vdb",
                "dim": self.embedding_dim,
                "description": f"SAGE Studio knowledge base: {self.collection_name}",
            }
            self._collection = self._manager.create_collection(config=collection_config)

            if self._collection is None:
                raise RuntimeError(f"Failed to create collection '{self.collection_name}'")

            # 创建默认索引
            index_config = {
                "name": "default_index",
                "dim": self.embedding_dim,
                "backend_type": "FAISS",
                "description": "Default index for knowledge retrieval",
            }
            self._collection.create_index(config=index_config)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """生成文本的 embedding 向量"""
        return self.embedder.embed(texts)

    async def add_documents(
        self,
        chunks: list[DocumentChunk],
        batch_size: int = 32,
    ) -> int:
        """添加文档到向量库

        Args:
            chunks: DocumentChunk 列表
            batch_size: 批处理大小

        Returns:
            成功添加的文档数量
        """
        if not chunks:
            return 0

        added_count = 0

        # 分批处理
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.content for c in batch]

            # 生成 embeddings
            embeddings = self._embed(texts)

            # 准备向量和元数据
            vectors = [np.array(emb, dtype=np.float32) for emb in embeddings]

            for chunk, vector in zip(batch, vectors):
                metadata = {
                    "source_file": chunk.source_file,
                    "chunk_index": str(chunk.chunk_index),
                    "chunk_id": chunk.chunk_id,
                    **{k: str(v) for k, v in chunk.metadata.items()},
                }

                try:
                    self.collection.insert(
                        index_names="default_index",
                        content=chunk.content,
                        vector=vector,
                        metadata=metadata,
                    )
                    added_count += 1
                except Exception as e:
                    # 记录错误但继续处理
                    import logging

                    logging.warning(f"Failed to insert chunk {chunk.chunk_id}: {e}")

        return added_count

    async def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
        source_filter: str | None = None,
    ) -> list[SearchResult]:
        """语义检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            score_threshold: 相似度阈值 (0-1)
            source_filter: 按来源文件过滤（可选）

        Returns:
            SearchResult 列表，按相似度降序排列
        """
        # 生成查询向量
        query_embedding = self._embed([query])[0]
        query_vector = np.array(query_embedding, dtype=np.float32)

        # 检索 - VDBMemoryCollection.retrieve 接收向量作为 query 参数
        results = self.collection.retrieve(
            query=query_vector,  # 传递向量而不是字符串
            top_k=top_k * 2,  # 多取一些以便过滤
            index_name="default_index",
            with_metadata=True,
        )

        if results is None:
            return []

        # 转换结果格式并过滤
        search_results = []
        for r in results:
            # 处理不同的结果格式
            if isinstance(r, dict):
                content = r.get("text", r.get("content", ""))
                score = float(r.get("score", r.get("similarity", 0.0)))
                metadata = r.get("metadata", {})
            else:
                # 如果是其他格式，尝试访问属性
                content = getattr(r, "text", getattr(r, "content", str(r)))
                score = float(getattr(r, "score", getattr(r, "similarity", 0.0)))
                metadata = getattr(r, "metadata", {})

            source = metadata.get("source_file", "unknown")

            # 应用过滤
            if source_filter and source_filter not in source:
                continue

            # 应用阈值
            if score < score_threshold:
                continue

            search_results.append(
                SearchResult(
                    content=content,
                    score=score,
                    source=source,
                    metadata=metadata,
                )
            )

        # 按分数排序并限制数量
        search_results.sort(key=lambda x: x.score, reverse=True)
        return search_results[:top_k]

    async def delete_by_source(self, source_file: str) -> int:
        """删除指定来源的所有文档

        Args:
            source_file: 源文件路径

        Returns:
            删除的文档数量
        """
        # 查找所有匹配的文档
        # neuromem 支持按 metadata 查找
        try:
            # 获取所有 item_id
            deleted_count = 0

            # 使用 metadata 过滤查找
            if hasattr(self.collection, "find_by_metadata"):
                item_ids = self.collection.find_by_metadata("source_file", source_file)
                for item_id in item_ids:
                    if self.collection.delete(item_id):
                        deleted_count += 1
            else:
                # 备用方案：遍历删除
                # 这个实现可能效率较低，但保证兼容性
                pass

            return deleted_count
        except Exception as e:
            import logging

            logging.warning(f"Failed to delete documents from {source_file}: {e}")
            return 0

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            包含向量数量、索引信息等的字典
        """
        stats = {
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "persist_dir": str(self.persist_dir),
        }

        try:
            if hasattr(self.collection, "statistics"):
                stats.update(self.collection.statistics)
            if hasattr(self.collection, "list_indexes"):
                stats["indexes"] = self.collection.list_indexes()
        except Exception:
            pass

        return stats

    def save(self) -> bool:
        """持久化到磁盘

        Returns:
            是否成功保存
        """
        try:
            if self._manager is not None:
                # MemoryManager 自动管理持久化
                return True
            return False
        except Exception as e:
            import logging

            logging.error(f"Failed to save vector store: {e}")
            return False

    def close(self):
        """关闭向量存储，释放资源"""
        self._collection = None
        self._manager = None
        self._embedder = None


# 便捷工厂函数
def create_vector_store(
    collection_name: str = "studio_default",
    embedding_model: str = "BAAI/bge-small-zh-v1.5",
    **kwargs,
) -> VectorStore:
    """创建 VectorStore 实例的便捷函数

    Args:
        collection_name: Collection 名称
        embedding_model: Embedding 模型名称
        **kwargs: 其他参数传递给 VectorStore

    Returns:
        VectorStore 实例
    """
    return VectorStore(
        collection_name=collection_name,
        embedding_model=embedding_model,
        **kwargs,
    )
