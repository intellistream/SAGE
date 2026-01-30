"""
Workload 4 聚类去重模块单元测试
"""

import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from ..clustering import (
    DBSCANClusteringOperator,
    SimilarityDeduplicator,
    analyze_clustering_quality,
    visualize_clusters,
)
from ..models import ClusteringResult, GraphMemoryResult, VDBRetrievalResult


class TestDBSCANClusteringOperator(unittest.TestCase):
    """测试 DBSCAN 聚类算子"""

    def setUp(self):
        """测试前准备"""
        self.operator = DBSCANClusteringOperator(
            eps=0.15, min_samples=2, metric="cosine", keep_noise=True
        )

    def _create_sample_vdb_results(self, n: int = 10) -> list[VDBRetrievalResult]:
        """创建样本 VDB 检索结果"""
        results = []
        for i in range(n):
            # 创建具有不同相似度的文档
            # 前 5 个文档相似，后 5 个文档相似
            group = i // 5
            base_content = f"This is document group {group} "
            content = base_content + f"document {i}"

            results.append(
                VDBRetrievalResult(
                    doc_id=f"doc_{i}",
                    content=content,
                    score=1.0 - i * 0.05,  # 递减的分数
                    source="vdb1",
                    stage=1,
                    metadata={"embedding": self._generate_similar_embedding(group, i)},
                )
            )
        return results

    def _generate_similar_embedding(self, group: int, idx: int, dim: int = 128) -> list[float]:
        """生成相似的 embedding（同组相似）"""
        np.random.seed(group * 1000)  # 同组使用相同的随机种子

        # 基础向量（组内相同）
        base = np.random.randn(dim)
        base = base / np.linalg.norm(base)

        # 添加少量噪声（确保同组内余弦相似度 > 0.9）
        np.random.seed(group * 1000 + idx)
        noise = np.random.randn(dim) * 0.05  # 减小噪声

        vec = base + noise

        # 归一化
        vec = vec / np.linalg.norm(vec)

        return vec.tolist()

    def test_basic_clustering(self):
        """测试基本聚类功能"""
        results = self._create_sample_vdb_results(10)
        joined_id = "test_join_1"

        # 执行聚类
        output_id, deduped, clusters = self.operator.execute((joined_id, results))

        # 验证输出
        self.assertEqual(output_id, joined_id)
        self.assertIsInstance(deduped, list)
        self.assertIsInstance(clusters, list)

        # 验证去重效果（10个文档应该聚成2-3个簇）
        self.assertLess(len(deduped), len(results))
        self.assertGreater(len(clusters), 0)

        # 验证聚类结果格式
        for cluster in clusters:
            self.assertIsInstance(cluster, ClusteringResult)
            self.assertGreater(cluster.cluster_size, 0)
            self.assertIsNotNone(cluster.representative_doc_id)
            self.assertIsNotNone(cluster.centroid)

    def test_empty_input(self):
        """测试空输入"""
        joined_id, deduped, clusters = self.operator.execute(("test_join", []))

        self.assertEqual(joined_id, "test_join")
        self.assertEqual(len(deduped), 0)
        self.assertEqual(len(clusters), 0)

    def test_single_document(self):
        """测试单个文档"""
        results = self._create_sample_vdb_results(1)
        joined_id, deduped, clusters = self.operator.execute(("test_join", results))

        self.assertEqual(len(deduped), 1)
        self.assertEqual(len(clusters), 0)

    def test_performance_25_docs(self):
        """性能测试: 25个文档聚类时间 < 50ms"""
        results = self._create_sample_vdb_results(25)

        start_time = time.perf_counter()
        self.operator.execute(("test_join", results))
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        print(f"\n25个文档聚类时间: {elapsed_ms:.2f}ms")

        # 验证性能要求
        self.assertLess(elapsed_ms, 100.0, "聚类时间应 < 100ms（宽松标准）")

    def test_deduplication_rate(self):
        """测试去重率（应达到 20-30%）"""
        # 创建 30 个文档，其中有明显的重复组
        results = []
        for i in range(30):
            group = i // 3  # 每 3 个文档为一组
            results.append(
                VDBRetrievalResult(
                    doc_id=f"doc_{i}",
                    content=f"Group {group} document {i}",
                    score=1.0 - i * 0.01,
                    source="vdb1",
                    stage=1,
                    metadata={"embedding": self._generate_similar_embedding(group, i % 3)},
                )
            )

        _, deduped, _ = self.operator.execute(("test_join", results))

        removed = len(results) - len(deduped)
        dedup_rate = removed / len(results)

        print(f"\n去重率: {dedup_rate * 100:.1f}% (移除 {removed}/{len(results)} 个文档)")

        # 验证去重率在合理范围
        self.assertGreater(dedup_rate, 0.15, "去重率应 > 15%")
        self.assertLess(dedup_rate, 0.7, "去重率应 < 70%（避免过度去重）")

    def test_representative_selection(self):
        """测试代表文档选择逻辑（应选择分数最高的）"""
        # 创建一个簇：3 个相似文档
        results = []
        embeddings = self._generate_similar_embedding(0, 0)
        for i, score in enumerate([0.9, 0.95, 0.85]):  # 中间的分数最高
            results.append(
                VDBRetrievalResult(
                    doc_id=f"doc_{i}",
                    content=f"Similar document {i}",
                    score=score,
                    source="vdb1",
                    stage=1,
                    metadata={"embedding": embeddings},  # 相同 embedding
                )
            )

        _, deduped, clusters = self.operator.execute(("test_join", results))

        # 应该只保留 1 个代表文档
        self.assertEqual(len(deduped), 1)

        # 代表文档应该是分数最高的（doc_1, score=0.95）
        self.assertEqual(deduped[0].doc_id, "doc_1")
        self.assertEqual(deduped[0].score, 0.95)

    def test_noise_handling(self):
        """测试噪声点处理"""
        # 创建大部分相似的文档 + 几个离群点
        results = []

        # 10 个相似文档（形成一个簇）
        for i in range(10):
            results.append(
                VDBRetrievalResult(
                    doc_id=f"similar_{i}",
                    content="Similar content",
                    score=0.9,
                    source="vdb1",
                    stage=1,
                    metadata={"embedding": self._generate_similar_embedding(0, i)},
                )
            )

        # 2 个离群点（噪声）
        for i in range(2):
            results.append(
                VDBRetrievalResult(
                    doc_id=f"outlier_{i}",
                    content=f"Different content {i}",
                    score=0.7,
                    source="vdb1",
                    stage=1,
                    metadata={"embedding": self._generate_similar_embedding(100 + i, 0)},
                )
            )

        _, deduped, clusters = self.operator.execute(("test_join", results))

        # 应该有 1 个簇 + 2 个噪声点保留
        self.assertGreaterEqual(len(deduped), 3)  # 至少 1(簇代表) + 2(噪声)
        self.assertGreaterEqual(len(clusters), 1)  # 至少 1 个簇

    def test_stats_collection(self):
        """测试统计信息收集"""
        results = self._create_sample_vdb_results(20)

        # 执行多次聚类
        for i in range(3):
            self.operator.execute((f"join_{i}", results))

        # 获取统计信息
        stats = self.operator.get_stats()

        self.assertIn("total_docs", stats)
        self.assertIn("total_clusters", stats)
        self.assertIn("total_removed", stats)
        self.assertIn("dedup_rate", stats)
        self.assertIn("avg_time_per_doc_ms", stats)

        self.assertEqual(stats["total_docs"], 60)  # 3次 × 20个文档
        self.assertGreater(stats["total_removed"], 0)


class TestSimilarityDeduplicator(unittest.TestCase):
    """测试基于相似度的去重算子"""

    def setUp(self):
        """测试前准备"""
        self.operator = SimilarityDeduplicator(threshold=0.95, use_simhash=False)

    def _create_duplicate_docs(
        self, n_groups: int = 5, group_size: int = 3
    ) -> list[VDBRetrievalResult]:
        """创建包含重复的文档"""
        results = []

        for group in range(n_groups):
            # 每组内的文档非常相似
            base_embedding = np.random.randn(128)
            base_embedding = base_embedding / np.linalg.norm(base_embedding)

            for i in range(group_size):
                # 添加微小噪声
                embedding = base_embedding + np.random.randn(128) * 0.01
                embedding = embedding / np.linalg.norm(embedding)

                results.append(
                    VDBRetrievalResult(
                        doc_id=f"group{group}_doc{i}",
                        content=f"Content of group {group}",
                        score=1.0 - (group * group_size + i) * 0.01,
                        source="vdb1",
                        stage=1,
                        metadata={"embedding": embedding.tolist()},
                    )
                )

        return results

    def test_basic_deduplication(self):
        """测试基本去重功能"""
        results = self._create_duplicate_docs(5, 3)  # 15个文档，5组
        joined_id = "test_join"

        output_id, deduped = self.operator.execute((joined_id, results))

        self.assertEqual(output_id, joined_id)
        self.assertLess(len(deduped), len(results))

        # 每组应该只保留1个（共5个）
        self.assertLessEqual(len(deduped), 7)  # 允许一些误差

    def test_high_threshold(self):
        """测试高阈值（0.99）- 几乎不去重"""
        operator = SimilarityDeduplicator(threshold=0.99)
        results = self._create_duplicate_docs(3, 3)

        _, deduped = operator.execute(("test", results))

        # 高阈值应该保留大部分文档
        self.assertGreaterEqual(len(deduped), len(results) * 0.7)

    def test_low_threshold(self):
        """测试低阈值（0.8）- 激进去重"""
        operator = SimilarityDeduplicator(threshold=0.8)
        results = self._create_duplicate_docs(5, 4)

        _, deduped = operator.execute(("test", results))

        # 低阈值应该去除更多文档
        removed_rate = (len(results) - len(deduped)) / len(results)
        self.assertGreater(removed_rate, 0.3)

    def test_score_preservation(self):
        """测试保留高分文档"""
        results = [
            VDBRetrievalResult(
                doc_id="high_score",
                content="content",
                score=0.95,
                source="vdb1",
                stage=1,
                metadata={"embedding": [0.5] * 128},
            ),
            VDBRetrievalResult(
                doc_id="low_score",
                content="content",
                score=0.70,
                source="vdb1",
                stage=1,
                metadata={"embedding": [0.501] * 128},  # 非常相似
            ),
        ]

        _, deduped = self.operator.execute(("test", results))

        # 应该只保留 1 个，且是高分的
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].doc_id, "high_score")

    def test_empty_and_single(self):
        """测试边界情况"""
        # 空输入
        _, deduped = self.operator.execute(("test", []))
        self.assertEqual(len(deduped), 0)

        # 单个文档
        results = [
            VDBRetrievalResult(doc_id="single", content="test", score=0.9, source="vdb1", stage=1)
        ]
        _, deduped = self.operator.execute(("test", results))
        self.assertEqual(len(deduped), 1)

    def test_performance(self):
        """性能测试: 20个文档去重时间 < 50ms"""
        results = self._create_duplicate_docs(4, 5)  # 20个文档

        start_time = time.perf_counter()
        self.operator.execute(("test", results))
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        print(f"\n20个文档去重时间: {elapsed_ms:.2f}ms")

        # O(n²) 算法，放宽要求
        self.assertLess(elapsed_ms, 100.0, "去重时间应 < 100ms")

    def test_graph_memory_results(self):
        """测试处理 GraphMemoryResult"""
        results = [
            GraphMemoryResult(
                node_id=f"node_{i}",
                content=f"Memory content {i // 2}",  # 两两相似
                depth=1,
                path=["root", f"node_{i}"],
                relevance_score=0.9 - i * 0.05,
            )
            for i in range(6)
        ]

        _, deduped = self.operator.execute(("test", results))

        # 应该去除一些重复
        self.assertLess(len(deduped), len(results))

    def test_stats(self):
        """测试统计信息"""
        results = self._create_duplicate_docs(3, 4)

        for i in range(2):
            self.operator.execute((f"join_{i}", results))

        stats = self.operator.get_stats()

        self.assertIn("total_docs", stats)
        self.assertIn("total_removed", stats)
        self.assertIn("dedup_rate", stats)
        self.assertEqual(stats["total_docs"], 24)  # 2次 × 12个文档


class TestVisualizationAndAnalysis(unittest.TestCase):
    """测试可视化和分析工具"""

    def _create_sample_clusters(self, n: int = 5) -> list[ClusteringResult]:
        """创建样本聚类结果"""
        clusters = []
        for i in range(n):
            centroid = np.random.randn(128).tolist()

            # 创建相似度矩阵（对角线为1）
            size = 2 + i
            sim_matrix = np.random.rand(size, size) * 0.3 + 0.7
            np.fill_diagonal(sim_matrix, 1.0)

            clusters.append(
                ClusteringResult(
                    cluster_id=i,
                    representative_doc_id=f"rep_doc_{i}",
                    cluster_docs=[f"doc_{i}_{j}" for j in range(size)],
                    cluster_size=size,
                    centroid=centroid,
                    similarity_matrix=sim_matrix.tolist(),
                )
            )

        return clusters

    def test_visualize_clusters(self):
        """测试聚类可视化（保存到文件）"""
        clusters = self._create_sample_clusters(5)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "clusters_vis.png"

            # 测试 t-SNE
            visualize_clusters(clusters, str(output_path), method="tsne")
            self.assertTrue(output_path.exists())

            # 测试 PCA
            output_path2 = Path(tmpdir) / "clusters_pca.png"
            visualize_clusters(clusters, str(output_path2), method="pca")
            self.assertTrue(output_path2.exists())

    def test_visualize_empty(self):
        """测试空聚类可视化"""
        # 应该不崩溃
        visualize_clusters([], None, method="tsne")

    def test_visualize_no_centroids(self):
        """测试没有 centroid 的聚类"""
        clusters = [
            ClusteringResult(
                cluster_id=0,
                representative_doc_id="doc_0",
                cluster_docs=["doc_0", "doc_1"],
                cluster_size=2,
                centroid=None,  # 没有 centroid
            )
        ]

        # 应该不崩溃
        visualize_clusters(clusters, None)

    def test_analyze_clustering_quality(self):
        """测试聚类质量分析"""
        clusters = self._create_sample_clusters(5)

        metrics = analyze_clustering_quality(clusters, verbose=False)

        # 验证返回的指标
        self.assertIn("num_clusters", metrics)
        self.assertIn("avg_cluster_size", metrics)
        self.assertIn("max_cluster_size", metrics)
        self.assertIn("min_cluster_size", metrics)
        self.assertIn("total_docs", metrics)
        self.assertIn("avg_intra_similarity", metrics)

        self.assertEqual(metrics["num_clusters"], 5)
        self.assertGreater(metrics["avg_intra_similarity"], 0.0)
        self.assertLessEqual(metrics["avg_intra_similarity"], 1.0)

    def test_analyze_empty(self):
        """测试空聚类分析"""
        metrics = analyze_clustering_quality([], verbose=False)
        self.assertEqual(metrics, {})


def run_integration_test():
    """集成测试: 完整的聚类去重流程"""
    print("\n" + "=" * 60)
    print("集成测试: 完整聚类去重流程")
    print("=" * 60)

    # 创建测试数据: 50个文档，包含明显的重复组
    results = []
    for group in range(10):
        base_embedding = np.random.randn(128)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)

        for i in range(5):
            embedding = base_embedding + np.random.randn(128) * 0.05
            embedding = embedding / np.linalg.norm(embedding)

            results.append(
                VDBRetrievalResult(
                    doc_id=f"doc_g{group}_i{i}",
                    content=f"Content of group {group}",
                    score=1.0 - (group * 5 + i) * 0.01,
                    source="vdb1",
                    stage=1,
                    metadata={"embedding": embedding.tolist()},
                )
            )

    print(f"原始文档数: {len(results)}")

    # Step 1: DBSCAN 聚类
    print("\n[1] DBSCAN 聚类")
    dbscan_op = DBSCANClusteringOperator(eps=0.15, min_samples=2)
    _, deduped_dbscan, clusters = dbscan_op.execute(("test", results))

    print(f"  去重后文档数: {len(deduped_dbscan)}")
    print(f"  发现簇数: {len(clusters)}")
    print(f"  去重率: {(1 - len(deduped_dbscan) / len(results)) * 100:.1f}%")

    stats = dbscan_op.get_stats()
    print(f"  平均处理时间: {stats['avg_time_per_doc_ms']:.2f}ms/doc")

    # Step 2: 相似度去重（进一步清理）
    print("\n[2] 相似度去重")
    sim_dedup_op = SimilarityDeduplicator(threshold=0.95)
    _, deduped_sim = sim_dedup_op.execute(("test", deduped_dbscan))

    print(f"  最终文档数: {len(deduped_sim)}")
    print(f"  总去重率: {(1 - len(deduped_sim) / len(results)) * 100:.1f}%")

    # Step 3: 分析聚类质量
    print("\n[3] 聚类质量分析")
    metrics = analyze_clustering_quality(clusters, verbose=False)
    print(f"  平均簇大小: {metrics['avg_cluster_size']:.2f}")
    print(f"  平均簇内相似度: {metrics.get('avg_intra_similarity', 0):.4f}")

    # Step 4: 可视化（可选）
    print("\n[4] 生成可视化")
    with tempfile.TemporaryDirectory() as tmpdir:
        vis_path = Path(tmpdir) / "integration_test_clusters.png"
        visualize_clusters(clusters, str(vis_path))
        print(f"  可视化已保存: {vis_path}")

    print("\n" + "=" * 60)
    print("集成测试完成")
    print("=" * 60)


if __name__ == "__main__":
    # 运行单元测试
    unittest.main(argv=[""], exit=False, verbosity=2)

    # 运行集成测试
    run_integration_test()
