#!/usr/bin/env python3
"""
Workload 4 最小测试 - 不使用真实 FAISS 索引
"""

import sys
from pathlib import Path

# 添加路径
SAGE_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-kernel" / "src"))
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-common" / "src"))

from workload4.config import Workload4Config
from workload4.pipeline import Workload4Pipeline


def test_minimal():
    """最小测试：构建 + 提交（不运行真实数据）"""
    print("=" * 80)
    print("Workload 4 最小测试")
    print("=" * 80)

    # 使用最小配置
    config = Workload4Config(
        num_tasks=2,
        duration=5,
        query_qps=1.0,
        doc_qps=2.0,
        use_remote=True,
        num_nodes=8,
        vdb_top_k=5,  # 减小 top-k
        # 使用 mock 数据而不是真实 FiQA
        vdb_index_dir="/tmp/mock_vdb",  # 不存在的路径，会使用 mock
    )

    print(f"Config: {config.num_tasks} tasks, {config.duration}s")
    print(f"VDB Index Dir: {config.vdb_index_dir}")

    # 创建 pipeline
    pipeline = Workload4Pipeline(config)

    print("\n构建 Pipeline...")
    pipeline.build(name="workload4_minimal_test")

    print("\n✓ Pipeline 构建成功")
    print(f"Environment: {type(pipeline.env).__name__}")

    # 尝试提交（这里会测试序列化）
    print("\n提交 Pipeline...")
    try:
        pipeline.env.submit()
        print("✓ Pipeline 提交成功！")
        return 0
    except Exception as e:
        print(f"✗ Pipeline 提交失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_minimal())
