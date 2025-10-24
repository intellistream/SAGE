"""
SAGE Performance Monitoring Usage Example
==========================================

这个示例展示如何使用 SAGE 的性能监控功能
"""

import time

from sage.kernel.runtime.monitoring import (
    RESOURCE_MONITOR_AVAILABLE,
    MetricsCollector,
    MetricsReporter,
    ResourceMonitor,
)


def example_metrics_collector():
    """示例1: 使用 MetricsCollector"""
    print("=" * 80)
    print("Example 1: MetricsCollector")
    print("=" * 80)

    # 创建指标收集器
    collector = MetricsCollector(
        name="example_task",
        window_size=1000,
        enable_detailed_tracking=True,
    )

    # 模拟处理10个数据包
    for i in range(10):
        # 记录包处理开始
        packet_id = collector.record_packet_start(
            packet_size=100 + i * 10,
        )

        # 模拟处理时间
        time.sleep(0.01 + i * 0.001)

        # 记录包处理结束
        success = i < 8  # 前8个成功，后2个失败
        collector.record_packet_end(
            packet_id=packet_id,
            success=success,
            error_type="TestError" if not success else None,
        )

    # 获取实时指标
    metrics = collector.get_real_time_metrics()
    print(f"\nTask: {metrics.task_name}")
    print(f"Total Processed: {metrics.total_packets_processed}")
    print(f"Total Failed: {metrics.total_packets_failed}")
    print(f"TPS: {metrics.packets_per_second:.2f}")
    print(f"Avg Latency: {metrics.avg_latency:.2f}ms")
    print(f"P99 Latency: {metrics.p99_latency:.2f}ms")
    print(f"Error Breakdown: {metrics.error_breakdown}")

    # 获取摘要
    summary = collector.get_summary()
    print(f"\nSummary: {summary}")


def example_resource_monitor():
    """示例2: 使用 ResourceMonitor"""
    print("\n" + "=" * 80)
    print("Example 2: ResourceMonitor")
    print("=" * 80)

    if not RESOURCE_MONITOR_AVAILABLE:
        print("⚠️ psutil not available, skipping resource monitor example")
        print("Install with: pip install psutil")
        return

    # 创建资源监控器
    monitor = ResourceMonitor(
        sampling_interval=0.5,
        sample_window=10,
        enable_auto_start=True,
    )

    # 等待收集一些样本
    print("\nCollecting resource samples...")
    time.sleep(3)

    # 获取当前使用情况
    cpu, memory = monitor.get_current_usage()
    print(f"\nCurrent Usage:")
    print(f"  CPU: {cpu:.2f}%")
    print(f"  Memory: {memory:.2f} MB")

    # 获取平均使用情况
    avg_cpu, avg_memory = monitor.get_average_usage()
    print(f"\nAverage Usage:")
    print(f"  CPU: {avg_cpu:.2f}%")
    print(f"  Memory: {avg_memory:.2f} MB")

    # 获取峰值使用情况
    peak_cpu, peak_memory = monitor.get_peak_usage()
    print(f"\nPeak Usage:")
    print(f"  CPU: {peak_cpu:.2f}%")
    print(f"  Memory: {peak_memory:.2f} MB")

    # 停止监控
    monitor.stop_monitoring()


def example_metrics_reporter():
    """示例3: 使用 MetricsReporter"""
    print("\n" + "=" * 80)
    print("Example 3: MetricsReporter")
    print("=" * 80)

    # 创建收集器
    collector = MetricsCollector(name="reporting_task")

    # 模拟一些数据
    for i in range(20):
        packet_id = collector.record_packet_start()
        time.sleep(0.005)
        collector.record_packet_end(packet_id, success=True)

    # 创建报告器（不自动启动）
    reporter = MetricsReporter(
        metrics_collector=collector,
        report_interval=60,
        enable_auto_report=False,
    )

    # 生成不同格式的报告
    print("\n--- JSON Format ---")
    json_report = reporter.generate_report(format="json")
    print(json_report[:500] + "..." if len(json_report) > 500 else json_report)

    print("\n--- Human-Readable Format ---")
    human_report = reporter.generate_report(format="human")
    print(human_report)

    print("\n--- Prometheus Format ---")
    prom_report = reporter.generate_report(format="prometheus")
    print(prom_report[:500] + "..." if len(prom_report) > 500 else prom_report)


def example_integrated_monitoring():
    """示例4: 集成监控（收集器 + 资源监控 + 报告器）"""
    print("\n" + "=" * 80)
    print("Example 4: Integrated Monitoring")
    print("=" * 80)

    # 创建收集器
    collector = MetricsCollector(
        name="integrated_task",
        window_size=100,
    )

    # 创建资源监控器（如果可用）
    resource_monitor = None
    if RESOURCE_MONITOR_AVAILABLE:
        resource_monitor = ResourceMonitor(
            sampling_interval=0.5,
            enable_auto_start=True,
        )

    # 创建报告器
    reporter = MetricsReporter(
        metrics_collector=collector,
        resource_monitor=resource_monitor,
        enable_auto_report=False,
    )

    # 模拟任务执行
    print("\nSimulating task execution...")
    for i in range(50):
        packet_id = collector.record_packet_start(packet_size=100)

        # 模拟不同的处理时间
        time.sleep(0.01 + (i % 5) * 0.002)

        # 模拟偶尔的失败
        success = (i % 10) != 0
        collector.record_packet_end(
            packet_id,
            success=success,
            error_type="SimulatedError" if not success else None,
        )

    # 等待资源监控收集数据
    if resource_monitor:
        time.sleep(2)

    # 生成综合报告
    print("\n" + "=" * 80)
    print("Performance Report")
    print("=" * 80)
    report = reporter.generate_report(format="human")
    print(report)

    # 清理
    if resource_monitor:
        resource_monitor.stop_monitoring()


def main():
    """运行所有示例"""
    print("\n" + "=" * 80)
    print("SAGE Performance Monitoring Examples")
    print("=" * 80)

    try:
        example_metrics_collector()
        example_resource_monitor()
        example_metrics_reporter()
        example_integrated_monitoring()

        print("\n" + "=" * 80)
        print("All examples completed successfully! ✓")
        print("=" * 80)
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
