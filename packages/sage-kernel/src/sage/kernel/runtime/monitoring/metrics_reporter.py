"""
Metrics Reporter
================

性能指标汇报器，支持：
- 定期汇报
- 多种导出格式（JSON, Prometheus, CSV, 人类可读）
- 自定义汇报回调
"""

import csv
import io
import json
import threading
import time
from collections.abc import Callable

from sage.kernel.runtime.monitoring.metrics import TaskPerformanceMetrics
from sage.kernel.runtime.monitoring.metrics_collector import MetricsCollector
from sage.kernel.runtime.monitoring.resource_monitor import ResourceMonitor


class MetricsReporter:
    """性能指标汇报器"""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        resource_monitor: ResourceMonitor | None = None,
        report_interval: int = 60,
        enable_auto_report: bool = False,
        report_callback: Callable[[str], None] | None = None,
    ):
        """
        初始化指标汇报器

        Args:
            metrics_collector: 指标收集器
            resource_monitor: 资源监控器（可选）
            report_interval: 汇报间隔（秒）
            enable_auto_report: 是否启用自动汇报
            report_callback: 汇报回调函数
        """
        self.metrics_collector = metrics_collector
        self.resource_monitor = resource_monitor
        self.report_interval = report_interval
        self.report_callback = report_callback

        # 汇报线程
        self._report_thread: threading.Thread | None = None
        self._running = False

        if enable_auto_report:
            self.start_reporting()

    def start_reporting(self) -> None:
        """启动定期汇报"""
        if self._running:
            return

        self._running = True
        self._report_thread = threading.Thread(
            target=self._report_loop, daemon=True, name="MetricsReporter"
        )
        self._report_thread.start()

    def stop_reporting(self) -> None:
        """停止定期汇报"""
        if not self._running:
            return

        self._running = False
        if self._report_thread:
            self._report_thread.join(timeout=5.0)
            self._report_thread = None

    def _report_loop(self) -> None:
        """汇报循环"""
        while self._running:
            try:
                report = self.generate_report(format="human")
                if self.report_callback:
                    self.report_callback(report)
            except Exception as e:
                # 汇报失败不影响监控
                print(f"Error generating metrics report: {e}")

            time.sleep(self.report_interval)

    def generate_report(self, format: str = "json") -> str:
        """
        生成性能报告

        Args:
            format: 输出格式 ("json", "prometheus", "csv", "human")

        Returns:
            格式化的报告字符串
        """
        # 获取指标
        metrics = self.metrics_collector.get_real_time_metrics()

        # 添加资源监控数据
        if self.resource_monitor:
            cpu, memory = self.resource_monitor.get_current_usage()
            metrics.cpu_usage_percent = cpu
            metrics.memory_usage_mb = memory

        # 根据格式生成报告
        if format == "json":
            return self._format_json(metrics)
        elif format == "prometheus":
            return self._format_prometheus(metrics)
        elif format == "csv":
            return self._format_csv(metrics)
        elif format == "human":
            return self._format_human(metrics)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_json(self, metrics: TaskPerformanceMetrics) -> str:
        """JSON格式"""
        return json.dumps(metrics.to_dict(), indent=2)

    def _format_prometheus(self, metrics: TaskPerformanceMetrics) -> str:
        """Prometheus格式"""
        lines = []
        task_name = metrics.task_name

        # 基础指标
        lines.append("# HELP sage_task_uptime_seconds Task uptime in seconds")
        lines.append("# TYPE sage_task_uptime_seconds gauge")
        lines.append(f'sage_task_uptime_seconds{{task="{task_name}"}} {metrics.uptime}')

        lines.append("# HELP sage_task_packets_processed_total Total packets processed")
        lines.append("# TYPE sage_task_packets_processed_total counter")
        lines.append(
            f'sage_task_packets_processed_total{{task="{task_name}"}} {metrics.total_packets_processed}'
        )

        lines.append("# HELP sage_task_packets_failed_total Total packets failed")
        lines.append("# TYPE sage_task_packets_failed_total counter")
        lines.append(
            f'sage_task_packets_failed_total{{task="{task_name}"}} {metrics.total_packets_failed}'
        )

        lines.append("# HELP sage_task_throughput_pps Current throughput in packets per second")
        lines.append("# TYPE sage_task_throughput_pps gauge")
        lines.append(f'sage_task_throughput_pps{{task="{task_name}"}} {metrics.packets_per_second}')

        # 延迟指标
        lines.append("# HELP sage_task_latency_milliseconds Task latency in milliseconds")
        lines.append("# TYPE sage_task_latency_milliseconds summary")
        lines.append(
            f'sage_task_latency_milliseconds{{task="{task_name}",quantile="0.5"}} {metrics.p50_latency}'
        )
        lines.append(
            f'sage_task_latency_milliseconds{{task="{task_name}",quantile="0.95"}} {metrics.p95_latency}'
        )
        lines.append(
            f'sage_task_latency_milliseconds{{task="{task_name}",quantile="0.99"}} {metrics.p99_latency}'
        )

        # 资源指标
        lines.append("# HELP sage_task_cpu_percent CPU usage percentage")
        lines.append("# TYPE sage_task_cpu_percent gauge")
        lines.append(f'sage_task_cpu_percent{{task="{task_name}"}} {metrics.cpu_usage_percent}')

        lines.append("# HELP sage_task_memory_megabytes Memory usage in megabytes")
        lines.append("# TYPE sage_task_memory_megabytes gauge")
        lines.append(f'sage_task_memory_megabytes{{task="{task_name}"}} {metrics.memory_usage_mb}')

        # 队列指标
        lines.append("# HELP sage_task_queue_depth Current queue depth")
        lines.append("# TYPE sage_task_queue_depth gauge")
        lines.append(f'sage_task_queue_depth{{task="{task_name}"}} {metrics.input_queue_depth}')

        return "\n".join(lines)

    def _format_csv(self, metrics: TaskPerformanceMetrics) -> str:
        """CSV格式"""
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入标题行
        writer.writerow(
            [
                "timestamp",
                "task_name",
                "uptime",
                "total_processed",
                "total_failed",
                "tps",
                "min_latency_ms",
                "max_latency_ms",
                "avg_latency_ms",
                "p50_latency_ms",
                "p95_latency_ms",
                "p99_latency_ms",
                "cpu_percent",
                "memory_mb",
                "queue_depth",
            ]
        )

        # 写入数据行
        writer.writerow(
            [
                metrics.timestamp,
                metrics.task_name,
                metrics.uptime,
                metrics.total_packets_processed,
                metrics.total_packets_failed,
                metrics.packets_per_second,
                metrics.min_latency,
                metrics.max_latency,
                metrics.avg_latency,
                metrics.p50_latency,
                metrics.p95_latency,
                metrics.p99_latency,
                metrics.cpu_usage_percent,
                metrics.memory_usage_mb,
                metrics.input_queue_depth,
            ]
        )

        return output.getvalue()

    def _format_human(self, metrics: TaskPerformanceMetrics) -> str:
        """人类可读格式"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"Performance Report: {metrics.task_name}")
        lines.append("=" * 80)
        lines.append(
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(metrics.timestamp))}"
        )
        lines.append(f"Uptime: {metrics.uptime:.2f}s")
        lines.append("")

        lines.append("Throughput:")
        lines.append(f"  Total Processed: {metrics.total_packets_processed}")
        lines.append(f"  Total Failed: {metrics.total_packets_failed}")
        success_rate = (
            (metrics.total_packets_processed - metrics.total_packets_failed)
            / metrics.total_packets_processed
            * 100
            if metrics.total_packets_processed > 0
            else 0
        )
        lines.append(f"  Success Rate: {success_rate:.2f}%")
        lines.append(f"  Current TPS: {metrics.packets_per_second:.2f}")
        lines.append(f"  Last Minute TPS: {metrics.last_minute_tps:.2f}")
        lines.append(f"  Last 5min TPS: {metrics.last_5min_tps:.2f}")
        lines.append(f"  Last Hour TPS: {metrics.last_hour_tps:.2f}")
        lines.append("")

        lines.append("Latency (milliseconds):")
        lines.append(f"  Min: {metrics.min_latency:.2f}")
        lines.append(f"  Max: {metrics.max_latency:.2f}")
        lines.append(f"  Avg: {metrics.avg_latency:.2f}")
        lines.append(f"  P50: {metrics.p50_latency:.2f}")
        lines.append(f"  P95: {metrics.p95_latency:.2f}")
        lines.append(f"  P99: {metrics.p99_latency:.2f}")
        lines.append("")

        lines.append("Resources:")
        lines.append(f"  CPU: {metrics.cpu_usage_percent:.2f}%")
        lines.append(f"  Memory: {metrics.memory_usage_mb:.2f} MB")
        lines.append("")

        lines.append("Queue:")
        lines.append(f"  Depth: {metrics.input_queue_depth}")
        lines.append(f"  Avg Wait Time: {metrics.input_queue_avg_wait_time:.2f} ms")
        lines.append("")

        if metrics.error_breakdown:
            lines.append("Errors:")
            for error_type, count in metrics.error_breakdown.items():
                lines.append(f"  {error_type}: {count}")
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)
