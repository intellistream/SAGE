"""Hybrid Memory Service - 多索引混合存储

支持多维向量索引和多路检索融合。
参考实现: EmotionalRAG (双向量索引)

特性:
1. 多索引支持: 语义向量、情感向量、BM25关键词等
2. 融合策略: weighted, rrf (Reciprocal Rank Fusion), learned
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any, Literal

import numpy as np

from sage.platform.service import BaseService


class HybridMemoryService(BaseService):
    """混合记忆服务

    支持多索引和多路检索融合。
    """

    def __init__(
        self,
        indexes: list[dict] | None = None,
        fusion_strategy: Literal["weighted", "rrf", "learned"] = "weighted",
        fusion_weights: list[float] | None = None,
        rrf_k: int = 60,
    ):
        """初始化混合记忆服务

        Args:
            indexes: 索引配置列表，每个配置包含:
                - name: 索引名称
                - type: 索引类型 ("vector" | "bm25" | "keyword")
                - embedding_model: 嵌入模型名称 (vector 类型)
            fusion_strategy: 融合策略
            fusion_weights: 融合权重 (weighted 策略)
            rrf_k: RRF 参数 (rrf 策略)
        """
        super().__init__()

        # 默认索引配置
        default_indexes = [
            {"name": "semantic", "type": "vector", "dim": 768},
            {"name": "keyword", "type": "bm25"},
        ]

        self.index_configs = indexes or default_indexes
        self.fusion_strategy = fusion_strategy
        self.fusion_weights = fusion_weights or [1.0 / len(self.index_configs)] * len(
            self.index_configs
        )
        self.rrf_k = rrf_k

        # 初始化索引存储
        self._init_indexes()

        # 文档存储
        self.documents: dict[str, dict[str, Any]] = {}

    def _init_indexes(self) -> None:
        """初始化索引结构"""
        self.indexes: dict[str, dict] = {}

        for config in self.index_configs:
            index_name = config["name"]
            index_type = config.get("type", "vector")

            if index_type == "vector":
                self.indexes[index_name] = {
                    "type": "vector",
                    "dim": config.get("dim", 768),
                    "embeddings": {},  # doc_id -> embedding
                }
            elif index_type == "bm25":
                self.indexes[index_name] = {
                    "type": "bm25",
                    "corpus": [],  # 文档列表
                    "doc_ids": [],  # 对应的文档 ID
                    "vocab": defaultdict(int),  # 词频
                    "doc_freq": defaultdict(int),  # 文档频率
                    "doc_lengths": {},  # 文档长度
                    "avg_doc_length": 0.0,
                }
            elif index_type == "keyword":
                self.indexes[index_name] = {
                    "type": "keyword",
                    "inverted_index": defaultdict(set),  # keyword -> doc_ids
                    "doc_keywords": {},  # doc_id -> keywords
                }
            else:
                self.indexes[index_name] = {
                    "type": index_type,
                    "data": {},
                }

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[np.ndarray] | dict[str, np.ndarray] | None = None,
        metadata: dict | None = None,
    ) -> str:
        """插入记忆条目

        Args:
            entry: 文本内容
            vector: 向量表示，可以是:
                - 单个向量 (用于第一个向量索引)
                - 向量列表 (按索引顺序)
                - 字典 {index_name: vector}
            metadata: 元数据，可包含:
                - keywords: 关键词列表 (用于 keyword 索引)
                - vectors: 命名向量字典 {index_name: vector}

        Returns:
            doc_id: 文档 ID
        """
        metadata = metadata or {}
        doc_id = metadata.get("id", str(uuid.uuid4()))

        # 存储文档
        self.documents[doc_id] = {
            "content": entry,
            "metadata": metadata,
        }

        # 处理向量
        vectors_dict = self._process_vectors(vector, metadata)

        # 更新各索引
        for index_name, index_data in self.indexes.items():
            index_type = index_data["type"]

            if index_type == "vector":
                if index_name in vectors_dict:
                    vec = np.array(vectors_dict[index_name], dtype=np.float32)
                    index_data["embeddings"][doc_id] = vec
            elif index_type == "bm25":
                self._update_bm25_index(index_name, doc_id, entry)
            elif index_type == "keyword":
                keywords = metadata.get("keywords", [])
                self._update_keyword_index(index_name, doc_id, keywords)

        return doc_id

    def _process_vectors(
        self,
        vector: np.ndarray | list | dict | None,
        metadata: dict,
    ) -> dict[str, np.ndarray]:
        """处理向量参数"""
        vectors_dict = {}

        # 从 metadata 获取命名向量
        if "vectors" in metadata and isinstance(metadata["vectors"], dict):
            vectors_dict.update(metadata["vectors"])

        if vector is None:
            return vectors_dict

        # 获取向量索引名称列表
        vector_index_names = [
            cfg["name"] for cfg in self.index_configs if cfg.get("type") == "vector"
        ]

        if isinstance(vector, dict):
            vectors_dict.update(vector)
        elif isinstance(vector, list) and len(vector) > 0:
            if isinstance(vector[0], np.ndarray):
                # 向量列表
                for i, vec in enumerate(vector):
                    if i < len(vector_index_names):
                        vectors_dict[vector_index_names[i]] = vec
            else:
                # 可能是单个向量作为列表
                if len(vector_index_names) > 0:
                    vectors_dict[vector_index_names[0]] = np.array(vector)
        elif isinstance(vector, np.ndarray):
            if len(vector_index_names) > 0:
                vectors_dict[vector_index_names[0]] = vector

        return vectors_dict

    def _update_bm25_index(
        self,
        index_name: str,
        doc_id: str,
        text: str,
    ) -> None:
        """更新 BM25 索引"""
        index = self.indexes[index_name]

        # 简单分词
        tokens = self._tokenize(text)

        index["corpus"].append(tokens)
        index["doc_ids"].append(doc_id)
        index["doc_lengths"][doc_id] = len(tokens)

        # 更新词频和文档频率
        seen_terms = set()
        for token in tokens:
            index["vocab"][token] += 1
            if token not in seen_terms:
                index["doc_freq"][token] += 1
                seen_terms.add(token)

        # 更新平均文档长度
        total_length = sum(index["doc_lengths"].values())
        index["avg_doc_length"] = total_length / len(index["doc_lengths"])

    def _update_keyword_index(
        self,
        index_name: str,
        doc_id: str,
        keywords: list[str],
    ) -> None:
        """更新关键词索引"""
        index = self.indexes[index_name]

        index["doc_keywords"][doc_id] = keywords
        for keyword in keywords:
            keyword_lower = keyword.lower()
            index["inverted_index"][keyword_lower].add(doc_id)

    def _tokenize(self, text: str) -> list[str]:
        """简单分词"""
        # 基础分词：按空格和标点分割
        import re

        tokens = re.findall(r"\b\w+\b", text.lower())
        return tokens

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | dict[str, np.ndarray] | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询文本
            vector: 查询向量
            metadata: 查询元数据，可包含:
                - indexes: 要使用的索引列表
                - fusion_weights: 覆盖默认融合权重
            top_k: 返回结果数

        Returns:
            检索结果列表
        """
        metadata = metadata or {}
        indexes_to_use = metadata.get("indexes", list(self.indexes.keys()))
        custom_weights = metadata.get("fusion_weights", self.fusion_weights)

        # 处理查询向量
        query_vectors = self._process_query_vectors(vector, metadata)

        # 各索引检索结果
        index_results: dict[str, list[tuple[str, float]]] = {}

        for index_name in indexes_to_use:
            if index_name not in self.indexes:
                continue

            index_data = self.indexes[index_name]
            index_type = index_data["type"]

            if index_type == "vector" and index_name in query_vectors:
                results = self._vector_search(
                    index_name, query_vectors[index_name], top_k * 2
                )
            elif index_type == "bm25" and query:
                results = self._bm25_search(index_name, query, top_k * 2)
            elif index_type == "keyword":
                keywords = metadata.get("keywords", [])
                if query and not keywords:
                    keywords = self._tokenize(query)
                results = self._keyword_search(index_name, keywords, top_k * 2)
            else:
                results = []

            index_results[index_name] = results

        # 融合结果
        fused_results = self._fuse_results(index_results, custom_weights, top_k)

        # 构建最终结果
        final_results = []
        for doc_id, score in fused_results:
            doc = self.documents.get(doc_id, {})
            final_results.append({
                "id": doc_id,
                "text": doc.get("content", ""),
                "score": score,
                "metadata": doc.get("metadata", {}),
            })

        return final_results

    def _process_query_vectors(
        self,
        vector: np.ndarray | dict | None,
        metadata: dict,
    ) -> dict[str, np.ndarray]:
        """处理查询向量"""
        vectors_dict = {}

        if "vectors" in metadata and isinstance(metadata["vectors"], dict):
            vectors_dict.update(metadata["vectors"])

        if vector is None:
            return vectors_dict

        vector_index_names = [
            cfg["name"] for cfg in self.index_configs if cfg.get("type") == "vector"
        ]

        if isinstance(vector, dict):
            vectors_dict.update(vector)
        elif isinstance(vector, np.ndarray):
            if len(vector_index_names) > 0:
                vectors_dict[vector_index_names[0]] = vector

        return vectors_dict

    def _vector_search(
        self,
        index_name: str,
        query_vector: np.ndarray,
        top_k: int,
    ) -> list[tuple[str, float]]:
        """向量检索"""
        index = self.indexes[index_name]
        embeddings = index["embeddings"]

        if not embeddings:
            return []

        query_vec = np.array(query_vector, dtype=np.float32)
        if len(query_vec.shape) == 1:
            query_vec = query_vec.reshape(1, -1)

        doc_ids = list(embeddings.keys())
        emb_matrix = np.array([embeddings[did] for did in doc_ids], dtype=np.float32)

        # 归一化
        query_norm = query_vec / (np.linalg.norm(query_vec, axis=1, keepdims=True) + 1e-8)
        emb_norm = emb_matrix / (np.linalg.norm(emb_matrix, axis=1, keepdims=True) + 1e-8)

        # 余弦相似度
        scores = np.dot(emb_norm, query_norm.T).flatten()

        # 获取 top-k
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = [(doc_ids[idx], float(scores[idx])) for idx in top_indices]
        return results

    def _bm25_search(
        self,
        index_name: str,
        query: str,
        top_k: int,
    ) -> list[tuple[str, float]]:
        """BM25 检索"""
        index = self.indexes[index_name]

        if not index["corpus"]:
            return []

        query_tokens = self._tokenize(query)
        n_docs = len(index["corpus"])
        k1 = 1.5
        b = 0.75
        avg_dl = index["avg_doc_length"]

        scores = []
        for i, (doc_tokens, doc_id) in enumerate(
            zip(index["corpus"], index["doc_ids"])
        ):
            doc_len = len(doc_tokens)
            score = 0.0

            for token in query_tokens:
                if token not in index["doc_freq"]:
                    continue

                df = index["doc_freq"][token]
                tf = doc_tokens.count(token)

                # IDF
                idf = np.log((n_docs - df + 0.5) / (df + 0.5) + 1)

                # TF normalization
                tf_norm = (tf * (k1 + 1)) / (
                    tf + k1 * (1 - b + b * doc_len / avg_dl)
                )

                score += idf * tf_norm

            scores.append((doc_id, score))

        # 排序并返回 top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _keyword_search(
        self,
        index_name: str,
        keywords: list[str],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """关键词检索"""
        index = self.indexes[index_name]
        inverted_index = index["inverted_index"]

        if not keywords:
            return []

        # 计算每个文档的匹配分数
        doc_scores: dict[str, float] = defaultdict(float)

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in inverted_index:
                matching_docs = inverted_index[keyword_lower]
                for doc_id in matching_docs:
                    doc_scores[doc_id] += 1.0

        # 归一化
        max_score = max(doc_scores.values()) if doc_scores else 1.0
        results = [
            (doc_id, score / max_score) for doc_id, score in doc_scores.items()
        ]

        # 排序并返回 top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _fuse_results(
        self,
        index_results: dict[str, list[tuple[str, float]]],
        weights: list[float],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """融合检索结果"""
        if self.fusion_strategy == "weighted":
            return self._weighted_fusion(index_results, weights, top_k)
        elif self.fusion_strategy == "rrf":
            return self._rrf_fusion(index_results, top_k)
        else:
            return self._weighted_fusion(index_results, weights, top_k)

    def _weighted_fusion(
        self,
        index_results: dict[str, list[tuple[str, float]]],
        weights: list[float],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """加权融合"""
        doc_scores: dict[str, float] = defaultdict(float)

        index_names = list(self.indexes.keys())

        for i, index_name in enumerate(index_names):
            if index_name not in index_results:
                continue

            weight = weights[i] if i < len(weights) else 1.0 / len(index_names)
            results = index_results[index_name]

            # 归一化分数
            max_score = max(r[1] for r in results) if results else 1.0
            max_score = max_score if max_score > 0 else 1.0

            for doc_id, score in results:
                normalized_score = score / max_score
                doc_scores[doc_id] += weight * normalized_score

        # 排序
        fused = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return fused[:top_k]

    def _rrf_fusion(
        self,
        index_results: dict[str, list[tuple[str, float]]],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """Reciprocal Rank Fusion"""
        doc_scores: dict[str, float] = defaultdict(float)

        for index_name, results in index_results.items():
            for rank, (doc_id, _) in enumerate(results, start=1):
                doc_scores[doc_id] += 1.0 / (self.rrf_k + rank)

        # 排序
        fused = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return fused[:top_k]

    def add_index(self, config: dict) -> bool:
        """动态添加索引"""
        index_name = config.get("name")
        if not index_name or index_name in self.indexes:
            return False

        self.index_configs.append(config)
        index_type = config.get("type", "vector")

        if index_type == "vector":
            self.indexes[index_name] = {
                "type": "vector",
                "dim": config.get("dim", 768),
                "embeddings": {},
            }
        elif index_type == "bm25":
            self.indexes[index_name] = {
                "type": "bm25",
                "corpus": [],
                "doc_ids": [],
                "vocab": defaultdict(int),
                "doc_freq": defaultdict(int),
                "doc_lengths": {},
                "avg_doc_length": 0.0,
            }
        elif index_type == "keyword":
            self.indexes[index_name] = {
                "type": "keyword",
                "inverted_index": defaultdict(set),
                "doc_keywords": {},
            }

        # 更新融合权重
        self.fusion_weights = [1.0 / len(self.indexes)] * len(self.indexes)

        return True

    def get_index_stats(self) -> dict[str, dict]:
        """获取索引统计信息"""
        stats = {}
        for index_name, index_data in self.indexes.items():
            index_type = index_data["type"]

            if index_type == "vector":
                stats[index_name] = {
                    "type": index_type,
                    "dim": index_data["dim"],
                    "doc_count": len(index_data["embeddings"]),
                }
            elif index_type == "bm25":
                stats[index_name] = {
                    "type": index_type,
                    "doc_count": len(index_data["corpus"]),
                    "vocab_size": len(index_data["vocab"]),
                    "avg_doc_length": index_data["avg_doc_length"],
                }
            elif index_type == "keyword":
                stats[index_name] = {
                    "type": index_type,
                    "doc_count": len(index_data["doc_keywords"]),
                    "keyword_count": len(index_data["inverted_index"]),
                }

        return stats


if __name__ == "__main__":
    def test_hybrid_memory():
        print("\n" + "=" * 70)
        print("HybridMemoryService 测试")
        print("=" * 70 + "\n")

        # 创建服务
        service = HybridMemoryService(
            indexes=[
                {"name": "semantic", "type": "vector", "dim": 128},
                {"name": "emotion", "type": "vector", "dim": 64},
                {"name": "keyword", "type": "keyword"},
            ],
            fusion_strategy="weighted",
            fusion_weights=[0.5, 0.3, 0.2],
        )

        # 插入文档
        for i in range(3):
            semantic_vec = np.random.randn(128).astype(np.float32)
            emotion_vec = np.random.randn(64).astype(np.float32)

            service.insert(
                f"这是第 {i+1} 篇测试文档",
                vector={"semantic": semantic_vec, "emotion": emotion_vec},
                metadata={"keywords": ["测试", f"文档{i+1}"]},
            )
            print(f"插入文档 {i+1}")

        # 打印统计
        stats = service.get_index_stats()
        print(f"\n索引统计: {stats}")

        # 检索测试
        query_vec = np.random.randn(128).astype(np.float32)
        results = service.retrieve(
            query="测试文档",
            vector={"semantic": query_vec},
            top_k=3,
        )
        print(f"\n检索结果: {len(results)} 条")
        for r in results:
            print(f"  - {r['text']} (score: {r['score']:.4f})")

        print("\n✅ 测试完成!")

    test_hybrid_memory()
