"""
Performance Metrics Data Classes
================================

定义性能监控的核心数据结构
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PacketMetrics:
    """单个数据包的性能指标"""

    packet_id: str
    arrival_time: float = field(default_factory=time.time)
    processing_start_time: float | None = None
    processing_end_time: float | None = None
    queue_wait_time: float = 0.0
    execution_time: float = 0.0
    success: bool = True
    error_type: str | None = None
    packet_size: int = 0

    def calculate_times(self) -> None:
        """计算各项时间指标"""
        if self.processing_start_time and self.arrival_time:
            self.queue_wait_time = self.processing_start_time - self.arrival_time

        if self.processing_end_time and self.processing_start_time:
            self.execution_time = self.processing_end_time - self.processing_start_time

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "packet_id": self.packet_id,
            "arrival_time": self.arrival_time,
            "processing_start_time": self.processing_start_time,
            "processing_end_time": self.processing_end_time,
            "queue_wait_time": self.queue_wait_time,
            "execution_time": self.execution_time,
            "success": self.success,
            "error_type": self.error_type,
            "packet_size": self.packet_size,
        }


@dataclass
class TaskPerformanceMetrics:
    """任务性能汇总指标"""

    task_name: str
    uptime: float = 0.0
    total_packets_processed: int = 0
    total_packets_failed: int = 0
    packets_per_second: float = 0.0

    # 延迟统计（毫秒）
    min_latency: float = 0.0
    max_latency: float = 0.0
    avg_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0

    # 队列统计
    input_queue_depth: int = 0
    input_queue_avg_wait_time: float = 0.0

    # 资源使用
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0

    # 错误统计
    error_breakdown: dict[str, int] = field(default_factory=dict)

    # 时间窗口统计
    last_minute_tps: float = 0.0
    last_5min_tps: float = 0.0
    last_hour_tps: float = 0.0

    # 元数据
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_name": self.task_name,
            "uptime": self.uptime,
            "total_packets_processed": self.total_packets_processed,
            "total_packets_failed": self.total_packets_failed,
            "packets_per_second": self.packets_per_second,
            "latency": {
                "min_ms": self.min_latency,
                "max_ms": self.max_latency,
                "avg_ms": self.avg_latency,
                "p50_ms": self.p50_latency,
                "p95_ms": self.p95_latency,
                "p99_ms": self.p99_latency,
            },
            "queue": {
                "input_depth": self.input_queue_depth,
                "avg_wait_time_ms": self.input_queue_avg_wait_time,
            },
            "resource": {
                "cpu_percent": self.cpu_usage_percent,
                "memory_mb": self.memory_usage_mb,
            },
            "errors": {
                "breakdown": self.error_breakdown,
                "total": self.total_packets_failed,
            },
            "throughput": {
                "current_tps": self.packets_per_second,
                "last_minute_tps": self.last_minute_tps,
                "last_5min_tps": self.last_5min_tps,
                "last_hour_tps": self.last_hour_tps,
            },
            "timestamp": self.timestamp,
        }


@dataclass
class ServiceRequestMetrics:
    """服务请求性能指标"""

    request_id: str
    method_name: str
    arrival_time: float = field(default_factory=time.time)
    processing_start_time: float | None = None
    processing_end_time: float | None = None
    queue_wait_time: float = 0.0
    execution_time: float = 0.0
    success: bool = True
    error_type: str | None = None
    request_size: int = 0
    response_size: int = 0

    def calculate_times(self) -> None:
        """计算各项时间指标"""
        if self.processing_start_time and self.arrival_time:
            self.queue_wait_time = self.processing_start_time - self.arrival_time

        if self.processing_end_time and self.processing_start_time:
            self.execution_time = self.processing_end_time - self.processing_start_time

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "method_name": self.method_name,
            "arrival_time": self.arrival_time,
            "processing_start_time": self.processing_start_time,
            "processing_end_time": self.processing_end_time,
            "queue_wait_time": self.queue_wait_time,
            "execution_time": self.execution_time,
            "success": self.success,
            "error_type": self.error_type,
            "request_size": self.request_size,
            "response_size": self.response_size,
        }


@dataclass
class MethodMetrics:
    """方法级别性能指标"""

    method_name: str
    total_requests: int = 0
    total_failures: int = 0
    min_response_time: float = float("inf")
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "method_name": self.method_name,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "response_time": {
                "min_ms": (
                    self.min_response_time if self.min_response_time != float("inf") else 0.0
                ),
                "max_ms": self.max_response_time,
                "avg_ms": self.avg_response_time,
                "p50_ms": self.p50_response_time,
                "p95_ms": self.p95_response_time,
                "p99_ms": self.p99_response_time,
            },
        }


@dataclass
class ServicePerformanceMetrics:
    """服务性能汇总指标"""

    service_name: str
    uptime: float = 0.0
    total_requests_processed: int = 0
    total_requests_failed: int = 0
    requests_per_second: float = 0.0

    # 按方法分组的统计
    method_metrics: dict[str, MethodMetrics] = field(default_factory=dict)

    # 延迟统计（毫秒）
    min_response_time: float = float("inf")
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0

    # 队列统计
    request_queue_depth: int = 0
    request_queue_avg_wait_time: float = 0.0
    response_queue_depths: dict[str, int] = field(default_factory=dict)

    # 资源使用
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0

    # 错误统计
    error_breakdown: dict[str, int] = field(default_factory=dict)

    # 并发统计
    concurrent_requests: int = 0
    max_concurrent_requests: int = 0

    # 时间窗口统计
    last_minute_rps: float = 0.0
    last_5min_rps: float = 0.0
    last_hour_rps: float = 0.0

    # 元数据
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "service_name": self.service_name,
            "uptime": self.uptime,
            "total_requests_processed": self.total_requests_processed,
            "total_requests_failed": self.total_requests_failed,
            "requests_per_second": self.requests_per_second,
            "response_time": {
                "min_ms": (
                    self.min_response_time if self.min_response_time != float("inf") else 0.0
                ),
                "max_ms": self.max_response_time,
                "avg_ms": self.avg_response_time,
                "p50_ms": self.p50_response_time,
                "p95_ms": self.p95_response_time,
                "p99_ms": self.p99_response_time,
            },
            "queue": {
                "request_depth": self.request_queue_depth,
                "request_avg_wait_time_ms": self.request_queue_avg_wait_time,
                "response_depths": self.response_queue_depths,
            },
            "resource": {
                "cpu_percent": self.cpu_usage_percent,
                "memory_mb": self.memory_usage_mb,
            },
            "errors": {
                "breakdown": self.error_breakdown,
                "total": self.total_requests_failed,
            },
            "concurrency": {
                "current": self.concurrent_requests,
                "max": self.max_concurrent_requests,
            },
            "throughput": {
                "current_rps": self.requests_per_second,
                "last_minute_rps": self.last_minute_rps,
                "last_5min_rps": self.last_5min_rps,
                "last_hour_rps": self.last_hour_rps,
            },
            "methods": {name: metrics.to_dict() for name, metrics in self.method_metrics.items()},
            "timestamp": self.timestamp,
        }
