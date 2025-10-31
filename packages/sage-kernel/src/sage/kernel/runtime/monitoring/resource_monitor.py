"""
Resource Monitor
================

资源使用监控器，监控：
- CPU 使用率
- 内存使用量
- 进程级别资源统计
"""

import threading
import time
from collections import deque

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ResourceMonitor:
    """资源使用监控器"""

    def __init__(
        self,
        sampling_interval: float = 1.0,
        sample_window: int = 60,
        enable_auto_start: bool = False,
    ):
        """
        初始化资源监控器

        Args:
            sampling_interval: 采样间隔（秒）
            sample_window: 保留的样本数量
            enable_auto_start: 是否自动启动监控
        """
        if not PSUTIL_AVAILABLE:
            raise ImportError(
                "psutil is required for ResourceMonitor. Install it with: pip install psutil"
            )

        self.sampling_interval = sampling_interval
        self.sample_window = sample_window

        # CPU 和内存样本
        self.cpu_samples: deque[tuple[float, float]] = deque(maxlen=sample_window)
        self.memory_samples: deque[tuple[float, float]] = deque(maxlen=sample_window)

        # 监控线程
        self._monitor_thread: threading.Thread | None = None
        self._running = False

        # 进程对象
        self._process = psutil.Process()

        # 启动监控
        if enable_auto_start:
            self.start_monitoring()

    def start_monitoring(self) -> None:
        """启动资源监控"""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="ResourceMonitor"
        )
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """停止资源监控"""
        if not self._running:
            return

        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None

    def _monitor_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                timestamp = time.time()

                # 获取 CPU 使用率
                cpu_percent = self._process.cpu_percent(interval=None)

                # 获取内存使用量（MB）
                memory_info = self._process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)

                # 保存样本
                self.cpu_samples.append((timestamp, cpu_percent))
                self.memory_samples.append((timestamp, memory_mb))

            except Exception:
                # 忽略采样错误，继续监控
                pass

            time.sleep(self.sampling_interval)

    def get_current_usage(self) -> tuple[float, float]:
        """
        获取当前CPU和内存使用率

        Returns:
            (cpu_percent, memory_mb) 元组
        """
        if not self.cpu_samples or not self.memory_samples:
            # 如果没有样本，立即采样一次
            try:
                cpu_percent = self._process.cpu_percent(interval=0.1)
                memory_mb = self._process.memory_info().rss / (1024 * 1024)
                return (cpu_percent, memory_mb)
            except Exception:
                return (0.0, 0.0)

        # 返回最新样本
        _, cpu = self.cpu_samples[-1]
        _, memory = self.memory_samples[-1]
        return (cpu, memory)

    def get_average_usage(self, time_window: float | None = None) -> tuple[float, float]:
        """
        获取平均CPU和内存使用率

        Args:
            time_window: 时间窗口（秒），None表示所有样本

        Returns:
            (avg_cpu_percent, avg_memory_mb) 元组
        """
        if not self.cpu_samples or not self.memory_samples:
            return (0.0, 0.0)

        current_time = time.time()
        cutoff_time = current_time - time_window if time_window else 0

        # 过滤样本
        cpu_values = [cpu for ts, cpu in self.cpu_samples if ts >= cutoff_time]
        memory_values = [mem for ts, mem in self.memory_samples if ts >= cutoff_time]

        if not cpu_values or not memory_values:
            return (0.0, 0.0)

        avg_cpu = sum(cpu_values) / len(cpu_values)
        avg_memory = sum(memory_values) / len(memory_values)

        return (avg_cpu, avg_memory)

    def get_peak_usage(self, time_window: float | None = None) -> tuple[float, float]:
        """
        获取峰值CPU和内存使用率

        Args:
            time_window: 时间窗口（秒），None表示所有样本

        Returns:
            (peak_cpu_percent, peak_memory_mb) 元组
        """
        if not self.cpu_samples or not self.memory_samples:
            return (0.0, 0.0)

        current_time = time.time()
        cutoff_time = current_time - time_window if time_window else 0

        # 过滤样本
        cpu_values = [cpu for ts, cpu in self.cpu_samples if ts >= cutoff_time]
        memory_values = [mem for ts, mem in self.memory_samples if ts >= cutoff_time]

        if not cpu_values or not memory_values:
            return (0.0, 0.0)

        peak_cpu = max(cpu_values)
        peak_memory = max(memory_values)

        return (peak_cpu, peak_memory)

    def get_system_wide_usage(self) -> tuple[float, float, float]:
        """
        获取系统级资源使用情况

        Returns:
            (system_cpu_percent, system_memory_percent, system_memory_available_mb) 元组
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            return (cpu_percent, memory_percent, memory_available_mb)
        except Exception:
            return (0.0, 0.0, 0.0)

    def get_summary(self) -> dict:
        """
        获取资源监控摘要

        Returns:
            摘要字典
        """
        current_cpu, current_memory = self.get_current_usage()
        avg_cpu, avg_memory = self.get_average_usage()
        peak_cpu, peak_memory = self.get_peak_usage()
        sys_cpu, sys_mem_pct, sys_mem_avail = self.get_system_wide_usage()

        return {
            "process": {
                "current": {
                    "cpu_percent": current_cpu,
                    "memory_mb": current_memory,
                },
                "average": {
                    "cpu_percent": avg_cpu,
                    "memory_mb": avg_memory,
                },
                "peak": {
                    "cpu_percent": peak_cpu,
                    "memory_mb": peak_memory,
                },
            },
            "system": {
                "cpu_percent": sys_cpu,
                "memory_percent": sys_mem_pct,
                "memory_available_mb": sys_mem_avail,
            },
            "monitoring": {
                "running": self._running,
                "sample_count": len(self.cpu_samples),
                "sampling_interval": self.sampling_interval,
            },
        }

    def __enter__(self):
        """上下文管理器入口"""
        self.start_monitoring()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop_monitoring()
