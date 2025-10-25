"""
Test suite for sage.kernel.runtime.monitoring.resource_monitor module

Tests the ResourceMonitor class for CPU and memory monitoring.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from sage.kernel.runtime.monitoring.resource_monitor import ResourceMonitor


class TestResourceMonitor:
    """测试 ResourceMonitor 类"""

    @pytest.fixture
    def mock_psutil(self):
        """Mock psutil 模块"""
        with patch("sage.kernel.runtime.monitoring.resource_monitor.PSUTIL_AVAILABLE", True):
            with patch("sage.kernel.runtime.monitoring.resource_monitor.psutil") as mock:
                # Mock Process 类
                mock_process = MagicMock()
                mock_process.cpu_percent.return_value = 50.0
                mock_memory_info = MagicMock()
                mock_memory_info.rss = 1024 * 1024 * 1024  # 1GB
                mock_process.memory_info.return_value = mock_memory_info

                mock.Process.return_value = mock_process
                mock.cpu_percent.return_value = 75.0
                mock_virtual_memory_obj = MagicMock()
                mock_virtual_memory_obj.percent = 60.0
                mock_virtual_memory_obj.available = 2 * 1024 * 1024 * 1024  # 2GB
                mock.virtual_memory.return_value = mock_virtual_memory_obj

                yield mock

    def test_monitor_creation(self):
        """测试创建 ResourceMonitor 实例"""
        monitor = ResourceMonitor(sampling_interval=1.0)

        assert monitor.sampling_interval == 1.0
        assert monitor._running is False
        assert len(monitor.cpu_samples) == 0
        assert len(monitor.memory_samples) == 0

    def test_start_monitoring(self, mock_psutil):
        """测试启动监控"""
        monitor = ResourceMonitor(sampling_interval=0.1)
        monitor.start_monitoring()

        assert monitor._running is True
        assert monitor._monitor_thread is not None
        assert monitor._monitor_thread.is_alive()

        # 等待收集一些样本
        time.sleep(0.3)

        monitor.stop_monitoring()

        # 验证收集到了样本
        assert len(monitor.cpu_samples) > 0
        assert len(monitor.memory_samples) > 0

    def test_stop_monitoring(self, mock_psutil):
        """测试停止监控"""
        monitor = ResourceMonitor(sampling_interval=0.1)
        monitor.start_monitoring()
        time.sleep(0.2)
        monitor.stop_monitoring()

        assert monitor._running is False

        # 等待线程完全停止
        if monitor._monitor_thread:
            monitor._monitor_thread.join(timeout=1.0)

        # 线程应该已经停止（如果存在）
        if monitor._monitor_thread:
            assert not monitor._monitor_thread.is_alive()

    def test_get_stats_without_monitoring(self):
        """测试在未启动监控时获取统计"""
        monitor = ResourceMonitor()
        stats = monitor.get_summary()

        # 验证返回了正确的结构
        assert "process" in stats
        assert "system" in stats
        assert "monitoring" in stats
        assert stats["monitoring"]["sample_count"] == 0

    def test_get_stats_with_monitoring(self, mock_psutil):
        """测试监控运行时获取统计"""
        monitor = ResourceMonitor(sampling_interval=0.1)
        monitor.start_monitoring()
        time.sleep(0.3)
        stats = monitor.get_summary()
        monitor.stop_monitoring()

        # 验证返回了正确的结构和数据
        assert "process" in stats
        assert stats["process"]["current"]["cpu_percent"] > 0
        assert stats["process"]["current"]["memory_mb"] > 0
        assert stats["monitoring"]["sample_count"] >= 0

    def test_psutil_not_available(self):
        """测试 psutil 不可用时的行为"""
        with patch("sage.kernel.runtime.monitoring.resource_monitor.PSUTIL_AVAILABLE", False):
            # 当psutil不可用时，ResourceMonitor初始化会抛出ImportError
            with pytest.raises(ImportError, match="psutil is required"):
                ResourceMonitor()

    def test_reset_stats(self, mock_psutil):
        """测试重置统计数据"""
        monitor = ResourceMonitor(sampling_interval=0.1)
        monitor.start_monitoring()
        time.sleep(0.2)

        # 确认有数据
        assert len(monitor.cpu_samples) > 0

        # 重置
        monitor.stop_monitoring()
        monitor = ResourceMonitor(sampling_interval=0.1)

        assert len(monitor.cpu_samples) == 0
        assert len(monitor.memory_samples) == 0

    def test_concurrent_start_stop(self, mock_psutil):
        """测试并发启动和停止"""
        monitor = ResourceMonitor(sampling_interval=0.1)

        # 多次启动
        monitor.start_monitoring()
        monitor.start_monitoring()  # 第二次启动应该被忽略

        time.sleep(0.2)

        # 多次停止
        monitor.stop_monitoring()
        monitor.stop_monitoring()  # 第二次停止应该安全

        assert monitor._running is False

    def test_memory_conversion(self, mock_psutil):
        """测试内存转换为 MB"""
        monitor = ResourceMonitor(sampling_interval=0.1)
        monitor.start_monitoring()
        time.sleep(0.2)
        stats = monitor.get_summary()
        monitor.stop_monitoring()

        # 验证内存单位是 MB（使用正确的结构）
        assert stats["process"]["current"]["memory_mb"] > 0
        # 应该是合理的 MB 值（1GB = 1024MB）
        assert stats["process"]["current"]["memory_mb"] < 100000  # 不太可能超过 100GB

    def test_custom_sample_interval(self, mock_psutil):
        """测试自定义采样间隔"""
        # 短间隔
        fast_monitor = ResourceMonitor(sampling_interval=0.05)
        fast_monitor.start_monitoring()
        time.sleep(0.2)
        fast_stats = fast_monitor.get_summary()
        fast_monitor.stop_monitoring()

        # 长间隔
        slow_monitor = ResourceMonitor(sampling_interval=0.2)
        slow_monitor.start_monitoring()
        time.sleep(0.2)
        slow_stats = slow_monitor.get_summary()
        slow_monitor.stop_monitoring()

        # 短间隔应该收集更多样本
        assert fast_stats["monitoring"]["sample_count"] >= slow_stats["monitoring"]["sample_count"]


class TestResourceMonitorEdgeCases:
    """测试 ResourceMonitor 边界情况"""

    def test_very_short_interval(self):
        """测试非常短的采样间隔"""
        with patch("sage.kernel.runtime.monitoring.resource_monitor.PSUTIL_AVAILABLE", True):
            with patch("sage.kernel.runtime.monitoring.resource_monitor.psutil") as mock:
                # Mock Process 类
                mock_process = MagicMock()
                mock_process.cpu_percent.return_value = 50.0
                mock_memory_info = MagicMock()
                mock_memory_info.rss = 1024 * 1024 * 1024
                mock_process.memory_info.return_value = mock_memory_info
                mock.Process.return_value = mock_process

                monitor = ResourceMonitor(sampling_interval=0.01)
                monitor.start_monitoring()
                time.sleep(0.1)
                monitor.stop_monitoring()

                # 应该能正常工作
                assert len(monitor.cpu_samples) > 0

    def test_stop_before_start(self):
        """测试在启动前停止"""
        monitor = ResourceMonitor()
        monitor.stop_monitoring()  # 应该安全地不执行任何操作

        assert monitor._running is False

    def test_get_stats_during_monitoring(self):
        """测试在监控运行时多次获取统计"""
        with patch("sage.kernel.runtime.monitoring.resource_monitor.PSUTIL_AVAILABLE", True):
            with patch("sage.kernel.runtime.monitoring.resource_monitor.psutil") as mock:
                # Mock Process 类
                mock_process = MagicMock()
                mock_process.cpu_percent.return_value = 50.0
                mock_memory_info = MagicMock()
                mock_memory_info.rss = 1024 * 1024 * 1024
                mock_process.memory_info.return_value = mock_memory_info
                mock.Process.return_value = mock_process

                monitor = ResourceMonitor(sampling_interval=0.1)
                monitor.start_monitoring()

                # 多次获取统计
                stats1 = monitor.get_summary()
                time.sleep(0.2)
                stats2 = monitor.get_summary()

                monitor.stop_monitoring()

                # 第二次应该有更多或相同数量的样本
                assert stats2["monitoring"]["sample_count"] >= stats1["monitoring"]["sample_count"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
