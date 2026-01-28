"""
Workload 4 - Semantic Join 和窗口管理

实现 60s 大窗口的双流语义 Join，这是 Workload 4 的核心挑战。

关键性能指标:
- 40 queries/s × 1500 docs × 1024 dim = 61.4M ops/s
- 窗口大小: 60s
- 相似度阈值: 0.7
- 并行度: 16

优化策略:
1. NumPy 矩阵运算批量计算相似度
2. 预归一化 embedding，避免重复计算
3. 阈值剪枝早期过滤
4. 增量更新窗口状态
"""

import time
from typing import Any
import numpy as np
from collections import OrderedDict

from sage.common.core.functions.comap_function import BaseCoMapFunction
from .models import QueryEvent, DocumentEvent, JoinedEvent


class JoinWindowState:
    """
    Join 窗口状态管理。
    
    职责:
    - 维护窗口内的文档缓存（60s）
    - 处理窗口滑动和过期文档清理
    - 高效的批量相似度计算（NumPy 优化）
    
    性能优化:
    - 使用 OrderedDict 按时间顺序存储文档
    - 预归一化 embeddings，避免重复计算
    - 批量矩阵运算 (query @ docs.T)
    - 增量更新 embedding 矩阵
    """
    
    def __init__(
        self,
        window_seconds: int = 60,
        threshold: float = 0.7,
        embedding_dim: int = 1024
    ):
        """
        初始化窗口状态。
        
        Args:
            window_seconds: 窗口大小（秒）
            threshold: 相似度阈值
            embedding_dim: Embedding 维度
        """
        self.window_seconds = window_seconds
        self.threshold = threshold
        self.embedding_dim = embedding_dim
        
        # 文档存储（按时间顺序）
        self._docs: OrderedDict[str, DocumentEvent] = OrderedDict()
        
        # Embedding 矩阵（已归一化）
        self._embeddings: np.ndarray | None = None
        self._doc_ids: list[str] = []
        
        # 统计信息
        self._total_docs_added = 0
        self._total_docs_expired = 0
        self._total_matches = 0
        
        # 性能优化：延迟重建阈值
        self._rebuild_threshold = 100  # 积累 100 个变更后重建矩阵
        self._pending_changes = 0
    
    def add_document(self, doc: DocumentEvent) -> bool:
        """
        添加文档到窗口。
        
        Args:
            doc: 文档事件
            
        Returns:
            是否成功添加
        """
        if doc.embedding is None:
            return False
        
        # 检查 embedding 维度
        if len(doc.embedding) != self.embedding_dim:
            return False
        
        # 添加文档
        self._docs[doc.doc_id] = doc
        self._total_docs_added += 1
        self._pending_changes += 1
        
        # 延迟重建：积累一定变更后才重建矩阵
        if self._pending_changes >= self._rebuild_threshold:
            self._rebuild_embedding_matrix()
        
        return True
    
    def remove_expired(self, current_time: float) -> int:
        """
        移除过期文档（超出窗口时间）。
        
        Args:
            current_time: 当前时间戳
            
        Returns:
            移除的文档数量
        """
        expired_count = 0
        cutoff_time = current_time - self.window_seconds
        
        # OrderedDict 保证按插入顺序迭代
        # 文档按时间顺序插入，所以可以从头开始删除
        expired_ids = []
        for doc_id, doc in self._docs.items():
            if doc.timestamp < cutoff_time:
                expired_ids.append(doc_id)
            else:
                # 后续文档都不会过期（时间递增）
                break
        
        # 批量删除
        for doc_id in expired_ids:
            del self._docs[doc_id]
            expired_count += 1
            self._pending_changes += 1
        
        self._total_docs_expired += expired_count
        
        # 如果删除了较多文档，重建矩阵
        if expired_count > 0:
            self._rebuild_embedding_matrix()
        
        return expired_count
    
    def find_matches(
        self,
        query_embedding: np.ndarray,
        top_k: int | None = None
    ) -> list[tuple[str, float]]:
        """
        批量相似度计算，找到匹配的文档。
        
        使用 NumPy 矩阵运算优化性能：
        scores = query_embedding @ embeddings.T
        
        Args:
            query_embedding: 查询 embedding (已归一化)
            top_k: 返回前 k 个结果（None = 返回所有超过阈值的）
            
        Returns:
            [(doc_id, similarity_score), ...] 按分数降序排列
        """
        # 确保矩阵已构建
        if self._embeddings is None or self._pending_changes > 0:
            self._rebuild_embedding_matrix()
        
        # 空窗口
        if self._embeddings is None or len(self._doc_ids) == 0:
            return []
        
        # 归一化查询 embedding
        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 0:
            query_embedding = query_embedding / query_norm
        
        # 批量余弦相似度计算 (O(N*D) 矩阵乘法)
        similarities = self._batch_similarity(query_embedding, self._embeddings)
        
        # 阈值过滤
        matches = [
            (self._doc_ids[i], float(similarities[i]))
            for i in range(len(similarities))
            if similarities[i] >= self.threshold
        ]
        
        # 按分数降序排列
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Top-K
        if top_k is not None and len(matches) > top_k:
            matches = matches[:top_k]
        
        self._total_matches += len(matches)
        
        return matches
    
    def _rebuild_embedding_matrix(self) -> None:
        """
        重建 embedding 矩阵（增量更新）。
        
        构建归一化的 embedding 矩阵以加速后续相似度计算。
        """
        if len(self._docs) == 0:
            self._embeddings = None
            self._doc_ids = []
            self._pending_changes = 0
            return
        
        # 提取所有 embeddings
        doc_ids = []
        embeddings = []
        
        for doc_id, doc in self._docs.items():
            if doc.embedding is not None:
                doc_ids.append(doc_id)
                embeddings.append(doc.embedding)
        
        if len(embeddings) == 0:
            self._embeddings = None
            self._doc_ids = []
            self._pending_changes = 0
            return
        
        # 转换为 NumPy 数组
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # 归一化（L2 norm）
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # 避免除零
        embeddings_array = embeddings_array / norms
        
        self._embeddings = embeddings_array
        self._doc_ids = doc_ids
        self._pending_changes = 0
    
    def _batch_similarity(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        批量余弦相似度计算（NumPy 优化）。
        
        假设输入已归一化，直接使用点积。
        
        Args:
            query_embedding: (D,) 已归一化
            doc_embeddings: (N, D) 已归一化
            
        Returns:
            similarities: (N,) 相似度分数
        """
        # 矩阵乘法: O(N * D)
        return doc_embeddings @ query_embedding
    
    def get_documents(self, doc_ids: list[str]) -> list[DocumentEvent]:
        """
        根据 doc_id 批量获取文档。
        
        Args:
            doc_ids: 文档 ID 列表
            
        Returns:
            文档列表
        """
        docs = []
        for doc_id in doc_ids:
            if doc_id in self._docs:
                docs.append(self._docs[doc_id])
        return docs
    
    def size(self) -> int:
        """返回窗口内文档数量"""
        return len(self._docs)
    
    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息。
        
        Returns:
            统计字典
        """
        return {
            "window_size": self.size(),
            "total_docs_added": self._total_docs_added,
            "total_docs_expired": self._total_docs_expired,
            "total_matches": self._total_matches,
            "pending_changes": self._pending_changes,
            "embedding_matrix_shape": self._embeddings.shape if self._embeddings is not None else None,
        }


class SemanticJoinOperator(BaseCoMapFunction):
    """
    双流语义 Join 算子。
    
    特点:
    - 60s 大窗口语义匹配
    - 批量相似度计算（NumPy 矩阵运算）
    - 支持阈值过滤
    - 输出 JoinedEvent
    
    处理流程:
    1. 查询流（主流）：
       - 在窗口中查找匹配文档
       - 创建 JoinedEvent
       - 清理过期文档
    
    2. 文档流（辅流）：
       - 添加文档到窗口
       - 不输出（Join 由查询触发）
    
    性能优化:
    - NumPy 矩阵运算批量计算
    - 预归一化避免重复计算
    - 增量窗口更新
    - 阈值剪枝早期过滤
    """
    
    def __init__(
        self,
        window_seconds: int = 60,
        threshold: float = 0.7,
        embedding_dim: int = 1024,
        top_k: int | None = None,
        enable_stats: bool = True,
        **kwargs
    ):
        """
        初始化 Semantic Join 算子。
        
        Args:
            window_seconds: 窗口大小（秒）
            threshold: 相似度阈值
            embedding_dim: Embedding 维度
            top_k: 每个查询返回的最大匹配数（None = 无限制）
            enable_stats: 是否启用统计
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self.window_seconds = window_seconds
        self.threshold = threshold
        self.embedding_dim = embedding_dim
        self.top_k = top_k
        self.enable_stats = enable_stats
        
        # 窗口状态
        self.window_state = JoinWindowState(
            window_seconds=window_seconds,
            threshold=threshold,
            embedding_dim=embedding_dim
        )
        
        # 统计信息
        self._total_queries = 0
        self._total_docs = 0
        self._total_joins = 0
        self._total_empty_joins = 0
        
        # 性能统计
        self._total_join_time = 0.0
        self._total_cleanup_time = 0.0
    
    def open(self, context: Any) -> None:
        """算子初始化"""
        if self.enable_stats:
            print(f"[SemanticJoinOperator] Initialized with window={self.window_seconds}s, "
                  f"threshold={self.threshold}, embedding_dim={self.embedding_dim}")
    
    def map0(self, query: QueryEvent) -> JoinedEvent | None:
        """
        处理查询流（stream 0，主流）。
        
        对每个查询：
        1. 清理过期文档
        2. 在窗口中查找匹配文档
        3. 创建 JoinedEvent
        
        Args:
            query: 查询事件
            
        Returns:
            JoinedEvent 或 None（无匹配时）
        """
        start_time = time.time()
        
        self._total_queries += 1
        current_time = query.timestamp
        
        # 1. 清理过期文档
        cleanup_start = time.time()
        expired_count = self.window_state.remove_expired(current_time)
        cleanup_time = time.time() - cleanup_start
        self._total_cleanup_time += cleanup_time
        
        # 2. 检查 query embedding
        if query.embedding is None:
            if self.enable_stats:
                print(f"[SemanticJoinOperator] Warning: query {query.query_id} has no embedding")
            return None
        
        # 3. 查找匹配文档
        query_embedding = np.array(query.embedding, dtype=np.float32)
        matches = self.window_state.find_matches(query_embedding, top_k=self.top_k)
        
        # 4. 创建 JoinedEvent
        if len(matches) > 0:
            # 获取匹配的文档对象
            matched_doc_ids = [doc_id for doc_id, _ in matches]
            matched_docs = self.window_state.get_documents(matched_doc_ids)
            
            # 计算平均相似度作为 Join 分数
            avg_score = sum(score for _, score in matches) / len(matches)
            
            joined_event = JoinedEvent(
                joined_id=f"{query.query_id}_{current_time}",
                query=query,
                matched_docs=matched_docs,
                join_timestamp=current_time,
                semantic_score=avg_score
            )
            
            self._total_joins += 1
            
            join_time = time.time() - start_time
            self._total_join_time += join_time
            
            if self.enable_stats and self._total_queries % 100 == 0:
                self._print_stats(expired_count, len(matches))
            
            return joined_event
        else:
            # 无匹配
            self._total_empty_joins += 1
            
            if self.enable_stats and self._total_queries % 100 == 0:
                self._print_stats(expired_count, 0)
            
            return None
    
    def map1(self, doc: DocumentEvent) -> None:
        """
        处理文档流（stream 1，辅流）。
        
        将文档添加到窗口，不输出（Join 由查询触发）。
        
        Args:
            doc: 文档事件
        """
        self._total_docs += 1
        
        # 添加到窗口
        success = self.window_state.add_document(doc)
        
        if not success and self.enable_stats:
            print(f"[SemanticJoinOperator] Warning: failed to add doc {doc.doc_id} to window")
    
    def _print_stats(self, expired_count: int, match_count: int) -> None:
        """打印统计信息"""
        window_stats = self.window_state.get_stats()
        avg_join_time = self._total_join_time / max(self._total_queries, 1) * 1000  # ms
        avg_cleanup_time = self._total_cleanup_time / max(self._total_queries, 1) * 1000  # ms
        join_rate = self._total_joins / max(self._total_queries, 1) * 100
        
        print(f"\n[SemanticJoinOperator] Stats after {self._total_queries} queries:")
        print(f"  Window: {window_stats['window_size']} docs (added: {window_stats['total_docs_added']}, "
              f"expired: {window_stats['total_docs_expired']}, just expired: {expired_count})")
        print(f"  Joins: {self._total_joins} successful, {self._total_empty_joins} empty "
              f"({join_rate:.1f}% success rate)")
        print(f"  Last query: {match_count} matches")
        print(f"  Avg join time: {avg_join_time:.2f}ms, avg cleanup time: {avg_cleanup_time:.2f}ms")
        print(f"  Total matches: {window_stats['total_matches']}")
    
    def close(self) -> None:
        """算子关闭，打印最终统计"""
        if self.enable_stats:
            print(f"\n[SemanticJoinOperator] Final Statistics:")
            print(f"  Total queries: {self._total_queries}")
            print(f"  Total docs: {self._total_docs}")
            print(f"  Total joins: {self._total_joins} ({self._total_joins / max(self._total_queries, 1) * 100:.1f}%)")
            print(f"  Total empty joins: {self._total_empty_joins}")
            print(f"  Avg join time: {self._total_join_time / max(self._total_queries, 1) * 1000:.2f}ms")
            
            window_stats = self.window_state.get_stats()
            print(f"  Window stats: {window_stats}")
        
        super().close()


class SimpleJoinOperator(BaseCoMapFunction):
    """
    简化版 Join 算子（用于测试和调试）。
    
    不使用窗口，直接对每对 query-doc 计算相似度。
    适合小规模测试。
    """
    
    def __init__(
        self,
        threshold: float = 0.7,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.threshold = threshold
        self._queries: dict[str, QueryEvent] = {}
        self._docs: dict[str, DocumentEvent] = {}
    
    def map0(self, query: QueryEvent) -> list[JoinedEvent]:
        """处理查询流（stream 0）"""
        self._queries[query.query_id] = query
        
        if query.embedding is None:
            return []
        
        # 与所有文档匹配
        query_emb = np.array(query.embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_emb)
        if query_norm > 0:
            query_emb = query_emb / query_norm
        
        results = []
        for doc in self._docs.values():
            if doc.embedding is not None:
                doc_emb = np.array(doc.embedding, dtype=np.float32)
                doc_norm = np.linalg.norm(doc_emb)
                if doc_norm > 0:
                    doc_emb = doc_emb / doc_norm
                
                similarity = float(np.dot(query_emb, doc_emb))
                
                if similarity >= self.threshold:
                    joined = JoinedEvent(
                        joined_id=f"{query.query_id}_{doc.doc_id}",
                        query=query,
                        matched_docs=[doc],
                        join_timestamp=query.timestamp,
                        semantic_score=similarity
                    )
                    results.append(joined)
        
        return results
    
    def map1(self, doc: DocumentEvent) -> None:
        """处理文档流（stream 1）"""
        self._docs[doc.doc_id] = doc
