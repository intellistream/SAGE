"""
性能基准测试
用于CI/CD中的性能回归检测
"""

import numpy as np
import pytest


@pytest.mark.benchmark
def test_metrics_computation_performance(benchmark):
    """测试指标计算性能"""
    # 生成测试数据
    latencies = np.random.exponential(0.01, 10000)

    def compute_metrics():
        return {
            "p50": np.percentile(latencies, 50),
            "p95": np.percentile(latencies, 95),
            "p99": np.percentile(latencies, 99),
        }

    result = benchmark(compute_metrics)
    assert result["p50"] > 0


@pytest.mark.benchmark
def test_vector_distance_performance(benchmark):
    """测试向量距离计算性能"""
    # 生成测试向量
    dim = 128
    query = np.random.randn(dim).astype(np.float32)
    vectors = np.random.randn(1000, dim).astype(np.float32)

    def compute_distances():
        # 欧氏距离
        return np.linalg.norm(vectors - query, axis=1)

    result = benchmark(compute_distances)
    assert len(result) == 1000


@pytest.mark.benchmark
def test_data_loading_performance(benchmark):
    """测试数据加载性能"""
    from datasets.base import Dataset

    class DummyDataset(Dataset):
        def __init__(self):
            super().__init__()
            self.nb = 10000
            self.nq = 100
            self.d = 128

        def prepare(self):
            self.data = np.random.randn(self.nb, self.d).astype(np.float32)
            self.queries = np.random.randn(self.nq, self.d).astype(np.float32)

        def get_dataset(self):
            return self.data

        def get_queries(self):
            return self.queries

    def load_data():
        ds = DummyDataset()
        ds.prepare()
        return ds.get_dataset()

    result = benchmark(load_data)
    assert result.shape == (10000, 128)


@pytest.mark.benchmark
def test_recall_computation_performance(benchmark):
    """测试召回率计算性能"""
    k = 10
    n_queries = 1000

    # 生成测试数据
    gt_ids = np.random.randint(0, 100000, (n_queries, k))
    pred_ids = np.random.randint(0, 100000, (n_queries, k))

    def compute_recall():
        recalls = []
        for i in range(n_queries):
            gt_set = set(gt_ids[i])
            pred_set = set(pred_ids[i])
            recall = len(gt_set & pred_set) / k
            recalls.append(recall)
        return np.mean(recalls)

    result = benchmark(compute_recall)
    assert 0 <= result <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
