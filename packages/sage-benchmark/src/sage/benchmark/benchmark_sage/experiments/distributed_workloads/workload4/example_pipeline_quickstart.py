#!/usr/bin/env python3
"""
Workload 4 Pipeline 快速示例

展示如何使用 Pipeline 工厂构建和运行 Workload 4。
"""

import sys
from pathlib import Path

# 添加路径
workload4_dir = Path(__file__).parent
sys.path.insert(0, str(workload4_dir))

try:
    from pipeline import (
        Workload4Config,
        Workload4Pipeline,
        create_workload4_pipeline,
        run_workload4,
        register_all_services,
    )
    from config import Workload4Config
except ImportError:
    # 如果在包内运行
    from .pipeline import (
        Workload4Config,
        Workload4Pipeline,
        create_workload4_pipeline,
        run_workload4,
        register_all_services,
    )
    from .config import Workload4Config


def example_1_minimal():
    """示例 1: 最小测试"""
    print("\n" + "=" * 80)
    print("Example 1: Minimal Test")
    print("=" * 80)
    
    pipeline = create_workload4_pipeline(
        num_tasks=5,
        duration=30,
        use_remote=False,  # Local 环境
        query_qps=1.0,
        doc_qps=1.0
    )
    
    pipeline.build(name="example_minimal")
    metrics = pipeline.run()
    
    print(f"\n✓ Completed in {metrics.end_to_end_time:.2f}s")


def example_2_custom_config():
    """示例 2: 自定义配置"""
    print("\n" + "=" * 80)
    print("Example 2: Custom Configuration")
    print("=" * 80)
    
    config = Workload4Config(
        num_tasks=10,
        duration=60,
        use_remote=False,
        query_qps=2.0,
        doc_qps=2.0,
        join_window_seconds=30,  # 较小的窗口
        rerank_top_k=10,
    )
    
    pipeline = Workload4Pipeline(config)
    pipeline.build(name="example_custom")
    metrics = pipeline.run()
    
    print(f"\n✓ Completed in {metrics.end_to_end_time:.2f}s")


def example_3_service_registration_only():
    """示例 3: 仅注册服务（不运行 Pipeline）"""
    print("\n" + "=" * 80)
    print("Example 3: Service Registration Only")
    print("=" * 80)
    
    from sage.kernel.api.local_environment import LocalEnvironment
    
    env = LocalEnvironment(name="example_services")
    config = Workload4Config()
    
    results = register_all_services(env, config)
    
    print(f"\nService Registration Results:")
    for service_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {service_name}")
    
    print(f"\n✓ {sum(results.values())}/{len(results)} services registered successfully")


def example_4_convenience_api():
    """示例 4: 便捷 API（一键运行）"""
    print("\n" + "=" * 80)
    print("Example 4: Convenience API")
    print("=" * 80)
    
    # 注意: 这会实际运行 Pipeline
    # 在这个示例中我们不执行，只展示用法
    
    code = """
    # 一键运行完整工作流
    metrics = run_workload4(
        num_tasks=100,
        duration=300,
        use_remote=True,
        num_nodes=8,
        query_qps=40.0,
        doc_qps=25.0
    )
    
    print(f"End-to-End Time: {metrics.end_to_end_time}s")
    """
    
    print("\nCode Example:")
    print(code)
    print("\n(Not executed in this demo)")


def main():
    """运行所有示例"""
    print("\n" + "=" * 80)
    print("Workload 4 Pipeline Examples")
    print("=" * 80)
    print("This script demonstrates various ways to use the Workload 4 Pipeline.")
    print("=" * 80)
    
    # 示例 3: 仅注册服务（不运行 Pipeline，避免耗时）
    example_3_service_registration_only()
    
    # 示例 4: 便捷 API（仅展示用法）
    example_4_convenience_api()
    
    # 其他示例需要实际运行 Pipeline，这里跳过
    # 如果需要，可以取消注释运行
    # example_1_minimal()
    # example_2_custom_config()
    
    print("\n" + "=" * 80)
    print("All Examples Completed!")
    print("=" * 80)
    print("\nTo run the full examples (including Pipeline execution):")
    print("  1. Uncomment example_1_minimal() and example_2_custom_config()")
    print("  2. Ensure embedding and LLM services are running")
    print("  3. Run: python example_pipeline_quickstart.py")
    print("=" * 80)


if __name__ == "__main__":
    main()
