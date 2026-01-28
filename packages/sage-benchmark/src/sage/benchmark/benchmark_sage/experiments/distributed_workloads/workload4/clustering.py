"""
Workload 4 聚类去重模块

实现 DBSCAN 聚类和基于相似度的去重算法，减少冗余文档。
"""

import time
from typing import Any
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

from .models import VDBRetrievalResult, ClusteringResult, GraphMemoryResult


# 简化的基类(避免依赖 sage.kernel)
class MapFunction:
    """简化的 MapFunction 基类"""
    def __init__(self, **kwargs):
        pass
    
    def execute(self, data):
        raise NotImplementedError


class DBSCANClusteringOperator(MapFunction):
    """
    DBSCAN 聚类去重算子。
    
    特点:
    - 使用 scikit-learn DBSCAN
    - 基于 embedding 余弦相似度
    - 每个 cluster 选择得分最高的代表文档
    - 去除噪声点(cluster_id=-1)
    
    参数:
        eps: DBSCAN 邻域半径(对应于 1-cosine_similarity)
        min_samples: 最小样本数
        metric: 距离度量(默认 cosine)
        keep_noise: 是否保留噪声点(cluster_id=-1)
    """
    
    def __init__(
        self,
        eps: float = 0.15,
        min_samples: int = 2,
        metric: str = "cosine",
        keep_noise: bool = True,
        **kwargs: Any
    ):
        super().__init__(**kwargs)
        self.eps = eps
        self.min_samples = min_samples
        self.metric = metric
        self.keep_noise = keep_noise
        
        # 性能统计
        self._total_docs = 0
        self._total_clusters = 0
        self._total_removed = 0
        self._total_time = 0.0
    
    def execute(
        self,
        data: tuple[object, list[object], list[VDBRetrievalResult | GraphMemoryResult]]
    ) -> tuple[object, list[object], list[VDBRetrievalResult | GraphMemoryResult], list[ClusteringResult]]:
        """
        执行聚类并去重。
        
        Args:
            data: (joined_event, graph_results, vdb_results) - 待聚类的文档列表
        
        Returns:
            (joined_event, graph_results, 去重后的VDB文档列表, 聚类信息)
        """
        from sage.kernel.runtime.communication.packet import StopSignal
        if isinstance(data, StopSignal):
            return data
        
        start_time = time.perf_counter()
        
        joined_event, graph_results, vdb_results = data
        
        # 合并 graph_results 和 vdb_results 进行聚类去重
        all_results = graph_results + vdb_results
        
        if len(all_results) == 0:
            return (joined_event, graph_results, [], [])
        
        if len(all_results) == 1:
            # 单个文档无需聚类
            # VDB结果去重后返回，graph结果保持不变
            if len(vdb_results) == 1:
                return (joined_event, graph_results, vdb_results, [])
            else:
                return (joined_event, graph_results, [], [])
        
        # 提取 embeddings 和文档信息
        embeddings = []
        doc_info = []
        
        for result in all_results:
            # 获取 embedding(从 metadata 或 content embedding)
            if isinstance(result, VDBRetrievalResult):
                embedding = result.metadata.get("embedding")
                if embedding is None:
                    # VDB 结果可能没有存储 embedding，需要重新计算或跳过
                    # 这里简化处理：使用文档ID的哈希作为伪embedding(实际应调用embedding服务)
                    embedding = self._get_pseudo_embedding(result.content)
                doc_info.append({
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "result": result,
                    "is_graph": False
                })
            elif isinstance(result, GraphMemoryResult):
                embedding = self._get_pseudo_embedding(result.content)
                doc_info.append({
                    "doc_id": result.node_id,
                    "score": result.relevance_score,
                    "result": result,
                    "is_graph": True
                })
            else:
                continue
            
            embeddings.append(embedding)
        
        if len(embeddings) < self.min_samples:
            # 文档太少，无需聚类
            return (joined_event, graph_results, vdb_results, [])
        
        # 转换为 numpy 数组
        embeddings_array = np.array(embeddings)
        
        # 执行 DBSCAN 聚类
        clustering = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric=self.metric
        )
        cluster_labels = clustering.fit_predict(embeddings_array)
        
        # 分组聚类结果
        clusters = defaultdict(list)
        for idx, label in enumerate(cluster_labels):
            clusters[label].append((idx, doc_info[idx]))
        
        # 为每个 cluster 选择代表文档
        deduplicated_results = []
        clustering_results = []
        
        for cluster_id, cluster_items in clusters.items():
            if cluster_id == -1:
                # 噪声点
                if self.keep_noise:
                    # 保留所有噪声点
                    for idx, info in cluster_items:
                        deduplicated_results.append(info["result"])
            else:
                # 选择得分最高的文档作为代表
                cluster_items.sort(key=lambda x: x[1]["score"], reverse=True)
                representative_idx, representative_info = cluster_items[0]
                deduplicated_results.append(representative_info["result"])
                
                # 记录聚类信息
                cluster_doc_ids = [info["doc_id"] for _, info in cluster_items]
                
                # 计算簇中心(centroid)
                cluster_embeddings = embeddings_array[[idx for idx, _ in cluster_items]]
                centroid = cluster_embeddings.mean(axis=0).tolist()
                
                # 计算簇内相似度矩阵(可选，用于分析)
                if len(cluster_items) <= 10:  # 仅对小簇计算，避免开销过大
                    sim_matrix = cosine_similarity(cluster_embeddings).tolist()
                else:
                    sim_matrix = None
                
                clustering_results.append(ClusteringResult(
                    cluster_id=int(cluster_id),
                    representative_doc_id=representative_info["doc_id"],
                    cluster_docs=cluster_doc_ids,
                    cluster_size=len(cluster_items),
                    centroid=centroid,
                    similarity_matrix=sim_matrix
                ))
        
        # 分离 graph 和 vdb 结果
        deduplicated_vdb = [r for r, info in zip(deduplicated_results, doc_info) if not info["is_graph"]]
        deduplicated_graph = [r for r, info in zip(deduplicated_results, doc_info) if info["is_graph"]]
        
        # 更新统计信息
        elapsed_time = time.perf_counter() - start_time
        self._total_docs += len(all_results)
        self._total_clusters += len([c for c in clusters if c != -1])
        self._total_removed += len(all_results) - len(deduplicated_results)
        self._total_time += elapsed_time
        
        return (joined_event, deduplicated_graph, deduplicated_vdb, clustering_results)
    
    def _get_pseudo_embedding(self, content: str, dim: int = 128) -> list[float]:
        """
        生成伪 embedding(用于测试/演示)。
        
        实际生产环境应调用真实的 embedding 服务。
        """
        # 使用内容的哈希值生成确定性的伪向量
        import hashlib
        hash_bytes = hashlib.sha256(content.encode()).digest()
        # 取前 dim*4 个字节，转换为 float
        vector = []
        for i in range(min(dim, len(hash_bytes) // 4)):
            val = int.from_bytes(hash_bytes[i*4:(i+1)*4], 'big') / (2**32)
            vector.append(val)
        
        # 填充到指定维度
        while len(vector) < dim:
            vector.append(0.0)
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = (np.array(vector) / norm).tolist()
        
        return vector
    
    def get_stats(self) -> dict[str, Any]:
        """获取聚类统计信息"""
        avg_time = self._total_time / max(self._total_docs, 1)
        dedup_rate = self._total_removed / max(self._total_docs, 1)
        
        return {
            "total_docs": self._total_docs,
            "total_clusters": self._total_clusters,
            "total_removed": self._total_removed,
            "dedup_rate": dedup_rate,
            "avg_time_per_doc_ms": avg_time * 1000,
            "total_time_sec": self._total_time,
        }


class SimilarityDeduplicator(MapFunction):
    """
    基于相似度矩阵的去重算子(O(n²) 但 n 小)。
    
    用于 DBSCAN 的补充或替代，特别适合文档数量较少的场景。
    
    算法:
    1. 计算所有文档对的相似度
    2. 如果两个文档相似度 > threshold，保留得分较高的
    3. 使用贪心算法避免重复比较
    
    参数:
        threshold: 相似度阈值(0-1)
        use_simhash: 是否使用 SimHash 粗筛优化
    """
    
    def __init__(
        self,
        threshold: float = 0.95,
        use_simhash: bool = True,
        **kwargs: Any
    ):
        super().__init__(**kwargs)
        self.threshold = threshold
        self.use_simhash = use_simhash
        
        # 性能统计
        self._total_docs = 0
        self._total_removed = 0
        self._total_time = 0.0
    
    def execute(
        self,
        data: tuple[str, list[VDBRetrievalResult | GraphMemoryResult]]
    ) -> tuple[str, list[VDBRetrievalResult | GraphMemoryResult]]:
        """
        执行相似度去重。
        
        Args:
            data: (joined_id, results) - 待去重的文档列表
        
        Returns:
            (joined_id, 去重后的文档列表)
        """
        from sage.kernel.runtime.communication.packet import StopSignal
        if isinstance(data, StopSignal):
            return data
        
        start_time = time.perf_counter()
        
        joined_id, results = data
        
        if len(results) <= 1:
            return (joined_id, results)
        
        # 提取文档信息和 embeddings
        doc_info = []
        embeddings = []
        
        for result in results:
            if isinstance(result, VDBRetrievalResult):
                embedding = result.metadata.get("embedding")
                if embedding is None:
                    embedding = self._get_pseudo_embedding(result.content)
                score = result.score
            elif isinstance(result, GraphMemoryResult):
                embedding = self._get_pseudo_embedding(result.content)
                score = result.relevance_score
            else:
                continue
            
            doc_info.append({
                "result": result,
                "score": score,
                "embedding": embedding,
                "content": result.content if isinstance(result, VDBRetrievalResult) else result.content
            })
            embeddings.append(embedding)
        
        # 按分数降序排序
        doc_info.sort(key=lambda x: x["score"], reverse=True)
        
        # 贪心去重
        kept_indices = []
        kept_embeddings = []
        
        for i, info in enumerate(doc_info):
            current_embedding = np.array(info["embedding"])
            
            # 检查是否与已保留的文档相似
            is_duplicate = False
            
            if self.use_simhash and len(kept_indices) > 10:
                # SimHash 粗筛(简化版：仅用于大量文档)
                # 实际实现可以使用真实的 SimHash 算法
                pass
            
            # 精确相似度计算
            for kept_emb in kept_embeddings:
                similarity = self._cosine_similarity(current_embedding, kept_emb)
                if similarity >= self.threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                kept_indices.append(i)
                kept_embeddings.append(current_embedding)
        
        # 构建去重后的结果
        deduplicated_results = [doc_info[i]["result"] for i in kept_indices]
        
        # 更新统计信息
        elapsed_time = time.perf_counter() - start_time
        self._total_docs += len(results)
        self._total_removed += len(results) - len(deduplicated_results)
        self._total_time += elapsed_time
        
        return (joined_id, deduplicated_results)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _get_pseudo_embedding(self, content: str, dim: int = 128) -> list[float]:
        """生成伪 embedding(与 DBSCAN 算子保持一致)"""
        import hashlib
        hash_bytes = hashlib.sha256(content.encode()).digest()
        vector = []
        for i in range(min(dim, len(hash_bytes) // 4)):
            val = int.from_bytes(hash_bytes[i*4:(i+1)*4], 'big') / (2**32)
            vector.append(val)
        
        while len(vector) < dim:
            vector.append(0.0)
        
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = (np.array(vector) / norm).tolist()
        
        return vector
    
    def get_stats(self) -> dict[str, Any]:
        """获取去重统计信息"""
        avg_time = self._total_time / max(self._total_docs, 1)
        dedup_rate = self._total_removed / max(self._total_docs, 1)
        
        return {
            "total_docs": self._total_docs,
            "total_removed": self._total_removed,
            "dedup_rate": dedup_rate,
            "avg_time_per_doc_ms": avg_time * 1000,
            "total_time_sec": self._total_time,
        }


def visualize_clusters(
    clustering_results: list[ClusteringResult],
    output_path: str | None = None,
    method: str = "tsne"
) -> None:
    """
    可视化聚类结果(用于调试)。
    
    使用 t-SNE 或 PCA 降维 + matplotlib 绘图。
    
    Args:
        clustering_results: 聚类结果列表
        output_path: 输出图片路径(如果为 None 则显示)
        method: 降维方法("tsne" | "pca")
    """
    try:
        import matplotlib.pyplot as plt
        from sklearn.manifold import TSNE
        from sklearn.decomposition import PCA
    except ImportError:
        print("可视化需要 matplotlib 和 scikit-learn，请安装后使用")
        return
    
    if not clustering_results:
        print("没有聚类结果可可视化")
        return
    
    # 收集所有簇的中心点
    centroids = []
    labels = []
    sizes = []
    
    for cluster in clustering_results:
        if cluster.centroid is not None:
            centroids.append(cluster.centroid)
            labels.append(cluster.cluster_id)
            sizes.append(cluster.cluster_size * 100)  # 缩放点大小
    
    if not centroids:
        print("没有可用的 centroid 数据")
        return
    
    centroids_array = np.array(centroids)
    
    # 降维到 2D
    if method == "tsne":
        if len(centroids_array) >= 30:  # t-SNE perplexity 默认30，需要更多样本
            reducer = TSNE(n_components=2, random_state=42)
            coords_2d = reducer.fit_transform(centroids_array)
        elif len(centroids_array) > 3:
            # 样本较少时使用小 perplexity
            perplexity = min(5, len(centroids_array) - 1)
            reducer = TSNE(n_components=2, random_state=42, perplexity=perplexity)
            coords_2d = reducer.fit_transform(centroids_array)
        else:
            # 使用 PCA 作为 fallback
            reducer = PCA(n_components=2)
            coords_2d = reducer.fit_transform(centroids_array)
    else:
        reducer = PCA(n_components=2)
        coords_2d = reducer.fit_transform(centroids_array)
    
    # 绘制散点图
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(
        coords_2d[:, 0],
        coords_2d[:, 1],
        c=labels,
        s=sizes,
        alpha=0.6,
        cmap="viridis"
    )
    
    # 添加标签
    for i, label in enumerate(labels):
        plt.annotate(
            f"C{label}({clustering_results[i].cluster_size})",
            (coords_2d[i, 0], coords_2d[i, 1]),
            fontsize=8,
            alpha=0.7
        )
    
    plt.colorbar(scatter, label="Cluster ID")
    plt.xlabel("Dimension 1")
    plt.ylabel("Dimension 2")
    plt.title(f"Clustering Visualization ({method.upper()})\n{len(clustering_results)} clusters")
    plt.grid(True, alpha=0.3)
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"聚类可视化已保存到: {output_path}")
    else:
        plt.show()
    
    plt.close()


def analyze_clustering_quality(
    clustering_results: list[ClusteringResult],
    verbose: bool = True
) -> dict[str, Any]:
    """
    分析聚类质量。
    
    计算以下指标:
    - 簇数量
    - 平均簇大小
    - 最大/最小簇大小
    - 簇内平均相似度(如果有 similarity_matrix)
    
    Args:
        clustering_results: 聚类结果列表
        verbose: 是否打印详细信息
    
    Returns:
        质量指标字典
    """
    if not clustering_results:
        return {}
    
    # 基础统计
    num_clusters = len(clustering_results)
    cluster_sizes = [c.cluster_size for c in clustering_results]
    avg_size = np.mean(cluster_sizes)
    max_size = max(cluster_sizes)
    min_size = min(cluster_sizes)
    
    # 簇内相似度统计
    intra_similarities = []
    for cluster in clustering_results:
        if cluster.similarity_matrix is not None:
            sim_matrix = np.array(cluster.similarity_matrix)
            # 排除对角线(自相似度为1)
            mask = ~np.eye(sim_matrix.shape[0], dtype=bool)
            if mask.sum() > 0:
                avg_sim = sim_matrix[mask].mean()
                intra_similarities.append(avg_sim)
    
    metrics = {
        "num_clusters": num_clusters,
        "avg_cluster_size": avg_size,
        "max_cluster_size": max_size,
        "min_cluster_size": min_size,
        "total_docs": sum(cluster_sizes),
    }
    
    if intra_similarities:
        metrics["avg_intra_similarity"] = float(np.mean(intra_similarities))
        metrics["min_intra_similarity"] = float(np.min(intra_similarities))
        metrics["max_intra_similarity"] = float(np.max(intra_similarities))
    
    if verbose:
        print("=" * 60)
        print("聚类质量分析")
        print("=" * 60)
        print(f"簇数量: {num_clusters}")
        print(f"总文档数: {metrics['total_docs']}")
        print(f"平均簇大小: {avg_size:.2f}")
        print(f"最大簇大小: {max_size}")
        print(f"最小簇大小: {min_size}")
        
        if "avg_intra_similarity" in metrics:
            print(f"平均簇内相似度: {metrics['avg_intra_similarity']:.4f}")
            print(f"最小簇内相似度: {metrics['min_intra_similarity']:.4f}")
            print(f"最大簇内相似度: {metrics['max_intra_similarity']:.4f}")
        
        print("=" * 60)
    
    return metrics
