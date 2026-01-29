#!/usr/bin/env python3
"""
Workload 4 简化测试脚本 - 用于验证基本功能
"""

import sys
from pathlib import Path

# 添加 SAGE 到路径
SAGE_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-kernel" / "src"))
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-common" / "src"))
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-libs" / "src"))
sys.path.insert(0, str(SAGE_ROOT / "packages" / "sage-benchmark" / "src"))

from workload4.config import Workload4Config
from workload4.pipeline import Workload4Pipeline

def main():
    print("=" * 80)
    print("Workload 4 简化测试")
    print("=" * 80)
    
    # 创建最小配置
    config = Workload4Config(
        num_tasks=10,  # 只运行 10 个任务
        duration=60,   # 只运行 60 秒
        query_qps=5.0,  # 降低 QPS
        doc_qps=3.0,
        use_remote=True,
        num_nodes=1,
        enable_detailed_metrics=False,
    )
    
    print("\n配置:")
    print(f"  任务数: {config.num_tasks}")
    print(f"  时长: {config.duration}s")
    print(f"  Query QPS: {config.query_qps}")
    print(f"  Doc QPS: {config.doc_qps}")
    print(f"  节点数: {config.num_nodes}")
    
    # 构建 pipeline
    print("\n正在构建 Pipeline...")
    pipeline = Workload4Pipeline(config)
    
    try:
        pipeline.build(name="workload4_test")
        print("✓ Pipeline 构建成功")
        
        print("\n正在运行...")
        metrics = pipeline.run()
        
        print("\n✓ 测试完成!")
        if metrics:
            print(f"  Total tasks: {metrics.total_tasks}")
            print(f"  Success: {metrics.success_count}")
            print(f"  Failed: {metrics.fail_count}")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
