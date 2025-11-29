"""Graph Memory Service - 基于图结构的记忆存储

支持两种模式:
1. knowledge_graph: 知识图谱模式 (参考 HippoRAG)
2. link_graph: 链接图模式 (参考 A-mem / Zettelkasten)
"""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from typing import Any, Literal

import numpy as np

from sage.platform.service import BaseService


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    """计算内容的 MD5 哈希 ID"""
    return prefix + hashlib.md5(content.encode()).hexdigest()[:16]


class GraphMemoryService(BaseService):
    """图结构记忆服务"""

    def __init__(
        self,
        graph_type: Literal["knowledge_graph", "link_graph"] = "knowledge_graph",
        node_embedding_dim: int = 768,
        edge_types: list[str] | None = None,
        link_policy: Literal["bidirectional", "directed"] = "bidirectional",
        max_links_per_node: int = 50,
        link_weight_init: float = 1.0,
        synonymy_threshold: float = 0.8,
        damping: float = 0.5,
    ):
        """初始化图记忆服务"""
        super().__init__()

        self.graph_type = graph_type
        self.node_embedding_dim = node_embedding_dim
        self.edge_types = edge_types or ["relation", "synonym", "temporal"]
        self.link_policy = link_policy
        self.max_links_per_node = max_links_per_node
        self.link_weight_init = link_weight_init
        self.synonymy_threshold = synonymy_threshold
        self.damping = damping

        # 核心数据结构
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str], dict[str, Any]] = {}
        self.node_embeddings: dict[str, np.ndarray] = {}

        # 知识图谱专用
        self.triples: list[tuple[str, str, str]] = []
        self.entity_to_chunks: dict[str, set[str]] = defaultdict(set)

        # 链接图专用
        self.node_keywords: dict[str, list[str]] = {}
        self.node_context: dict[str, str] = {}
        self.node_links: dict[str, list[str]] = defaultdict(list)

        # 邻接表
        self.adj_list: dict[str, dict[str, float]] = defaultdict(dict)
        self.inverse_adj_list: dict[str, dict[str, float]] = defaultdict(dict)

    def insert(
        self,
        entry: str,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
    ) -> str:
        """插入记忆条目"""
        metadata = metadata or {}

        if self.graph_type == "knowledge_graph":
            return self._insert_knowledge_graph(entry, vector, metadata)
        else:
            return self._insert_link_graph(entry, vector, metadata)

    def _insert_knowledge_graph(
        self,
        entry: str,
        vector: np.ndarray | None,
        metadata: dict,
    ) -> str:
        """知识图谱模式插入"""
        node_type = metadata.get("node_type", "passage")

        if node_type == "passage":
            node_id = compute_mdhash_id(entry, "chunk-")
            self.nodes[node_id] = {
                "content": entry,
                "type": "passage",
                "metadata": metadata,
            }

            if vector is not None:
                self.node_embeddings[node_id] = np.array(vector, dtype=np.float32)

            triples = metadata.get("triples", [])
            for triple in triples:
                # 支持字典格式和列表/元组格式
                if isinstance(triple, dict):
                    subject = triple.get("head") or triple.get("subject")
                    predicate = triple.get("relation") or triple.get("predicate")
                    obj = triple.get("tail") or triple.get("object")
                elif isinstance(triple, (list, tuple)) and len(triple) >= 3:
                    subject, predicate, obj = triple[0], triple[1], triple[2]
                else:
                    continue
                if subject and predicate and obj:
                    self._add_triple(subject, predicate, obj, node_id)

        elif node_type == "entity":
            node_id = compute_mdhash_id(entry, "entity-")
            self.nodes[node_id] = {
                "content": entry,
                "type": "entity",
                "metadata": metadata,
            }

            if vector is not None:
                self.node_embeddings[node_id] = np.array(vector, dtype=np.float32)

        else:
            node_id = str(uuid.uuid4())
            self.nodes[node_id] = {
                "content": entry,
                "type": node_type,
                "metadata": metadata,
            }

            if vector is not None:
                self.node_embeddings[node_id] = np.array(vector, dtype=np.float32)

        return node_id

    def _add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        chunk_id: str,
    ) -> None:
        """添加三元组"""
        self.triples.append((subject, predicate, obj))

        subject_id = compute_mdhash_id(subject.lower(), "entity-")
        obj_id = compute_mdhash_id(obj.lower(), "entity-")

        if subject_id not in self.nodes:
            self.nodes[subject_id] = {"content": subject, "type": "entity"}
        if obj_id not in self.nodes:
            self.nodes[obj_id] = {"content": obj, "type": "entity"}

        edge_key = (subject_id, obj_id)
        if edge_key not in self.edges:
            self.edges[edge_key] = {
                "type": "relation",
                "predicate": predicate,
                "weight": 1.0,
            }
        else:
            self.edges[edge_key]["weight"] += 1.0

        self.adj_list[subject_id][obj_id] = self.edges[edge_key]["weight"]
        self.inverse_adj_list[obj_id][subject_id] = self.edges[edge_key]["weight"]

        self.entity_to_chunks[subject_id].add(chunk_id)
        self.entity_to_chunks[obj_id].add(chunk_id)

    def _insert_link_graph(
        self,
        entry: str,
        vector: np.ndarray | None,
        metadata: dict,
    ) -> str:
        """链接图模式插入"""
        node_id = metadata.get("id", str(uuid.uuid4()))

        self.nodes[node_id] = {
            "content": entry,
            "type": "memory",
            "metadata": metadata,
        }

        if vector is not None:
            self.node_embeddings[node_id] = np.array(vector, dtype=np.float32)

        self.node_keywords[node_id] = metadata.get("keywords", [])
        self.node_context[node_id] = metadata.get("context", "")

        links = metadata.get("links", [])
        for link_id in links:
            if link_id in self.nodes:
                self._create_link(node_id, link_id)

        return node_id

    def _create_link(
        self,
        src_id: str,
        dst_id: str,
        weight: float | None = None,
    ) -> None:
        """创建链接"""
        if weight is None:
            weight = self.link_weight_init

        if len(self.node_links[src_id]) >= self.max_links_per_node:
            return

        edge_key = (src_id, dst_id)
        self.edges[edge_key] = {
            "type": "link",
            "weight": weight,
        }

        self.adj_list[src_id][dst_id] = weight
        self.node_links[src_id].append(dst_id)

        if self.link_policy == "bidirectional":
            reverse_key = (dst_id, src_id)
            if reverse_key not in self.edges:
                self.edges[reverse_key] = {
                    "type": "link",
                    "weight": weight,
                }
                self.adj_list[dst_id][src_id] = weight
                self.node_links[dst_id].append(src_id)

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索相关记忆"""
        metadata = metadata or {}

        if self.graph_type == "knowledge_graph":
            return self._retrieve_knowledge_graph(query, vector, metadata, top_k)
        else:
            return self._retrieve_link_graph(query, vector, metadata, top_k)

    def _retrieve_knowledge_graph(
        self,
        query: str | None,
        vector: np.ndarray | None,
        metadata: dict,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """知识图谱检索"""
        method = metadata.get("method", "ppr")

        if method == "knn" and vector is not None:
            return self._knn_retrieve(vector, top_k)
        elif method == "ppr":
            seed_nodes = metadata.get("seed_nodes", [])

            if not seed_nodes and vector is not None:
                knn_results = self._knn_retrieve(vector, min(5, top_k))
                seed_nodes = [r.get("node_id") for r in knn_results if r.get("node_id")]

            if seed_nodes:
                return self._ppr_retrieve(seed_nodes, top_k)
            else:
                return self._knn_retrieve(vector, top_k) if vector is not None else []
        else:
            return self._knn_retrieve(vector, top_k) if vector is not None else []

    def _knn_retrieve(
        self,
        vector: np.ndarray,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """KNN 向量检索"""
        if not self.node_embeddings:
            return []

        query_vec = np.array(vector, dtype=np.float32)
        if len(query_vec.shape) == 1:
            query_vec = query_vec.reshape(1, -1)

        node_ids = list(self.node_embeddings.keys())
        embeddings = np.array(
            [self.node_embeddings[nid] for nid in node_ids], dtype=np.float32
        )

        if len(embeddings) == 0:
            return []

        query_norm = query_vec / (np.linalg.norm(query_vec, axis=1, keepdims=True) + 1e-8)
        emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)

        scores = np.dot(emb_norm, query_norm.T).flatten()

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            node_id = node_ids[idx]
            node_data = self.nodes.get(node_id, {})
            results.append({
                "text": node_data.get("content", ""),
                "node_id": node_id,
                "score": float(scores[idx]),
                "metadata": node_data.get("metadata", {}),
            })

        return results

    def _ppr_retrieve(
        self,
        seed_nodes: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Personalized PageRank 检索"""
        if not self.nodes:
            return []

        node_ids = list(self.nodes.keys())
        node_to_idx = {nid: idx for idx, nid in enumerate(node_ids)}
        n = len(node_ids)

        if n == 0:
            return []

        reset_prob = np.zeros(n)
        valid_seeds = [nid for nid in seed_nodes if nid in node_to_idx]

        if not valid_seeds:
            return []

        for seed_id in valid_seeds:
            idx = node_to_idx[seed_id]
            reset_prob[idx] = 1.0 / len(valid_seeds)

        transition_matrix = np.zeros((n, n))
        for src_id, neighbors in self.adj_list.items():
            if src_id not in node_to_idx:
                continue
            src_idx = node_to_idx[src_id]
            total_weight = sum(neighbors.values())
            if total_weight > 0:
                for dst_id, weight in neighbors.items():
                    if dst_id in node_to_idx:
                        dst_idx = node_to_idx[dst_id]
                        transition_matrix[dst_idx, src_idx] = weight / total_weight

        dangling = np.where(transition_matrix.sum(axis=0) == 0)[0]
        for idx in dangling:
            transition_matrix[:, idx] = 1.0 / n

        ppr_scores = reset_prob.copy()
        for _ in range(50):
            new_scores = (
                (1 - self.damping) * reset_prob + self.damping * transition_matrix @ ppr_scores
            )
            if np.abs(new_scores - ppr_scores).sum() < 1e-6:
                break
            ppr_scores = new_scores

        passage_scores = []
        for idx, node_id in enumerate(node_ids):
            node_data = self.nodes.get(node_id, {})
            if node_data.get("type") == "passage":
                passage_scores.append((node_id, ppr_scores[idx]))

        passage_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for node_id, score in passage_scores[:top_k]:
            node_data = self.nodes.get(node_id, {})
            results.append({
                "text": node_data.get("content", ""),
                "node_id": node_id,
                "score": float(score),
                "metadata": node_data.get("metadata", {}),
            })

        return results

    def _retrieve_link_graph(
        self,
        query: str | None,
        vector: np.ndarray | None,
        metadata: dict,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """链接图检索"""
        method = metadata.get("method", "knn")

        if vector is not None:
            initial_results = self._knn_retrieve(vector, min(5, top_k))
        else:
            initial_results = []

        if method == "expand":
            expand_depth = metadata.get("expand_depth", 1)
            expanded_results = self._expand_links(initial_results, expand_depth, top_k)
            return expanded_results
        else:
            return initial_results[:top_k]

    def _expand_links(
        self,
        initial_results: list[dict],
        depth: int,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """扩展链接检索"""
        visited = set()
        results = []

        for r in initial_results:
            node_id = r.get("node_id")
            if node_id and node_id not in visited:
                visited.add(node_id)
                results.append(r)

        current_level = [r.get("node_id") for r in initial_results if r.get("node_id")]

        for _ in range(depth):
            next_level = []
            for node_id in current_level:
                neighbors = self.node_links.get(node_id, [])
                for neighbor_id in neighbors:
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_level.append(neighbor_id)

                        node_data = self.nodes.get(neighbor_id, {})
                        results.append({
                            "text": node_data.get("content", ""),
                            "node_id": neighbor_id,
                            "score": 0.5,
                            "metadata": node_data.get("metadata", {}),
                        })

            current_level = next_level

            if len(results) >= top_k:
                break

        return results[:top_k]

    def add_synonymy_edges(self, similarity_threshold: float | None = None) -> int:
        """添加同义边 (knowledge_graph 专用)"""
        if self.graph_type != "knowledge_graph":
            return 0

        threshold = similarity_threshold or self.synonymy_threshold

        entity_nodes = [
            (nid, data)
            for nid, data in self.nodes.items()
            if data.get("type") == "entity" and nid in self.node_embeddings
        ]

        if len(entity_nodes) < 2:
            return 0

        node_ids = [nid for nid, _ in entity_nodes]
        embeddings = np.array(
            [self.node_embeddings[nid] for nid in node_ids], dtype=np.float32
        )

        embeddings = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)

        similarity_matrix = np.dot(embeddings, embeddings.T)

        num_edges = 0
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                if similarity_matrix[i, j] >= threshold:
                    src_id, dst_id = node_ids[i], node_ids[j]
                    edge_key = (src_id, dst_id)

                    if edge_key not in self.edges:
                        self.edges[edge_key] = {
                            "type": "synonym",
                            "weight": float(similarity_matrix[i, j]),
                        }
                        self.adj_list[src_id][dst_id] = float(similarity_matrix[i, j])
                        self.inverse_adj_list[dst_id][src_id] = float(similarity_matrix[i, j])
                        num_edges += 1

                    reverse_key = (dst_id, src_id)
                    if reverse_key not in self.edges:
                        self.edges[reverse_key] = {
                            "type": "synonym",
                            "weight": float(similarity_matrix[i, j]),
                        }
                        self.adj_list[dst_id][src_id] = float(similarity_matrix[i, j])
                        self.inverse_adj_list[src_id][dst_id] = float(similarity_matrix[i, j])
                        num_edges += 1

        return num_edges

    def strengthen_link(self, src_id: str, dst_id: str, delta: float = 0.1) -> bool:
        """增强链接权重 (link_graph 专用)"""
        if self.graph_type != "link_graph":
            return False

        edge_key = (src_id, dst_id)
        if edge_key in self.edges:
            self.edges[edge_key]["weight"] += delta
            self.adj_list[src_id][dst_id] += delta
            return True
        return False

    def get_neighbors(self, node_id: str, edge_type: str | None = None) -> list[str]:
        """获取节点的邻居"""
        neighbors = []
        for (src, dst), edge_data in self.edges.items():
            if src == node_id:
                if edge_type is None or edge_data.get("type") == edge_type:
                    neighbors.append(dst)
        return neighbors

    def get_graph_info(self) -> dict:
        """获取图统计信息"""
        entity_nodes = sum(1 for n in self.nodes.values() if n.get("type") == "entity")
        passage_nodes = sum(1 for n in self.nodes.values() if n.get("type") == "passage")
        memory_nodes = sum(1 for n in self.nodes.values() if n.get("type") == "memory")

        edge_types_count: dict[str, int] = defaultdict(int)
        for edge_data in self.edges.values():
            edge_types_count[edge_data.get("type", "unknown")] += 1

        return {
            "graph_type": self.graph_type,
            "total_nodes": len(self.nodes),
            "entity_nodes": entity_nodes,
            "passage_nodes": passage_nodes,
            "memory_nodes": memory_nodes,
            "total_edges": len(self.edges),
            "edge_types": dict(edge_types_count),
            "total_triples": len(self.triples),
        }


if __name__ == "__main__":
    def test_graph_memory():
        print("\n" + "=" * 70)
        print("GraphMemoryService 测试")
        print("=" * 70 + "\n")

        # 知识图谱模式
        kg_service = GraphMemoryService(graph_type="knowledge_graph")
        doc_vec = np.random.randn(768).astype(np.float32)
        kg_service.insert(
            "机器学习是人工智能的分支",
            vector=doc_vec,
            metadata={
                "node_type": "passage",
                "triples": [("机器学习", "是", "人工智能分支")],
            },
        )
        print(f"KG info: {kg_service.get_graph_info()}")

        # 链接图模式
        lg_service = GraphMemoryService(graph_type="link_graph")
        mem_vec = np.random.randn(768).astype(np.float32)
        lg_service.insert(
            "今天学习了编程",
            vector=mem_vec,
            metadata={"id": "mem_001", "keywords": ["编程", "学习"]},
        )
        print(f"LG info: {lg_service.get_graph_info()}")

        print("\n✅ 测试完成!")

    test_graph_memory()
