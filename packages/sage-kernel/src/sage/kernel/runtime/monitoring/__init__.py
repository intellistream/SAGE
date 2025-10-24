"""
SAGE Runtime Monitoring Module
===============================

提供全面的任务和服务性能监控功能，包括：
- 包级别性能监控
- 任务和服务级别性能汇总
- 资源使用监控
- 性能指标收集和汇报
"""

from sage.kernel.runtime.monitoring.metrics import (
    MethodMetrics,
    PacketMetrics,
    ServicePerformanceMetrics,
    ServiceRequestMetrics,
    TaskPerformanceMetrics,
)
from sage.kernel.runtime.monitoring.metrics_collector import MetricsCollector
from sage.kernel.runtime.monitoring.metrics_reporter import MetricsReporter

# ResourceMonitor 是可选的，需要 psutil
try:
    from sage.kernel.runtime.monitoring.resource_monitor import ResourceMonitor

    RESOURCE_MONITOR_AVAILABLE = True
except ImportError:
    ResourceMonitor = None  # type: ignore[assignment,misc]
    RESOURCE_MONITOR_AVAILABLE = False

__all__ = [
    # 数据类
    "PacketMetrics",
    "TaskPerformanceMetrics",
    "ServiceRequestMetrics",
    "ServicePerformanceMetrics",
    "MethodMetrics",
    # 组件
    "MetricsCollector",
    "MetricsReporter",
    "ResourceMonitor",
    "RESOURCE_MONITOR_AVAILABLE",
]
