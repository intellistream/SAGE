"""
Metrics Collector
=================

性能指标收集器，支持：
- 包级别性能监控
- 百分位数计算
- 时间窗口统计
- 错误分类统计
"""

import time
import uuid
from collections import deque
from datetime import datetime, timedelta
from threading import Lock

from sage.kernel.runtime.monitoring.metrics import (
    PacketMetrics,
    ServiceRequestMetrics,
    TaskPerformanceMetrics,
)


class MetricsCollector:
    """性能指标收集器"""

    def __init__(
        self,
        name: str,
        window_size: int = 10000,
        retention_period: timedelta = timedelta(hours=24),
        enable_detailed_tracking: bool = True,
    ):
        """
        初始化指标收集器

        Args:
            name: 任务或服务名称
            window_size: 滑动窗口大小（保留最近N个样本）
            retention_period: 数据保留时长
            enable_detailed_tracking: 是否启用详细的包级别跟踪
        """
        self.name = name
        self.window_size = window_size
        self.retention_period = retention_period
        self.enable_detailed_tracking = enable_detailed_tracking

        # 包/请求级别指标存储
        self.packet_metrics: deque[PacketMetrics | ServiceRequestMetrics] = deque(
            maxlen=window_size
        )

        # 聚合指标存储（按时间分组）
        self.aggregated_metrics: dict[datetime, TaskPerformanceMetrics] = {}

        # 运行时跟踪
        self._in_flight: dict[str, PacketMetrics | ServiceRequestMetrics] = {}

        # 统计计数器
        self._total_processed = 0
        self._total_failed = 0
        self._error_breakdown: dict[str, int] = {}

        # 时间窗口计数器（用于TPS计算）
        self._last_minute_count: deque[tuple] = deque()  # (timestamp, count)
        self._last_5min_count: deque[tuple] = deque()
        self._last_hour_count: deque[tuple] = deque()

        # 启动时间
        self._start_time = time.time()

        # 线程安全锁
        self._lock = Lock()

    def record_packet_start(
        self,
        packet_id: str | None = None,
        packet_size: int = 0,
        method_name: str | None = None,
    ) -> str:
        """
        记录包处理开始

        Args:
            packet_id: 包ID（如果为None则自动生成）
            packet_size: 包大小
            method_name: 方法名（用于服务请求）

        Returns:
            包ID
        """
        if packet_id is None:
            packet_id = str(uuid.uuid4())

        with self._lock:
            current_time = time.time()

            if method_name:
                # 服务请求指标
                metrics: PacketMetrics | ServiceRequestMetrics = ServiceRequestMetrics(
                    request_id=packet_id,
                    method_name=method_name,
                    arrival_time=current_time,
                    processing_start_time=current_time,
                    request_size=packet_size,
                )
            else:
                # 包指标
                metrics = PacketMetrics(
                    packet_id=packet_id,
                    arrival_time=current_time,
                    processing_start_time=current_time,
                    packet_size=packet_size,
                )

            if self.enable_detailed_tracking:
                self._in_flight[packet_id] = metrics

        return packet_id

    def record_packet_end(
        self,
        packet_id: str,
        success: bool = True,
        error_type: str | None = None,
        response_size: int = 0,
    ) -> None:
        """
        记录包处理结束

        Args:
            packet_id: 包ID
            success: 是否成功
            error_type: 错误类型
            response_size: 响应大小（用于服务请求）
        """
        with self._lock:
            current_time = time.time()

            # 更新计数器
            self._total_processed += 1
            if not success:
                self._total_failed += 1
                if error_type:
                    self._error_breakdown[error_type] = self._error_breakdown.get(error_type, 0) + 1

            # 更新时间窗口计数器
            self._update_time_window_counters(current_time)

            # 更新包指标
            if self.enable_detailed_tracking and packet_id in self._in_flight:
                metrics = self._in_flight.pop(packet_id)
                metrics.processing_end_time = current_time
                metrics.success = success
                metrics.error_type = error_type

                if isinstance(metrics, ServiceRequestMetrics):
                    metrics.response_size = response_size

                metrics.calculate_times()
                self.packet_metrics.append(metrics)

    def _update_time_window_counters(self, current_time: float) -> None:
        """更新时间窗口计数器"""
        # 添加当前时间戳
        self._last_minute_count.append((current_time, 1))
        self._last_5min_count.append((current_time, 1))
        self._last_hour_count.append((current_time, 1))

        # 移除过期的记录
        cutoff_1min = current_time - 60
        cutoff_5min = current_time - 300
        cutoff_1hour = current_time - 3600

        while self._last_minute_count and self._last_minute_count[0][0] < cutoff_1min:
            self._last_minute_count.popleft()

        while self._last_5min_count and self._last_5min_count[0][0] < cutoff_5min:
            self._last_5min_count.popleft()

        while self._last_hour_count and self._last_hour_count[0][0] < cutoff_1hour:
            self._last_hour_count.popleft()

    def calculate_percentiles(self, values: list[float]) -> dict[str, float]:
        """
        计算百分位数

        Args:
            values: 数值列表

        Returns:
            包含 p50, p95, p99 的字典
        """
        if not values:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        sorted_values = sorted(values)
        n = len(sorted_values)

        def percentile(p: float) -> float:
            k = (n - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < n:
                return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
            else:
                return sorted_values[f]

        return {
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        }

    def get_real_time_metrics(self) -> TaskPerformanceMetrics:
        """
        获取实时性能指标

        Returns:
            TaskPerformanceMetrics 实例
        """
        with self._lock:
            current_time = time.time()
            uptime = current_time - self._start_time

            # 收集执行时间数据
            execution_times = [
                m.execution_time * 1000  # 转换为毫秒
                for m in self.packet_metrics
                if m.execution_time > 0
            ]

            # 计算百分位数
            percentiles = self.calculate_percentiles(execution_times)

            # 计算各时间窗口的TPS
            last_minute_tps = (
                len(self._last_minute_count) / 60.0 if self._last_minute_count else 0.0
            )
            last_5min_tps = len(self._last_5min_count) / 300.0 if self._last_5min_count else 0.0
            last_hour_tps = len(self._last_hour_count) / 3600.0 if self._last_hour_count else 0.0

            # 计算平均TPS
            packets_per_second = self._total_processed / uptime if uptime > 0 else 0.0

            # 计算队列等待时间
            wait_times = [
                m.queue_wait_time * 1000 for m in self.packet_metrics if m.queue_wait_time > 0
            ]
            avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0.0

            metrics = TaskPerformanceMetrics(
                task_name=self.name,
                uptime=uptime,
                total_packets_processed=self._total_processed,
                total_packets_failed=self._total_failed,
                packets_per_second=packets_per_second,
                min_latency=min(execution_times) if execution_times else 0.0,
                max_latency=max(execution_times) if execution_times else 0.0,
                avg_latency=(
                    sum(execution_times) / len(execution_times) if execution_times else 0.0
                ),
                p50_latency=percentiles["p50"],
                p95_latency=percentiles["p95"],
                p99_latency=percentiles["p99"],
                input_queue_depth=len(self._in_flight),
                input_queue_avg_wait_time=avg_wait_time,
                error_breakdown=self._error_breakdown.copy(),
                last_minute_tps=last_minute_tps,
                last_5min_tps=last_5min_tps,
                last_hour_tps=last_hour_tps,
                timestamp=current_time,
            )

            return metrics

    def get_metrics_history(
        self, time_range: timedelta | None = None
    ) -> list[PacketMetrics | ServiceRequestMetrics]:
        """
        获取历史性能指标

        Args:
            time_range: 时间范围（从现在往前）

        Returns:
            历史指标列表
        """
        with self._lock:
            if time_range is None:
                return list(self.packet_metrics)

            current_time = time.time()
            cutoff_time = current_time - time_range.total_seconds()

            return [m for m in self.packet_metrics if m.arrival_time >= cutoff_time]

    def reset_metrics(self) -> None:
        """重置所有性能指标"""
        with self._lock:
            self.packet_metrics.clear()
            self.aggregated_metrics.clear()
            self._in_flight.clear()
            self._total_processed = 0
            self._total_failed = 0
            self._error_breakdown.clear()
            self._last_minute_count.clear()
            self._last_5min_count.clear()
            self._last_hour_count.clear()
            self._start_time = time.time()

    def get_summary(self) -> dict[str, str | int | float | dict]:
        """
        获取简要统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            current_time = time.time()
            uptime = current_time - self._start_time

            return {
                "name": self.name,
                "uptime_seconds": uptime,
                "total_processed": self._total_processed,
                "total_failed": self._total_failed,
                "success_rate": (
                    (self._total_processed - self._total_failed) / self._total_processed
                    if self._total_processed > 0
                    else 0.0
                ),
                "in_flight": len(self._in_flight),
                "error_breakdown": self._error_breakdown.copy(),
                "samples_collected": len(self.packet_metrics),
            }
