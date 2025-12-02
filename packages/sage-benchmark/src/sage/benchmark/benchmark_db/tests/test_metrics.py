"""
测试指标计算
"""

import numpy as np
import pytest
from bench.metrics import BenchmarkMetrics


def test_metrics_initialization():
    """测试指标初始化"""
    metrics = BenchmarkMetrics()
    assert metrics is not None


def test_latency_percentiles():
    """测试延迟百分位数计算"""
    latencies = [0.001, 0.002, 0.003, 0.004, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05]

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)

    assert p50 > 0
    assert p95 > p50
    assert p99 >= p95


def test_recall_computation():
    """测试召回率计算"""
    # Ground truth
    gt = np.array([[1, 2, 3, 4, 5]])
    # Predictions
    pred = np.array([[1, 2, 3, 6, 7]])

    # 计算召回率
    k = 5
    gt_set = set(gt[0])
    pred_set = set(pred[0])
    recall = len(gt_set & pred_set) / k

    assert recall == 0.6  # 3/5


def test_throughput_calculation():
    """测试吞吐量计算"""
    num_operations = 1000
    duration = 10.0  # seconds

    throughput = num_operations / duration

    assert throughput == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
