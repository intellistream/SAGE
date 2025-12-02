#!/usr/bin/env python3
"""
测试拥塞丢弃功能

使用方法:
    # 从 benchmark_anns 根目录运行
    python tests/test_congestion.py

    # 或者使用 pytest
    cd tests && pytest test_congestion.py

或者使用 run_benchmark.py:
    python run_benchmark.py --algorithm faiss_HNSW --dataset sift --runbook test_congestion_drop
"""

import os
import sys

# 添加父目录到路径，以便导入 benchmark_anns 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from bench.algorithms.base import DummyStreamingANN
from bench.runner import BenchmarkRunner


# 创建一个简单的测试数据集
class SimpleDataset:
    def __init__(self, n=50000, d=128):
        self.nb = n
        self.nq = 100
        self.d = d
        self.dtype = "float32"
        self._data = np.random.randn(n, d).astype("float32")
        self._queries = np.random.randn(self.nq, d).astype("float32")

    def get_dataset_iterator(self, bs=10000):
        for i in range(0, self.nb, bs):
            yield self._data[i : i + bs]

    def get_queries(self):
        return self._queries

    def get_data_in_range(self, start, end):
        return self._data[start:end]

    def short_name(self):
        return "test_dataset"

    def distance(self):
        return "euclidean"

    def search_type(self):
        return "knn"


# 创建数据集和算法
print("创建测试数据集...")
dataset = SimpleDataset()
algo = DummyStreamingANN()

# 创建 runner（启用 worker）
print("初始化 Runner (use_worker=True)...")
runner = BenchmarkRunner(
    algorithm=algo,
    dataset=dataset,
    k=10,
    use_worker=True,  # 启用 worker
)

# 定义 runbook
runbook = {
    "operations": [
        {"operation": "startHPC"},
        {"operation": "initial", "start": 0, "end": 10000},
        {
            "operation": "enableScenario",
            "congestionDrop": True,
            "useBackpressureLogic": True,  # 使用背压逻辑
        },
        {
            "operation": "batch_insert",
            "start": 10000,
            "end": 20000,
            "batchSize": 50,  # 小批次
            "eventRate": 50000,  # 高速率
            "continuousQuery": False,
        },
        {"operation": "waitPending"},
        {"operation": "endHPC"},
    ]
}

print("\n" + "=" * 60)
print("测试拥塞丢弃功能")
print("=" * 60)

# 运行测试
try:
    metrics = runner.run_runbook(runbook)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

    # 输出丢弃统计
    if runner.worker and hasattr(runner.worker, "drop_count_total"):
        print(f"\n总丢弃数: {runner.worker.drop_count_total}")
        if runner.worker.drop_count_total > 0:
            print("✓ 拥塞丢弃功能正常工作！")
        else:
            print("⚠️  未触发丢弃")
            print("提示: 队列容量默认为 10，如果插入速度不够快可能不会触发拥塞")
            print("      可以尝试增加 eventRate 或减小 batchSize")
    else:
        print("⚠️  Worker 未启用")

except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()
