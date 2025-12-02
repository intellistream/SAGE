#!/usr/bin/env python3
"""
快速测试脚本 - 验证流式测评功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import numpy as np
from bench.algorithms.base import DummyStreamingANN
from bench.maintenance import MaintenancePolicy
from bench.runner import BenchmarkRunner
from datasets.base import Dataset


class SimpleDataset(Dataset):
    """简单测试数据集"""

    def __init__(self):
        super().__init__()
        self.nb = 10000
        self.nq = 100
        self.d = 20
        self.dtype = "float32"
        self._data = None
        self._queries = None

    def prepare(self, skip_data=False):
        """生成随机数据"""
        np.random.seed(42)
        self._data = np.random.randn(self.nb, self.d).astype(np.float32)
        self._queries = np.random.randn(self.nq, self.d).astype(np.float32)

    def get_dataset(self):
        if self._data is None:
            self.prepare()
        return self._data

    def get_queries(self):
        if self._queries is None:
            self.prepare()
        return self._queries

    def get_data_in_range(self, start, end):
        if self._data is None:
            self.prepare()
        return self._data[start:end]

    def get_groundtruth(self, k=None):
        return np.zeros((self.nq, k or 10), dtype=np.int32)

    def distance(self):
        return "euclidean"

    def short_name(self):
        return f"simple-{self.nb}"


def test_basic_operations():
    """测试基本操作"""
    print("=" * 60)
    print("测试 1: 基本操作")
    print("=" * 60)

    # 创建算法和数据集
    algo = DummyStreamingANN(metric="euclidean")
    dataset = SimpleDataset()
    dataset.prepare()

    print(f"算法: {algo}")
    print(f"数据集: {dataset}")

    # 初始化
    algo.setup("float32", 10000, 20)
    print("✓ Setup completed")

    # 插入数据
    data = dataset.get_data_in_range(0, 100)
    ids = np.arange(0, 100, dtype=np.uint32)
    algo.insert(data, ids)
    print(f"✓ Inserted {len(ids)} vectors")

    # 查询
    queries = dataset.get_queries()[:10]
    I, D = algo.query(queries, k=5)
    print(f"✓ Query completed: I.shape={I.shape}, D.shape={D.shape}")

    # 删除
    delete_ids = np.arange(50, 60, dtype=np.uint32)
    algo.delete(delete_ids)
    print(f"✓ Deleted {len(delete_ids)} vectors")

    print("\n✅ 基本操作测试通过\n")


def test_runbook_execution():
    """测试 runbook 执行"""
    print("=" * 60)
    print("测试 2: Runbook 执行")
    print("=" * 60)

    # 创建算法和数据集
    algo = DummyStreamingANN(metric="euclidean")
    dataset = SimpleDataset()
    dataset.prepare()

    # 创建 runner
    runner = BenchmarkRunner(
        algorithm=algo, dataset=dataset, k=10, num_workers=1, maintenance_policy=MaintenancePolicy()
    )

    # 定义简单的 runbook
    runbook = [
        {
            "operation": "initial_load",
            "start": 0,
            "end": 1000,
        },
        {
            "operation": "batch_insert",
            "start": 1000,
            "end": 2000,
            "batch_size": 200,
            "event_rate": 1000.0,
            "query_interval": 0.2,
        },
        {
            "operation": "search",
        },
    ]

    # 执行 runbook
    metrics = runner.run_runbook(runbook)

    # 验证结果
    assert metrics.algorithm_name == "DummyStreamingANN"
    assert len(metrics.latency_insert) > 0
    assert len(metrics.latency_query) > 0
    print(f"✓ Total time: {metrics.total_time / 1e6:.2f}s")
    print(f"✓ Insert operations: {runner.counts['batch_insert']}")
    print(f"✓ Search operations: {runner.counts['search']}")

    # 保存结果
    output_dir = "results/test_runbook"
    os.makedirs(output_dir, exist_ok=True)
    runner.save_timestamps(os.path.join(output_dir, "timestamps.csv"))
    runner.save_metrics(os.path.join(output_dir, "metrics.json"))
    print(f"✓ Results saved to {output_dir}")

    print("\n✅ Runbook 执行测试通过\n")


def test_maintenance():
    """测试维护功能"""
    print("=" * 60)
    print("测试 3: 维护功能")
    print("=" * 60)

    from bench.maintenance import MaintenancePolicy, MaintenanceState

    state = MaintenanceState()
    policy = MaintenancePolicy({"default": 0.2})

    # 记录初始范围
    state.record_initial_range(0, 1000)
    assert state.live_points == 1000
    print(f"✓ Initial range: {state.live_points} points")

    # 记录插入
    state.record_insert_range(1000, 1500)
    assert state.live_points == 1500
    print(f"✓ After insert: {state.live_points} points")

    # 记录删除
    state.record_delete_range(500, 700)
    assert state.deleted_points == 200
    ratio = state.deletion_ratio()
    print(f"✓ After delete: {state.deleted_points} deleted, ratio={ratio:.3f}")

    # 检查是否需要重建
    should_rebuild = policy.should_execute(state, "default")
    print(f"✓ Should rebuild: {should_rebuild}")

    # 记录重建
    intervals = state.get_intervals()
    state.record_rebuild(intervals, 1000.0)
    assert state.deleted_points == 0
    print(f"✓ After rebuild: {state.deleted_points} deleted")

    print("\n✅ 维护功能测试通过\n")


def test_timestamps():
    """测试时间戳生成"""
    print("=" * 60)
    print("测试 4: 时间戳生成")
    print("=" * 60)

    from bench.metrics import generate_timestamps, get_latency_percentile

    # 生成时间戳
    timestamps = generate_timestamps(1000, event_rate=2000.0)
    assert len(timestamps) == 1000
    print(f"✓ Generated {len(timestamps)} timestamps")
    print(f"  First: {timestamps[0]}, Last: {timestamps[-1]}")
    print(f"  Interval: {timestamps[1] - timestamps[0]} us")

    # 计算延迟
    event_time = np.arange(0, 1000000, 1000, dtype=np.int64)
    processed_time = event_time + np.random.randint(100, 1000, size=len(event_time))

    p50 = get_latency_percentile(0.5, event_time, processed_time)
    p99 = get_latency_percentile(0.99, event_time, processed_time)
    print(f"✓ Latency P50: {p50:.2f} us")
    print(f"✓ Latency P99: {p99:.2f} us")

    print("\n✅ 时间戳功能测试通过\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("流式测评功能测试套件")
    print("=" * 60 + "\n")

    try:
        test_basic_operations()
        test_runbook_execution()
        test_maintenance()
        test_timestamps()

        print("=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
