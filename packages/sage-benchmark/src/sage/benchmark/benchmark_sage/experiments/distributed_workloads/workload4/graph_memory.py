"""
Workload 4 图遍历和内存检索

实现基于图结构的内存检索，使用 BFS 遍历关联节点。
"""

import logging
import time
from collections import deque
from typing import Any

import networkx as nx
import numpy as np

from sage.common.core.functions.map_function import MapFunction

try:
    from .models import JoinedEvent, GraphMemoryResult
except ImportError:
    from models import JoinedEvent, GraphMemoryResult

logger = logging.getLogger(__name__)


class GraphMemoryService:
    """
    图内存服务。
    
    使用 NetworkX 构建知识图，支持 BFS 遍历和相似度检索。
    
    特点:
    - 节点包含 content 和 embedding
    - 边权重表示相似度
    - BFS 遍历支持 beam search
    - 最大深度和节点数限制
    """
    
    def __init__(
        self,
        config: dict[str, Any],
        embedding_dim: int = 1024,
        similarity_threshold: float = 0.7,
        **kwargs
    ):
        """
        初始化图内存服务。
        
        Args:
            config: 服务配置
            embedding_dim: Embedding 维度
            similarity_threshold: 构图相似度阈值
        """
        self.config = config
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        self.graph: nx.DiGraph | None = None
        self.node_embeddings: dict[str, np.ndarray] = {}
        self.node_contents: dict[str, str] = {}
        self.node_types: dict[str, str] = {}
        
        logger.info(
            f"GraphMemoryService initialized with embedding_dim={embedding_dim}, "
            f"similarity_threshold={similarity_threshold}"
        )
    
    def build_graph(self, knowledge_base: list[dict[str, Any]]) -> None:
        """
        从知识库构建图。
        
        Args:
            knowledge_base: 知识库列表，每个元素包含:
                - node_id: 节点ID
                - content: 内容文本
                - embedding: 向量表示
                - node_type: 节点类型（可选）
        """
        logger.info(f"Building knowledge graph from {len(knowledge_base)} items...")
        start_time = time.time()
        
        self.graph = nx.DiGraph()
        
        # 添加节点
        for item in knowledge_base:
            node_id = item["node_id"]
            content = item["content"]
            embedding = np.array(item["embedding"], dtype=np.float32)
            node_type = item.get("node_type", "memory")
            
            self.graph.add_node(node_id)
            self.node_embeddings[node_id] = embedding
            self.node_contents[node_id] = content
            self.node_types[node_id] = node_type
        
        # 构建边（基于相似度）
        node_ids = list(self.node_embeddings.keys())
        embeddings_matrix = np.array([self.node_embeddings[nid] for nid in node_ids])
        
        # 归一化
        norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
        embeddings_matrix = embeddings_matrix / (norms + 1e-8)
        
        # 计算相似度矩阵
        similarity_matrix = embeddings_matrix @ embeddings_matrix.T
        
        # 添加边
        edge_count = 0
        for i, source_id in enumerate(node_ids):
            for j, target_id in enumerate(node_ids):
                if i != j and similarity_matrix[i, j] >= self.similarity_threshold:
                    weight = float(similarity_matrix[i, j])
                    self.graph.add_edge(source_id, target_id, weight=weight)
                    edge_count += 1
        
        elapsed = time.time() - start_time
        logger.info(
            f"Graph built: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges in {elapsed:.2f}s"
        )
    
    def search(
        self,
        query_embedding: list[float],
        max_depth: int = 3,
        max_nodes: int = 200,
        beam_width: int = 10,
    ) -> list[dict[str, Any]]:
        """
        BFS 图遍历搜索。
        
        Args:
            query_embedding: 查询向量
            max_depth: 最大遍历深度
            max_nodes: 最大返回节点数
            beam_width: Beam search 宽度
        
        Returns:
            遍历结果列表，每个元素包含:
                - node_id: 节点ID
                - content: 内容
                - depth: 深度
                - path: 遍历路径
                - relevance_score: 相关性分数
                - node_type: 节点类型
        """
        if self.graph is None or self.graph.number_of_nodes() == 0:
            logger.warning("Graph is empty, returning empty results")
            return []
        
        query_emb = np.array(query_embedding, dtype=np.float32)
        query_emb = query_emb / (np.linalg.norm(query_emb) + 1e-8)
        
        # 找到起始节点（与查询最相似的节点）
        start_nodes = self._find_top_k_similar_nodes(query_emb, k=beam_width)
        
        if not start_nodes:
            logger.warning("No start nodes found")
            return []
        
        # BFS with beam search
        visited: set[str] = set()
        results: list[dict[str, Any]] = []
        
        # 队列元素: (node_id, depth, path, cumulative_score)
        queue: deque[tuple[str, int, list[str], float]] = deque()
        
        # 初始化队列
        for node_id, score in start_nodes:
            queue.append((node_id, 0, [node_id], score))
        
        while queue and len(results) < max_nodes:
            current_id, depth, path, cum_score = queue.popleft()
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            # 添加到结果
            results.append({
                "node_id": current_id,
                "content": self.node_contents[current_id],
                "depth": depth,
                "path": path.copy(),
                "relevance_score": cum_score,
                "node_type": self.node_types.get(current_id, "memory"),
            })
            
            # 如果未达到最大深度，继续扩展
            if depth < max_depth:
                neighbors = self._get_neighbors_with_scores(current_id, query_emb)
                
                # Beam search: 只保留 top-k 邻居
                top_neighbors = sorted(neighbors, key=lambda x: x[1], reverse=True)[
                    :beam_width
                ]
                
                for neighbor_id, neighbor_score in top_neighbors:
                    if neighbor_id not in visited:
                        new_path = path + [neighbor_id]
                        # 累积分数（平均）
                        new_cum_score = (cum_score * depth + neighbor_score) / (
                            depth + 1
                        )
                        queue.append((neighbor_id, depth + 1, new_path, new_cum_score))
        
        logger.debug(f"Graph search returned {len(results)} nodes")
        return results[:max_nodes]
    
    def _find_top_k_similar_nodes(
        self, query_embedding: np.ndarray, k: int = 10
    ) -> list[tuple[str, float]]:
        """
        找到与查询最相似的 top-k 节点。
        
        Args:
            query_embedding: 查询向量（已归一化）
            k: 返回节点数
        
        Returns:
            [(node_id, score), ...]
        """
        node_ids = list(self.node_embeddings.keys())
        if not node_ids:
            return []
        
        embeddings = np.array([self.node_embeddings[nid] for nid in node_ids])
        
        # 归一化
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / (norms + 1e-8)
        
        # 余弦相似度
        scores = embeddings @ query_embedding
        
        # Top-k
        top_k_indices = np.argsort(scores)[-k:][::-1]
        
        return [(node_ids[i], float(scores[i])) for i in top_k_indices]
    
    def _get_neighbors_with_scores(
        self, node_id: str, query_embedding: np.ndarray
    ) -> list[tuple[str, float]]:
        """
        获取节点的邻居及其与查询的相关性分数。
        
        Args:
            node_id: 当前节点ID
            query_embedding: 查询向量（已归一化）
        
        Returns:
            [(neighbor_id, score), ...]
        """
        if node_id not in self.graph:
            return []
        
        neighbors = list(self.graph.successors(node_id))
        
        if not neighbors:
            return []
        
        # 计算邻居与查询的相似度
        neighbor_embeddings = np.array(
            [self.node_embeddings[nid] for nid in neighbors]
        )
        
        # 归一化
        norms = np.linalg.norm(neighbor_embeddings, axis=1, keepdims=True)
        neighbor_embeddings = neighbor_embeddings / (norms + 1e-8)
        
        # 余弦相似度
        scores = neighbor_embeddings @ query_embedding
        
        # 结合边权重（可选）
        edge_weights = [
            self.graph[node_id][neighbor]["weight"] for neighbor in neighbors
        ]
        
        # 综合分数: 0.7 * query_similarity + 0.3 * edge_weight
        combined_scores = 0.7 * scores + 0.3 * np.array(edge_weights)
        
        return [(neighbors[i], float(combined_scores[i])) for i in range(len(neighbors))]


class GraphMemoryRetriever(MapFunction):
    """
    图遍历内存检索算子。
    
    特点:
    - BFS 遍历（beam search）
    - 最大深度和节点数限制
    - 路径记录
    - 与查询向量的相关性排序
    """
    
    def __init__(
        self,
        max_depth: int = 3,
        max_nodes: int = 200,
        beam_width: int = 10,
        service_name: str = "graph_memory",
        **kwargs
    ):
        """
        初始化图遍历算子。
        
        Args:
            max_depth: 最大遍历深度
            max_nodes: 最大返回节点数
            beam_width: Beam search 宽度
            service_name: 图内存服务名称
        """
        super().__init__(**kwargs)
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.beam_width = beam_width
        self.service_name = service_name
        
        logger.info(
            f"GraphMemoryRetriever initialized: max_depth={max_depth}, "
            f"max_nodes={max_nodes}, beam_width={beam_width}"
        )
    
    def execute(self, data: JoinedEvent) -> list[GraphMemoryResult]:
        """
        执行图遍历搜索。
        
        Args:
            data: Join 后的事件
        
        Returns:
            图遍历结果列表
        """
        if data.query.embedding is None:
            logger.warning(f"Query {data.query.query_id} has no embedding")
            return []
        
        try:
            # 调用图内存服务
            search_results = self.call_service(
                self.service_name,
                "search",
                query_embedding=data.query.embedding,
                max_depth=self.max_depth,
                max_nodes=self.max_nodes,
                beam_width=self.beam_width,
            )
            
            # 转换为 GraphMemoryResult
            results = [
                GraphMemoryResult(
                    node_id=r["node_id"],
                    content=r["content"],
                    depth=r["depth"],
                    path=r["path"],
                    relevance_score=r["relevance_score"],
                    node_type=r.get("node_type", "memory"),
                )
                for r in search_results
            ]
            
            logger.debug(
                f"Query {data.query.query_id}: retrieved {len(results)} graph nodes"
            )
            
            return results
        
        except Exception as e:
            logger.error(
                f"Graph memory retrieval failed for query {data.query.query_id}: {e}",
                exc_info=True,
            )
            return []


def build_knowledge_graph(
    documents: list[dict[str, Any]],
    embedding_dim: int = 1024,
    similarity_threshold: float = 0.7,
) -> nx.DiGraph:
    """
    从文档构建知识图（工具函数）。
    
    Args:
        documents: 文档列表，每个元素包含:
            - node_id: 节点ID
            - content: 内容文本
            - embedding: 向量表示（可选，如果没有则需要外部计算）
            - node_type: 节点类型（可选）
        embedding_dim: Embedding 维度
        similarity_threshold: 构图相似度阈值
    
    Returns:
        NetworkX 有向图
    """
    logger.info(f"Building knowledge graph from {len(documents)} documents...")
    
    graph = nx.DiGraph()
    node_embeddings: dict[str, np.ndarray] = {}
    
    # 添加节点
    for doc in documents:
        node_id = doc["node_id"]
        embedding = np.array(doc["embedding"], dtype=np.float32)
        
        graph.add_node(
            node_id,
            content=doc["content"],
            node_type=doc.get("node_type", "memory"),
        )
        node_embeddings[node_id] = embedding
    
    # 构建边
    node_ids = list(node_embeddings.keys())
    embeddings_matrix = np.array([node_embeddings[nid] for nid in node_ids])
    
    # 归一化
    norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
    embeddings_matrix = embeddings_matrix / (norms + 1e-8)
    
    # 相似度矩阵
    similarity_matrix = embeddings_matrix @ embeddings_matrix.T
    
    # 添加边
    edge_count = 0
    for i, source_id in enumerate(node_ids):
        for j, target_id in enumerate(node_ids):
            if i != j and similarity_matrix[i, j] >= similarity_threshold:
                weight = float(similarity_matrix[i, j])
                graph.add_edge(source_id, target_id, weight=weight)
                edge_count += 1
    
    logger.info(
        f"Knowledge graph built: {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges"
    )
    
    return graph


def register_graph_memory_service(
    env: Any,
    knowledge_base: list[dict[str, Any]],
    embedding_dim: int = 1024,
    similarity_threshold: float = 0.7,
    service_name: str = "graph_memory",
) -> bool:
    """
    注册图内存服务到环境。
    
    Args:
        env: RemoteEnvironment 实例
        knowledge_base: 知识库列表
        embedding_dim: Embedding 维度
        similarity_threshold: 构图相似度阈值
        service_name: 服务名称
    
    Returns:
        注册是否成功
    """
    try:
        # 创建服务实例
        service = GraphMemoryService(
            config={},
            embedding_dim=embedding_dim,
            similarity_threshold=similarity_threshold,
        )
        
        # 构建图
        service.build_graph(knowledge_base)
        
        # 注册到环境
        env.register_service(service_name, service)
        
        logger.info(f"Graph memory service '{service_name}' registered successfully")
        return True
    
    except Exception as e:
        logger.error(f"Failed to register graph memory service: {e}", exc_info=True)
        return False
