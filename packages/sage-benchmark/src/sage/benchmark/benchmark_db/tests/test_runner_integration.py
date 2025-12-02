#!/usr/bin/env python3
"""
测试 BenchmarkRunner 与 runbook 的集成

验证 runner.py 能否正确执行实际格式的 runbook
"""

import sys
from pathlib import Path

import numpy as np
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bench.runner import BenchmarkRunner

from sage.benchmark.benchmark_db.datasets.loaders import load_dataset


def create_mock_algorithm():
    """创建一个模拟算法用于测试"""

    class MockAlgorithm:
        def __init__(self):
            self.name = "mock_algorithm"
            self.data = []
            self.index_built = False

        def fit(self, X):
            """构建索引"""
            self.data = X.copy()
            self.index_built = True
            print(f"  MockAlgorithm: 构建索引，数据量 {len(X)}")

        def batch_insert(self, X):
            """批量插入"""
            if not self.index_built:
                self.fit(X)
            else:
                self.data = np.vstack([self.data, X])
            print(f"  MockAlgorithm: 批量插入 {len(X)} 条数据，当前总量 {len(self.data)}")

        def query(self, X, k):
            """查询"""
            n = len(X)
            # 返回随机结果
            results = np.random.randint(0, max(len(self.data), 1), size=(n, k))
            print(f"  MockAlgorithm: 查询 {n} 条，k={k}")
            return results

        def batch_delete(self, ids):
            """批量删除"""
            print(f"  MockAlgorithm: 删除 {len(ids)} 条数据")

        def __str__(self):
            return self.name

    return MockAlgorithm()


def test_runbook_execution():
    """测试 runbook 执行"""

    print("=" * 80)
    print("测试 BenchmarkRunner 执行 Runbook")
    print("=" * 80)

    # 1. 创建模拟算法
    algorithm = create_mock_algorithm()

    # 2. 加载一个小数据集
    try:
        dataset = load_dataset("random-xs")
        print(f"\n✓ 数据集加载成功: {dataset.short_name()}")
    except Exception as e:
        print(f"\n✗ 数据集加载失败: {e}")
        return

    # 3. 加载实际的 runbook
    runbook_path = Path(__file__).resolve().parent.parent / "runbooks" / "simple.yaml"

    if not runbook_path.exists():
        print(f"\n✗ Runbook 文件不存在: {runbook_path}")
        return

    with open(runbook_path) as f:
        runbook = yaml.safe_load(f)

    print("✓ Runbook 加载成功: simple.yaml")

    # 4. 创建 runner
    runner = BenchmarkRunner(
        algorithm=algorithm,
        dataset=dataset,
        k=10,
        save_timestamps=False,
        output_dir="/tmp/test_runner",
    )

    print("✓ BenchmarkRunner 创建成功")

    # 5. 执行 runbook（使用 random-xs 数据集配置）
    print("\n开始执行 runbook (数据集: random-xs)...")

    try:
        metrics = runner.run_runbook(runbook, dataset_name="random-xs")

        print(f"\n{'=' * 80}")
        print("执行完成！")
        print(f"{'=' * 80}")
        print(f"算法: {metrics.algorithm_name}")
        print(f"数据集: {metrics.dataset_name}")
        print(f"总时间: {runner.attrs['totalTime']:.2f} 秒")
        print("操作统计:")
        for op, count in runner.counts.items():
            if count > 0:
                print(f"  - {op}: {count}")

    except Exception as e:
        print(f"\n✗ Runbook 执行失败: {e}")
        import traceback

        traceback.print_exc()


def test_enable_scenario():
    """测试 enableScenario 操作"""

    print("\n" + "=" * 80)
    print("测试 enableScenario 操作")
    print("=" * 80)

    algorithm = create_mock_algorithm()
    dataset = load_dataset("random-xs")

    runner = BenchmarkRunner(
        algorithm=algorithm,
        dataset=dataset,
        k=10,
        save_timestamps=False,
        output_dir="/tmp/test_runner",
    )

    # 测试 enableScenario 的新格式
    runbook = {
        "random-xs": {
            "max_pts": 10000,
            1: {"operation": "startHPC"},
            2: {"operation": "initial", "start": 0, "end": 5000},
            3: {"operation": "enableScenario", "randomDrop": 1, "randomDropProb": 0.05},
            4: {
                "operation": "batch_insert",
                "start": 5000,
                "end": 10000,
                "batchSize": 2500,
                "eventRate": 10000,
            },
            5: {"operation": "waitPending"},
            6: {"operation": "search"},
            7: {"operation": "endHPC"},
        }
    }

    try:
        _ = runner.run_runbook(runbook, dataset_name="random-xs")

        # 检查是否正确启用了随机丢弃
        if runner.random_drop:
            print(f"\n✓ 随机丢弃已启用，概率: {runner.random_drop_prob}")
        else:
            print("\n✗ 随机丢弃未启用")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_runbook_execution()
    test_enable_scenario()
