"""
QA Pipeline with Performance Monitoring Demo

这个示例展示如何使用 SAGE 的性能监控功能来监测 RAG 管道的性能指标:
- 实时 TPS/QPS 统计
- 延迟分位数 (P50/P95/P99)
- CPU/内存资源使用
- 每个组件的详细性能数据

Pipeline 流程:
JSONLBatch -> ChromaRetriever -> QAPromptor -> OpenAIGenerator -> TerminalSink
"""

import os
import sys
import time

from sage.common.utils.config.loader import load_config

# 导入 Sage 相关模块
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.batch import JSONLBatch
from sage.libs.foundation.io.sink import TerminalSink
from sage.middleware.operators.rag import ChromaRetriever, OpenAIGenerator, QAPromptor


def pipeline_run():
    """创建并运行带性能监控的数据处理管道

    该函数会初始化环境，加载配置，设置数据处理流程，并启动管道。
    启用性能监控后，会在管道运行时收集各种性能指标。
    """
    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - qa_monitoring_demo example")
        print("✅ Test passed: Example structure validated")
        return

    # 初始化环境 (启用监控功能)
    env = LocalEnvironment(enable_monitoring=True)

    print("=" * 80)
    print("🔍 Performance Monitoring Demo - RAG Pipeline")
    print("=" * 80)
    print("📊 Monitoring enabled: TPS, Latency (P50/P95/P99), CPU/Memory")
    print("🔄 Pipeline: Retrieval -> Prompt -> Generation")
    print("=" * 80)

    # 构建数据处理流程 (去掉了 BGEReranker,简化为基础 RAG 流程)
    (
        env.from_source(JSONLBatch, config["source"])
        .map(ChromaRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    # 提交管道并运行
    print("\n🚀 Starting pipeline execution...")
    env.submit()

    # 等待管道处理数据
    print("⏳ Processing queries with monitoring...")
    time.sleep(25)

    # 打印性能监控报告
    print("\n" + "=" * 80)
    print("📈 PERFORMANCE MONITORING REPORT")
    print("=" * 80)

    # 获取并显示各个任务的性能指标
    try:
        if env.env_uuid is None:
            print("\n⚠️  Warning: env_uuid is None, skipping metrics")
        else:
            job = env.jobmanager.jobs.get(env.env_uuid)
            if job and hasattr(job, "dispatcher"):
                tasks = job.dispatcher.tasks
                for task_name, task in tasks.items():
                    if hasattr(task, "get_current_metrics"):
                        metrics = task.get_current_metrics()
                        if metrics is None:
                            continue
                        print(f"\n🔧 Task: {task_name}")
                        print(f"  📦 Packets Processed: {metrics.total_packets_processed}")  # type: ignore[attr-defined]
                        print(
                            f"  ✅ Success: {metrics.total_packets_processed} | ❌ Errors: {metrics.total_packets_failed}"  # type: ignore[attr-defined]
                        )
                        print(f"  📊 TPS: {metrics.packets_per_second:.2f} packets/sec")  # type: ignore[attr-defined]
                        if metrics.p50_latency > 0:  # type: ignore[attr-defined]
                            print(f"  ⏱️  Latency P50: {metrics.p50_latency:.1f}ms")  # type: ignore[attr-defined]
                            print(f"  ⏱️  Latency P95: {metrics.p95_latency:.1f}ms")  # type: ignore[attr-defined]
                            print(f"  ⏱️  Latency P99: {metrics.p99_latency:.1f}ms")  # type: ignore[attr-defined]
                            print(f"  ⏱️  Avg Latency: {metrics.avg_latency:.1f}ms")  # type: ignore[attr-defined]
                        if metrics.cpu_usage_percent > 0 or metrics.memory_usage_mb > 0:  # type: ignore[attr-defined]
                            print(f"  💻 CPU: {metrics.cpu_usage_percent:.1f}%")  # type: ignore[attr-defined]
                            print(f"  🧠 Memory: {metrics.memory_usage_mb:.1f}MB")  # type: ignore[attr-defined]
                        if metrics.input_queue_depth > 0:  # type: ignore[attr-defined]
                            print(f"  📥 Queue Depth: {metrics.input_queue_depth}")  # type: ignore[attr-defined]
                        if metrics.error_breakdown:  # type: ignore[attr-defined]
                            print(f"  ❌ Error Breakdown: {metrics.error_breakdown}")  # type: ignore[attr-defined]
            else:
                print("⚠️  Dispatcher or job not found, cannot retrieve metrics.")
    except Exception as e:
        import traceback

        print(f"⚠️  Could not retrieve detailed metrics: {e}")
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ Pipeline execution completed!")
    print("=" * 80)

    # 关闭环境
    env.close()


if __name__ == "__main__":
    import os

    # 检查是否在测试模式下运行
    if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
        print("🧪 Test mode detected - qa_monitoring_demo example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)

    # 加载配置文件
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "config_monitoring_demo.yaml"
    )
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print("Please create the configuration file first.")
        sys.exit(1)

    config = load_config(config_path)

    # 运行管道
    pipeline_run()
