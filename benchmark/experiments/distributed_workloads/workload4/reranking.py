"""
Workload 4 重排序和评分模块。

实现 5 维评分的重排序算法和 MMR 多样性过滤。

评分维度:
1. Semantic: 语义相关性(query-doc 相似度)
2. Freshness: 时间新鲜度(基于 timestamp)
3. Diversity: 多样性(cluster 覆盖度)
4. Authority: 权威性(图中心性、引用数)
5. Coverage: 覆盖度(关键词覆盖)
"""

import time
from typing import Any

import numpy as np

from sage.common.core.functions import MapFunction

from .models import (
    ClusteringResult,
    QueryEvent,
    RerankingResult,
    VDBRetrievalResult,
)


class MultiDimensionalReranker(MapFunction):
    """
    5 维评分重排序算子。

    评分维度:
    1. Semantic: 语义相关性(query-doc 相似度)
    2. Freshness: 时间新鲜度(基于 timestamp)
    3. Diversity: 多样性(cluster 覆盖度)
    4. Authority: 权威性(图中心性、引用数)
    5. Coverage: 覆盖度(关键词覆盖)

    Args:
        score_weights: 各维度权重字典，总和应为 1.0
        top_k: 返回 top-k 结果
        enable_profiling: 是否启用性能分析
    """

    def __init__(
        self,
        score_weights: dict[str, float] | None = None,
        top_k: int = 15,
        enable_profiling: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        # 默认权重
        self.weights = score_weights or {
            "semantic": 0.30,
            "freshness": 0.20,
            "diversity": 0.20,
            "authority": 0.15,
            "coverage": 0.15,
        }

        # 验证权重
        total_weight = sum(self.weights.values())
        if not 0.99 <= total_weight <= 1.01:  # 允许浮点误差
            raise ValueError(f"权重总和应为 1.0，实际为 {total_weight}")

        self.top_k = top_k
        self.enable_profiling = enable_profiling

    def execute(
        self,
        data: tuple[object, list[object], list[VDBRetrievalResult], list[ClusteringResult] | None],
    ) -> tuple[object, list[object], list[RerankingResult]]:
        """
        计算 5 维评分并重排序。

        Args:
            data: (joined_event, graph_results, vdb_results, clustering_results)

        Returns:
            (joined_event, graph_results, 重排序后的 RerankingResult 列表)
        """
        from sage.kernel.runtime.communication.packet import StopSignal

        if isinstance(data, StopSignal):
            return data

        start_time = time.perf_counter() if self.enable_profiling else 0

        joined_event, graph_results, vdb_results, clustering_info = data
        query = joined_event.query

        if not vdb_results:
            return (joined_event, graph_results, [])

        # 提取 query embedding
        query_embedding = np.array(query.embedding) if query.embedding else None

        # 构建聚类信息索引
        cluster_map = {}
        if clustering_info:
            for cluster in clustering_info:
                for doc_id in cluster.cluster_docs:
                    cluster_map[doc_id] = cluster.cluster_id

        # 计算各维度评分
        reranking_results = []
        for result in vdb_results:
            score_breakdown = self._compute_scores(
                query=query,
                result=result,
                query_embedding=query_embedding,
                cluster_map=cluster_map,
                current_time=time.time(),
            )

            # 加权求和
            final_score = sum(self.weights[dim] * score for dim, score in score_breakdown.items())

            reranking_results.append(
                RerankingResult(
                    doc_id=result.doc_id,
                    content=result.content,
                    final_score=final_score,
                    score_breakdown=score_breakdown,
                    rank=0,  # 稍后填充
                )
            )

        # 按 final_score 降序排序
        reranking_results.sort(key=lambda x: x.final_score, reverse=True)

        # 填充 rank
        for rank, result in enumerate(reranking_results[: self.top_k], start=1):
            result.rank = rank

        if self.enable_profiling:
            elapsed = (time.perf_counter() - start_time) * 1000  # ms
            print(
                f"[MultiDimensionalReranker] 重排序 {len(vdb_results)} 个文档耗时: {elapsed:.2f}ms"
            )

        return (joined_event, graph_results, reranking_results[: self.top_k])

    def _compute_scores(
        self,
        query: QueryEvent,
        result: VDBRetrievalResult,
        query_embedding: np.ndarray | None,
        cluster_map: dict[str, int],
        current_time: float,
    ) -> dict[str, float]:
        """
        计算各维度评分。

        Returns:
            {dimension: score} 字典，所有分数归一化到 [0, 1]
        """
        scores = {}

        # 1. Semantic: 使用 VDB 检索分数作为语义相关性
        scores["semantic"] = result.score

        # 2. Freshness: 基于时间衰减
        scores["freshness"] = self._compute_freshness_score(
            doc_timestamp=result.metadata.get("timestamp", current_time),
            current_time=current_time,
            half_life_hours=24,  # 24 小时半衰期
        )

        # 3. Diversity: 基于聚类覆盖度
        scores["diversity"] = self._compute_diversity_score(
            doc_id=result.doc_id,
            cluster_map=cluster_map,
        )

        # 4. Authority: 基于元数据中的权威性指标
        scores["authority"] = self._compute_authority_score(
            metadata=result.metadata,
        )

        # 5. Coverage: 关键词覆盖度
        scores["coverage"] = self._compute_coverage_score(
            query_text=query.query_text,
            doc_content=result.content,
        )

        return scores

    def _compute_freshness_score(
        self,
        doc_timestamp: float,
        current_time: float,
        half_life_hours: float = 24,
    ) -> float:
        """
        计算时间新鲜度评分(指数衰减)。

        Args:
            doc_timestamp: 文档时间戳
            current_time: 当前时间戳
            half_life_hours: 半衰期(小时)

        Returns:
            新鲜度评分 [0, 1]
        """
        age_hours = (current_time - doc_timestamp) / 3600

        # 指数衰减: score = 2^(-age / half_life)
        score = 2 ** (-age_hours / half_life_hours)

        return max(0.0, min(1.0, score))

    def _compute_diversity_score(
        self,
        doc_id: str,
        cluster_map: dict[str, int],
    ) -> float:
        """
        计算多样性评分。

        如果文档来自新的 cluster，分数更高。

        Args:
            doc_id: 文档 ID
            cluster_map: {doc_id: cluster_id}

        Returns:
            多样性评分 [0, 1]
        """
        if not cluster_map:
            # 没有聚类信息，给中性分数
            return 0.5

        # 如果文档属于某个 cluster，给基础分数
        # 实际应用中，这里可以跟踪已选择的 cluster，给新 cluster 更高分数
        # 这里简化为: 所有文档基础分数 0.6
        if doc_id in cluster_map:
            return 0.6
        else:
            # 不在任何 cluster 中(噪音点)，视为高多样性
            return 0.8

    def _compute_authority_score(
        self,
        metadata: dict[str, Any],
    ) -> float:
        """
        计算权威性评分。

        基于元数据中的指标(如引用数、图中心性等)。

        Args:
            metadata: 文档元数据

        Returns:
            权威性评分 [0, 1]
        """
        # 尝试从元数据中提取权威性指标

        # 1. 引用数(如果有)
        citations = metadata.get("citations", 0)
        citation_score = min(1.0, citations / 100)  # 归一化：100 引用 = 1.0

        # 2. 图中心性(如果有)
        centrality = metadata.get("centrality", 0.0)
        centrality_score = min(1.0, centrality)

        # 3. 来源权威性
        source = metadata.get("source", "")
        source_score = 0.5
        if "authoritative" in source.lower() or "verified" in source.lower():
            source_score = 0.9

        # 综合评分(加权平均)
        if citations > 0 or centrality > 0:
            # 有明确的权威性指标
            authority_score = citation_score * 0.5 + centrality_score * 0.5
        else:
            # 只有来源信息
            authority_score = source_score

        return authority_score

    def _compute_coverage_score(
        self,
        query_text: str,
        doc_content: str,
    ) -> float:
        """
        计算关键词覆盖度评分。

        Args:
            query_text: 查询文本
            doc_content: 文档内容

        Returns:
            覆盖度评分 [0, 1]
        """
        # 简单实现：基于关键词覆盖
        # 提取查询关键词(简单分词)
        query_tokens = set(query_text.lower().split())
        doc_tokens = set(doc_content.lower().split())

        # 去除停用词(简化版)
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        query_tokens -= stopwords

        if not query_tokens:
            return 0.5  # 没有有效关键词，给中性分数

        # 计算覆盖率
        covered = query_tokens & doc_tokens
        coverage = len(covered) / len(query_tokens)

        return coverage


class MMRDiversityFilter(MapFunction):
    """
    MMR (Maximal Marginal Relevance) 多样性过滤。

    平衡相关性和多样性，避免结果过于相似。

    公式:
        MMR = λ * Sim(q, d) - (1-λ) * max(Sim(d, d_selected))

    Args:
        lambda_param: 相关性权重 [0, 1]，越高越重视相关性
        top_k: 返回 top-k 结果
        enable_profiling: 是否启用性能分析
    """

    def __init__(
        self, lambda_param: float = 0.7, top_k: int = 10, enable_profiling: bool = False, **kwargs
    ):
        super().__init__(**kwargs)

        if not 0 <= lambda_param <= 1:
            raise ValueError(f"lambda_param 应在 [0, 1]，实际为 {lambda_param}")

        self.lambda_param = lambda_param
        self.top_k = top_k
        self.enable_profiling = enable_profiling

    def execute(
        self, data: tuple[object, list[object], list[RerankingResult]]
    ) -> tuple[object, list[object], list[RerankingResult]]:
        """
        MMR 迭代选择。

        Args:
            data: (joined_event, graph_results, reranking_results)

        Returns:
            (joined_event, graph_results, MMR 过滤后的结果列表)
        """
        from sage.kernel.runtime.communication.packet import StopSignal

        if isinstance(data, StopSignal):
            return data

        joined_event, graph_results, reranking_results = data
        start_time = time.perf_counter() if self.enable_profiling else 0

        if not reranking_results:
            return (joined_event, graph_results, [])

        if len(reranking_results) <= self.top_k:
            # 结果数量不超过 top_k，直接返回
            return (joined_event, graph_results, reranking_results)

        query = joined_event.query

        # 提取 query embedding
        query_embedding = np.array(query.embedding) if query.embedding else None
        if query_embedding is None:
            # 没有 embedding，无法计算相似度，直接返回 top-k
            return (joined_event, graph_results, reranking_results[: self.top_k])

        # 归一化 query embedding
        query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # 提取文档 embeddings(从元数据中，假设已包含)
        doc_embeddings = []
        for result in reranking_results:
            # 尝试从 content 或 metadata 获取 embedding
            # 这里简化处理：假设在重排序前已经附加了 embedding
            # 实际实现中可能需要重新调用 embedding service
            embedding = result.score_breakdown.get("embedding")
            if embedding:
                doc_embeddings.append(np.array(embedding))
            else:
                # 如果没有 embedding，使用 semantic score 作为相似度的近似
                doc_embeddings.append(None)

        # MMR 迭代选择
        selected: list[RerankingResult] = []
        selected_embeddings: list[np.ndarray] = []
        remaining_indices = list(range(len(reranking_results)))

        while len(selected) < self.top_k and remaining_indices:
            best_idx = None
            best_mmr_score = -float("inf")

            for idx in remaining_indices:
                result = reranking_results[idx]
                doc_embedding = doc_embeddings[idx]

                # 计算相关性分数(使用 final_score 或 semantic score)
                relevance_score = result.score_breakdown.get("semantic", result.final_score)

                # 计算与已选择文档的最大相似度
                max_similarity = 0.0
                if doc_embedding is not None and len(selected_embeddings) > 0:
                    # 归一化当前文档 embedding
                    doc_norm = doc_embedding / (np.linalg.norm(doc_embedding) + 1e-8)

                    # 计算与所有已选择文档的相似度
                    for selected_emb in selected_embeddings:
                        similarity = np.dot(doc_norm, selected_emb)
                        max_similarity = max(max_similarity, similarity)

                # 计算 MMR 分数
                mmr_score = (
                    self.lambda_param * relevance_score - (1 - self.lambda_param) * max_similarity
                )

                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = idx

            if best_idx is None:
                break

            # 选择最佳文档
            selected.append(reranking_results[best_idx])
            if doc_embeddings[best_idx] is not None:
                # 归一化并添加到已选择列表
                doc_norm = doc_embeddings[best_idx] / (
                    np.linalg.norm(doc_embeddings[best_idx]) + 1e-8
                )
                selected_embeddings.append(doc_norm)

            remaining_indices.remove(best_idx)

        # 更新 rank
        for rank, result in enumerate(selected, start=1):
            result.rank = rank

        if self.enable_profiling:
            elapsed = (time.perf_counter() - start_time) * 1000  # ms
            print(
                f"[MMRDiversityFilter] MMR 过滤 {len(reranking_results)} → {len(selected)} 耗时: {elapsed:.2f}ms"
            )

        return (joined_event, graph_results, selected)


def visualize_score_breakdown(
    reranking_results: list[RerankingResult],
    output_path: str,
    title: str = "5-Dimensional Score Breakdown",
) -> None:
    """
    可视化 5 维评分分布(雷达图)。

    Args:
        reranking_results: 重排序结果列表
        output_path: 输出图片路径(PNG)
        title: 图表标题
    """
    try:
        from math import pi

        import matplotlib.pyplot as plt
    except ImportError:
        print("警告: matplotlib 未安装，无法生成可视化")
        return

    if not reranking_results:
        print("警告: 没有结果可以可视化")
        return

    # 提取前 5 个结果用于可视化
    top_results = reranking_results[:5]

    # 维度标签
    dimensions = ["Semantic", "Freshness", "Diversity", "Authority", "Coverage"]
    num_dims = len(dimensions)

    # 创建雷达图
    angles = [n / float(num_dims) * 2 * pi for n in range(num_dims)]
    angles += angles[:1]  # 闭合

    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection="polar"))

    # 为每个文档绘制雷达图
    for idx, result in enumerate(top_results):
        values = [
            result.score_breakdown.get("semantic", 0),
            result.score_breakdown.get("freshness", 0),
            result.score_breakdown.get("diversity", 0),
            result.score_breakdown.get("authority", 0),
            result.score_breakdown.get("coverage", 0),
        ]
        values += values[:1]  # 闭合

        label = f"Rank {result.rank} (Score: {result.final_score:.3f})"
        ax.plot(angles, values, "o-", linewidth=2, label=label)
        ax.fill(angles, values, alpha=0.15)

    # 设置标签
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimensions, size=10)
    ax.set_ylim(0, 1)
    ax.set_title(title, size=14, weight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    # 保存图片
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"✓ 评分可视化已保存到: {output_path}")


def visualize_score_distribution(
    reranking_results: list[RerankingResult],
    output_path: str,
    title: str = "Score Distribution by Dimension",
) -> None:
    """
    可视化评分分布(柱状图)。

    Args:
        reranking_results: 重排序结果列表
        output_path: 输出图片路径(PNG)
        title: 图表标题
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("警告: matplotlib 未安装，无法生成可视化")
        return

    if not reranking_results:
        print("警告: 没有结果可以可视化")
        return

    # 提取所有维度的平均分数
    dimensions = ["semantic", "freshness", "diversity", "authority", "coverage"]
    avg_scores = {}

    for dim in dimensions:
        scores = [r.score_breakdown.get(dim, 0) for r in reranking_results]
        avg_scores[dim] = np.mean(scores) if scores else 0

    # 绘制柱状图
    fig, ax = plt.subplots(figsize=(10, 6))

    x_pos = range(len(dimensions))
    values = [avg_scores[dim] for dim in dimensions]
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"]

    bars = ax.bar(x_pos, values, color=colors, alpha=0.8, edgecolor="black")

    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.3f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_xlabel("Dimensions", fontsize=12, weight="bold")
    ax.set_ylabel("Average Score", fontsize=12, weight="bold")
    ax.set_title(title, fontsize=14, weight="bold")
    ax.set_xticks(x_pos)
    ax.set_xticklabels([d.capitalize() for d in dimensions], fontsize=10)
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"✓ 评分分布已保存到: {output_path}")
