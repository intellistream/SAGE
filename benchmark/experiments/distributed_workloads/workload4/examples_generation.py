"""
Workload 4 Generation 组件使用示例

演示如何使用 BatchLLMGenerator 和 Workload4MetricsSink。
"""

import sys
import time
from pathlib import Path

# 添加当前目录到 path
sys.path.insert(0, str(Path(__file__).parent))


def example_batch_llm_generator():
    """示例：批量 LLM 生成"""
    from generation import BatchLLMGenerator, create_mock_batch_context

    print("=" * 80)
    print("示例 1: 批量 LLM 生成")
    print("=" * 80)

    # 创建生成器
    generator = BatchLLMGenerator(
        llm_base_url="http://11.11.11.7:8904/v1",
        llm_model="Qwen/Qwen2.5-3B-Instruct",
        max_tokens=120,
        temperature=0.7,
    )

    # 创建 Mock BatchContext
    print("\n创建测试批次（3个查询）...")
    batch_context = create_mock_batch_context(num_items=3)

    # 执行生成
    print("\n调用 LLM 生成回复...")
    start_time = time.time()
    results = generator.execute(batch_context)
    elapsed = time.time() - start_time

    # 打印结果
    print(f"\n生成完成，耗时: {elapsed:.2f}s")
    print(f"生成 {len(results)} 个回复\n")

    for i, (query_id, response, metrics) in enumerate(results, 1):
        print(f"--- 结果 {i} ---")
        print(f"Query ID: {query_id}")
        print(f"Response: {response[:100]}...")
        print(f"E2E Latency: {metrics.end_to_end_time * 1000:.2f}ms")
        print()

    # 打印统计
    stats = generator.get_stats()
    print("生成统计:")
    print(f"  总调用次数: {stats['total_calls']}")
    print(f"  失败次数: {stats['failed_calls']}")
    print(f"  总 Token 数: {stats['total_tokens']}")
    print(f"  平均 Token/调用: {stats['avg_tokens_per_call']:.1f}")


def example_workload4_metrics_sink():
    """示例：指标收集 Sink"""
    from generation import Workload4MetricsSink
    from models import Workload4Metrics

    print("\n" + "=" * 80)
    print("示例 2: 指标收集 Sink")
    print("=" * 80)

    # 创建输出目录
    output_dir = Path("/tmp/sage_workload4_example")

    # 创建 Sink
    print(f"\n创建 MetricsSink，输出目录: {output_dir}")
    sink = Workload4MetricsSink(
        metrics_output_dir=str(output_dir),
        verbose=True,
    )

    # 模拟收集指标
    print("\n模拟收集 20 个任务的指标...")
    for i in range(20):
        # 创建指标
        metrics = Workload4Metrics(
            task_id=f"task_{i}",
            query_id=f"query_{i}",
            query_arrival_time=time.time(),
            join_time=time.time() + 0.05 + i * 0.001,
            vdb1_start_time=time.time() + 0.06,
            vdb1_end_time=time.time() + 0.15,
            vdb2_start_time=time.time() + 0.06,
            vdb2_end_time=time.time() + 0.14,
            clustering_time=time.time() + 0.17,
            reranking_time=time.time() + 0.19,
            generation_time=time.time() + 0.25,
            end_to_end_time=0.25 + i * 0.01,
            join_matched_docs=5 + i % 3,
            vdb1_results=10 + i % 5,
            vdb2_results=8 + i % 4,
            graph_nodes_visited=15 + i % 6,
            clusters_found=3 + i % 2,
            duplicates_removed=2 + i % 3,
            final_top_k=10,
            semantic_join_score=0.80 + i * 0.01,
            final_rerank_score=0.85 + i * 0.005,
            diversity_score=0.75 + i * 0.01,
        )

        # 收集指标
        data = (f"query_{i}", f"Response for query {i}", metrics)
        sink.execute(data)

        time.sleep(0.05)  # 模拟处理间隔

    # 关闭 Sink
    print("\n关闭 Sink，生成汇总报告...")
    sink.close()

    # 打印统计
    print("\n最终统计:")
    stats = sink.get_stats()
    print(f"  处理任务数: {stats['count']}")
    print(f"  运行时间: {stats['elapsed_seconds']:.2f}s")
    print(f"  吞吐量: {stats['throughput_qps']:.2f} QPS")

    # 列出输出文件
    print("\n输出文件:")
    for file in sorted(output_dir.glob("*")):
        print(f"  - {file.name}")


def example_end_to_end():
    """示例：端到端流程"""
    print("\n" + "=" * 80)
    print("示例 3: 端到端流程（生成 + 收集）")
    print("=" * 80)

    from generation import (
        BatchLLMGenerator,
        Workload4MetricsSink,
        create_mock_batch_context,
    )

    # 创建组件
    output_dir = Path("/tmp/sage_workload4_e2e")

    generator = BatchLLMGenerator(
        llm_base_url="http://11.11.11.7:8904/v1",
        llm_model="Qwen/Qwen2.5-3B-Instruct",
        max_tokens=120,
    )

    sink = Workload4MetricsSink(
        metrics_output_dir=str(output_dir),
        verbose=True,
    )

    # 处理多个批次
    print("\n处理 3 个批次...")
    for batch_id in range(3):
        print(f"\n--- 批次 {batch_id + 1} ---")

        # 创建批次
        batch_context = create_mock_batch_context(num_items=5)

        # 生成回复
        results = generator.execute(batch_context)

        # 收集指标
        for result in results:
            sink.execute(result)

        time.sleep(0.5)  # 批次间隔

    # 关闭 Sink
    print("\n关闭 Sink...")
    sink.close()

    print(f"\n✓ 完成! 输出目录: {output_dir}")


def example_custom_metrics():
    """示例：自定义指标字段"""
    from models import Workload4Metrics

    print("\n" + "=" * 80)
    print("示例 4: 自定义指标字段")
    print("=" * 80)

    # 创建指标
    metrics = Workload4Metrics(
        task_id="custom_task_1",
        query_id="custom_query_1",
        query_arrival_time=time.time(),
        join_time=time.time() + 0.1,
        vdb1_start_time=time.time() + 0.11,
        vdb1_end_time=time.time() + 0.2,
        vdb2_start_time=time.time() + 0.11,
        vdb2_end_time=time.time() + 0.19,
        graph_start_time=time.time() + 0.2,
        graph_end_time=time.time() + 0.3,
        clustering_time=time.time() + 0.32,
        reranking_time=time.time() + 0.35,
        batch_time=time.time() + 0.36,
        generation_time=time.time() + 0.5,
        end_to_end_time=0.5,
        join_matched_docs=8,
        vdb1_results=15,
        vdb2_results=12,
        graph_nodes_visited=25,
        clusters_found=4,
        duplicates_removed=5,
        final_top_k=10,
        cpu_time_ms=450.0,
        memory_peak_mb=256.0,
        semantic_join_score=0.85,
        final_rerank_score=0.88,
        diversity_score=0.78,
    )

    # 计算延迟
    latencies = metrics.compute_latencies()

    print("\n指标详情:")
    print(f"  Task ID: {metrics.task_id}")
    print(f"  Query ID: {metrics.query_id}")
    print(f"  端到端延迟: {metrics.end_to_end_time * 1000:.2f}ms")
    print()
    print("各阶段延迟:")
    for stage, latency in latencies.items():
        print(f"  {stage}: {latency * 1000:.2f}ms")
    print()
    print("中间结果:")
    print(f"  Join 匹配文档: {metrics.join_matched_docs}")
    print(f"  VDB1 结果: {metrics.vdb1_results}")
    print(f"  VDB2 结果: {metrics.vdb2_results}")
    print(f"  图遍历节点: {metrics.graph_nodes_visited}")
    print(f"  聚类数: {metrics.clusters_found}")
    print(f"  去重数: {metrics.duplicates_removed}")
    print(f"  最终 Top-K: {metrics.final_top_k}")
    print()
    print("质量指标:")
    print(f"  语义 Join 分数: {metrics.semantic_join_score:.4f}")
    print(f"  最终重排序分数: {metrics.final_rerank_score:.4f}")
    print(f"  多样性分数: {metrics.diversity_score:.4f}")


def example_error_handling():
    """示例：错误处理"""
    from generation import BatchLLMGenerator, create_mock_batch_context

    print("\n" + "=" * 80)
    print("示例 5: 错误处理")
    print("=" * 80)

    # 创建生成器（使用不存在的 URL）
    print("\n创建生成器（使用不存在的 LLM 服务）...")
    generator = BatchLLMGenerator(
        llm_base_url="http://localhost:9999/v1",
        llm_model="test-model",
        max_tokens=50,
        max_retries=2,
    )

    # 创建批次
    batch_context = create_mock_batch_context(num_items=2)

    # 执行生成（会失败）
    print("\n执行生成（预期失败）...")
    results = generator.execute(batch_context)

    # 打印结果
    print(f"\n生成完成，返回 {len(results)} 个结果")
    for i, (query_id, response, metrics) in enumerate(results, 1):
        print(f"\n--- 结果 {i} ---")
        print(f"Query ID: {query_id}")
        print(f"Response: {response}")
        print(f"包含错误: {'[Error:' in response}")

    # 打印统计
    stats = generator.get_stats()
    print("\n错误统计:")
    print(f"  总调用次数: {stats['total_calls']}")
    print(f"  失败次数: {stats['failed_calls']}")
    print(f"  失败率: {stats['failed_calls'] / stats['total_calls'] * 100:.1f}%")


if __name__ == "__main__":
    import sys

    print("\nWorkload 4 Generation 组件示例")
    print("=" * 80)

    # 根据命令行参数选择示例
    if len(sys.argv) > 1:
        example_name = sys.argv[1]

        examples = {
            "1": example_batch_llm_generator,
            "2": example_workload4_metrics_sink,
            "3": example_end_to_end,
            "4": example_custom_metrics,
            "5": example_error_handling,
        }

        if example_name in examples:
            examples[example_name]()
        else:
            print(f"未知示例: {example_name}")
            print("可用示例: 1, 2, 3, 4, 5")
    else:
        # 运行所有示例
        print("\n运行所有示例...\n")

        # 示例 4 和 5 不需要真实服务
        example_custom_metrics()
        example_error_handling()

        # 示例 1, 2, 3 需要真实 LLM 服务（可选）
        try:
            # 尝试连接 LLM 服务
            import requests

            response = requests.get("http://11.11.11.7:8904/health", timeout=2)
            if response.status_code == 200:
                print("\n✓ LLM 服务可用，运行完整示例...")
                example_batch_llm_generator()
                example_workload4_metrics_sink()
                example_end_to_end()
            else:
                print("\n⚠ LLM 服务不可用，跳过示例 1, 2, 3")
        except Exception:
            print("\n⚠ LLM 服务不可用，跳过示例 1, 2, 3")

    print("\n" + "=" * 80)
    print("所有示例完成!")
    print("=" * 80)
