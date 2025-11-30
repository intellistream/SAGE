"""Key-Value Memory Service - 键值对存储

支持三种匹配模式:
1. exact: 精确匹配
2. fuzzy: 模糊匹配 (基于编辑距离)
3. semantic: 语义匹配 (基于向量相似度)

参考实现: LAPS (实体键值存储)
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any, Callable, Literal

import numpy as np

from sage.platform.service import BaseService


def levenshtein_distance(s1: str, s2: str) -> int:
    """计算 Levenshtein 编辑距离"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def fuzzy_similarity(s1: str, s2: str) -> float:
    """计算模糊相似度 (0-1)"""
    distance = levenshtein_distance(s1.lower(), s2.lower())
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    return 1.0 - distance / max_len


class KeyValueMemoryService(BaseService):
    """键值对记忆服务

    支持精确匹配、模糊匹配和语义匹配三种模式。
    """

    def __init__(
        self,
        match_type: Literal["exact", "fuzzy", "semantic"] = "exact",
        key_extractor: Literal["entity", "keyword", "custom"] | Callable = "entity",
        fuzzy_threshold: float = 0.8,
        semantic_threshold: float = 0.7,
        embedding_dim: int = 768,
        case_sensitive: bool = False,
    ):
        """初始化键值记忆服务

        Args:
            match_type: 匹配类型
            key_extractor: 键提取器
            fuzzy_threshold: 模糊匹配阈值
            semantic_threshold: 语义匹配阈值
            embedding_dim: 向量维度
            case_sensitive: 是否区分大小写
        """
        super().__init__()

        self.match_type = match_type
        self.fuzzy_threshold = fuzzy_threshold
        self.semantic_threshold = semantic_threshold
        self.embedding_dim = embedding_dim
        self.case_sensitive = case_sensitive

        # 设置键提取器
        if callable(key_extractor):
            self.key_extractor = key_extractor
        elif key_extractor == "entity":
            self.key_extractor = self._entity_extractor
        elif key_extractor == "keyword":
            self.key_extractor = self._keyword_extractor
        else:
            self.key_extractor = self._default_extractor

        # 键值存储
        self.kv_store: dict[str, dict[str, Any]] = {}

        # 键到条目 ID 的映射 (支持一键多值)
        self.key_to_ids: dict[str, list[str]] = defaultdict(list)

        # 键向量存储 (语义匹配用)
        self.key_embeddings: dict[str, np.ndarray] = {}

        # 值向量存储
        self.value_embeddings: dict[str, np.ndarray] = {}

    def _default_extractor(self, text: str) -> list[str]:
        """默认键提取器"""
        return [text]

    def _entity_extractor(self, text: str) -> list[str]:
        """实体键提取器 (简化版)"""
        # 简单实现：提取大写开头的词和引号内的内容
        import re

        entities = []

        # 提取引号内容
        quoted = re.findall(r'"([^"]+)"', text)
        entities.extend(quoted)

        # 提取大写开头的词
        words = text.split()
        for word in words:
            clean_word = re.sub(r"[^\w]", "", word)
            if clean_word and clean_word[0].isupper():
                entities.append(clean_word)

        return entities if entities else [text]

    def _keyword_extractor(self, text: str) -> list[str]:
        """关键词键提取器"""
        import re

        # 简单分词
        words = re.findall(r"\b\w+\b", text.lower())
        # 过滤停用词
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "of",
            "to",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "and",
            "but",
            "or",
            "nor",
            "so",
            "yet",
            "both",
            "either",
            "neither",
            "not",
            "only",
            "own",
            "same",
            "than",
            "too",
            "very",
            "just",
        }
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords if keywords else [text]

    def insert(
        self,
        entry: str,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
    ) -> str:
        """插入键值对

        Args:
            entry: 值内容
            vector: 值向量
            metadata: 元数据，可包含:
                - key: 显式指定的键
                - keys: 多个键的列表
                - key_vector: 键的向量表示

        Returns:
            entry_id: 条目 ID
        """
        metadata = metadata or {}
        entry_id = metadata.get("id", str(uuid.uuid4()))

        # 获取键
        if "keys" in metadata:
            keys = metadata["keys"]
        elif "key" in metadata:
            keys = [metadata["key"]]
        else:
            keys = self.key_extractor(entry)

        # 标准化键
        if not self.case_sensitive:
            keys = [k.lower() for k in keys]

        # 存储键值对
        self.kv_store[entry_id] = {
            "keys": keys,
            "value": entry,
            "metadata": metadata,
        }

        # 更新键索引
        for key in keys:
            if entry_id not in self.key_to_ids[key]:
                self.key_to_ids[key].append(entry_id)

        # 存储值向量
        if vector is not None:
            self.value_embeddings[entry_id] = np.array(vector, dtype=np.float32)

        # 存储键向量
        if "key_vector" in metadata:
            for key in keys:
                self.key_embeddings[key] = np.array(metadata["key_vector"], dtype=np.float32)

        return entry_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索值

        Args:
            query: 查询键
            vector: 查询向量
            metadata: 查询元数据，可包含:
                - match_type: 覆盖默认匹配类型
                - threshold: 覆盖默认阈值

        Returns:
            检索结果列表
        """
        metadata = metadata or {}
        match_type = metadata.get("match_type", self.match_type)

        if match_type == "exact":
            return self._exact_match(query, top_k)
        elif match_type == "fuzzy":
            threshold = metadata.get("threshold", self.fuzzy_threshold)
            return self._fuzzy_match(query, threshold, top_k)
        elif match_type == "semantic":
            threshold = metadata.get("threshold", self.semantic_threshold)
            return self._semantic_match(query, vector, threshold, top_k)
        else:
            return self._exact_match(query, top_k)

    def _exact_match(
        self,
        query: str | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """精确匹配"""
        if query is None:
            return []

        search_key = query if self.case_sensitive else query.lower()

        results = []
        if search_key in self.key_to_ids:
            entry_ids = self.key_to_ids[search_key]
            for entry_id in entry_ids[:top_k]:
                entry = self.kv_store.get(entry_id, {})
                results.append(
                    {
                        "id": entry_id,
                        "key": search_key,
                        "text": entry.get("value", ""),
                        "score": 1.0,
                        "metadata": entry.get("metadata", {}),
                    }
                )

        return results

    def _fuzzy_match(
        self,
        query: str | None,
        threshold: float,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """模糊匹配"""
        if query is None:
            return []

        search_key = query if self.case_sensitive else query.lower()

        # 计算与所有键的相似度
        matches = []
        for key in self.key_to_ids.keys():
            similarity = fuzzy_similarity(search_key, key)
            if similarity >= threshold:
                matches.append((key, similarity))

        # 按相似度排序
        matches.sort(key=lambda x: x[1], reverse=True)

        # 获取结果
        results = []
        seen_ids = set()

        for key, similarity in matches:
            if len(results) >= top_k:
                break

            for entry_id in self.key_to_ids[key]:
                if entry_id in seen_ids:
                    continue

                seen_ids.add(entry_id)
                entry = self.kv_store.get(entry_id, {})
                results.append(
                    {
                        "id": entry_id,
                        "key": key,
                        "text": entry.get("value", ""),
                        "score": similarity,
                        "metadata": entry.get("metadata", {}),
                    }
                )

                if len(results) >= top_k:
                    break

        return results

    def _semantic_match(
        self,
        query: str | None,
        vector: np.ndarray | None,
        threshold: float,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """语义匹配"""
        if vector is None:
            # 如果没有查询向量，回退到模糊匹配
            return self._fuzzy_match(query, self.fuzzy_threshold, top_k)

        if not self.key_embeddings and not self.value_embeddings:
            return []

        query_vec = np.array(vector, dtype=np.float32)
        if len(query_vec.shape) == 1:
            query_vec = query_vec.reshape(1, -1)

        # 归一化查询向量
        query_norm = query_vec / (np.linalg.norm(query_vec, axis=1, keepdims=True) + 1e-8)

        results = []

        # 与键向量匹配
        if self.key_embeddings:
            keys = list(self.key_embeddings.keys())
            key_embs = np.array([self.key_embeddings[k] for k in keys], dtype=np.float32)
            key_embs_norm = key_embs / (np.linalg.norm(key_embs, axis=1, keepdims=True) + 1e-8)

            key_scores = np.dot(key_embs_norm, query_norm.T).flatten()

            for i, key in enumerate(keys):
                if key_scores[i] >= threshold:
                    for entry_id in self.key_to_ids[key]:
                        entry = self.kv_store.get(entry_id, {})
                        results.append(
                            {
                                "id": entry_id,
                                "key": key,
                                "text": entry.get("value", ""),
                                "score": float(key_scores[i]),
                                "metadata": entry.get("metadata", {}),
                                "match_type": "key",
                            }
                        )

        # 与值向量匹配
        if self.value_embeddings:
            entry_ids = list(self.value_embeddings.keys())
            value_embs = np.array(
                [self.value_embeddings[eid] for eid in entry_ids], dtype=np.float32
            )
            value_embs_norm = value_embs / (
                np.linalg.norm(value_embs, axis=1, keepdims=True) + 1e-8
            )

            value_scores = np.dot(value_embs_norm, query_norm.T).flatten()

            for i, entry_id in enumerate(entry_ids):
                if value_scores[i] >= threshold:
                    entry = self.kv_store.get(entry_id, {})
                    # 检查是否已添加
                    if not any(r["id"] == entry_id for r in results):
                        results.append(
                            {
                                "id": entry_id,
                                "key": entry.get("keys", [""])[0],
                                "text": entry.get("value", ""),
                                "score": float(value_scores[i]),
                                "metadata": entry.get("metadata", {}),
                                "match_type": "value",
                            }
                        )

        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get(self, key: str) -> list[dict[str, Any]]:
        """按键获取值 (精确匹配)"""
        return self._exact_match(key, top_k=100)

    def set(
        self,
        key: str,
        value: str,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
    ) -> str:
        """设置键值对"""
        metadata = metadata or {}
        metadata["key"] = key
        return self.insert(value, vector, metadata)

    def delete(self, key: str) -> int:
        """删除键对应的所有值"""
        search_key = key if self.case_sensitive else key.lower()

        if search_key not in self.key_to_ids:
            return 0

        entry_ids = self.key_to_ids.pop(search_key)
        deleted_count = 0

        for entry_id in entry_ids:
            if entry_id in self.kv_store:
                entry = self.kv_store.pop(entry_id)
                deleted_count += 1

                # 从其他键的索引中删除
                for other_key in entry.get("keys", []):
                    if other_key != search_key and other_key in self.key_to_ids:
                        if entry_id in self.key_to_ids[other_key]:
                            self.key_to_ids[other_key].remove(entry_id)

                # 删除向量
                if entry_id in self.value_embeddings:
                    del self.value_embeddings[entry_id]

        # 删除键向量
        if search_key in self.key_embeddings:
            del self.key_embeddings[search_key]

        return deleted_count

    def update(
        self,
        key: str,
        value: str,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
    ) -> bool:
        """更新键对应的值 (如果存在多个值，只更新第一个)"""
        search_key = key if self.case_sensitive else key.lower()

        if search_key not in self.key_to_ids:
            return False

        entry_ids = self.key_to_ids[search_key]
        if not entry_ids:
            return False

        entry_id = entry_ids[0]
        if entry_id in self.kv_store:
            self.kv_store[entry_id]["value"] = value
            if metadata:
                self.kv_store[entry_id]["metadata"].update(metadata)
            if vector is not None:
                self.value_embeddings[entry_id] = np.array(vector, dtype=np.float32)
            return True

        return False

    def get_all_keys(self) -> list[str]:
        """获取所有键"""
        return list(self.key_to_ids.keys())

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_entries": len(self.kv_store),
            "total_keys": len(self.key_to_ids),
            "key_embeddings_count": len(self.key_embeddings),
            "value_embeddings_count": len(self.value_embeddings),
            "match_type": self.match_type,
        }


if __name__ == "__main__":

    def test_key_value_memory():
        print("\n" + "=" * 70)
        print("KeyValueMemoryService 测试")
        print("=" * 70 + "\n")

        # 创建服务
        service = KeyValueMemoryService(
            match_type="fuzzy",
            key_extractor="entity",
            fuzzy_threshold=0.6,
        )

        # 插入数据
        service.set("Python", "Python 是一种高级编程语言")
        service.set("JavaScript", "JavaScript 是一种脚本语言")
        service.set("Java", "Java 是一种面向对象编程语言")

        print(f"统计信息: {service.get_stats()}")
        print(f"所有键: {service.get_all_keys()}")

        # 精确匹配
        print("\n精确匹配 'Python':")
        results = service.retrieve("Python", metadata={"match_type": "exact"})
        for r in results:
            print(f"  - {r['key']}: {r['text']} (score: {r['score']:.4f})")

        # 模糊匹配
        print("\n模糊匹配 'Pythn' (拼写错误):")
        results = service.retrieve("Pythn", metadata={"match_type": "fuzzy"})
        for r in results:
            print(f"  - {r['key']}: {r['text']} (score: {r['score']:.4f})")

        # 语义匹配
        print("\n语义匹配 (使用随机向量):")
        query_vec = np.random.randn(768).astype(np.float32)
        service.set(
            "ML",
            "机器学习是 AI 的一个分支",
            vector=np.random.randn(768).astype(np.float32),
        )
        results = service.retrieve(
            "ML",
            vector=query_vec,
            metadata={"match_type": "semantic", "threshold": 0.0},
        )
        for r in results:
            print(f"  - {r['key']}: {r['text']} (score: {r['score']:.4f})")

        print("\n✅ 测试完成!")

    test_key_value_memory()
