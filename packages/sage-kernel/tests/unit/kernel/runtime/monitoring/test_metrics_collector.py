"""
Test suite for sage.kernel.runtime.monitoring.metrics_collector module

Tests the MetricsCollector class functionality including packet tracking,
TPS calculation, and latency percentile computation.
"""

import time

import pytest
from sage.kernel.runtime.monitoring.metrics_collector import MetricsCollector


class TestMetricsCollector:
    """测试 MetricsCollector 类"""

    def test_collector_creation(self):
        """测试创建 MetricsCollector 实例"""
        collector = MetricsCollector(name="test_task")

        assert collector.name == "test_task"
        assert collector.window_size == 10000  # 默认值是10000
        assert len(collector.packet_metrics) == 0
        assert collector._total_processed == 0
        assert collector._total_failed == 0

    def test_custom_window_size(self):
        """测试自定义窗口大小"""
        collector = MetricsCollector(name="test_task", window_size=500)

        assert collector.window_size == 500
        assert collector.packet_metrics.maxlen == 500

    def test_record_packet_start(self):
        """测试记录数据包开始处理"""
        collector = MetricsCollector(name="test_task")

        packet_id = "packet_001"
        collector.record_packet_start(packet_id)

        assert packet_id in collector._in_flight
        assert collector._in_flight[packet_id].packet_id == packet_id
        assert collector._in_flight[packet_id].processing_start_time is not None

    def test_record_packet_end_success(self):
        """测试记录数据包成功处理完成"""
        collector = MetricsCollector(name="test_task")

        packet_id = "packet_002"
        collector.record_packet_start(packet_id)
        time.sleep(0.01)  # 模拟处理时间
        collector.record_packet_end(packet_id, success=True)

        assert packet_id not in collector._in_flight
        assert collector._total_processed == 1
        assert collector._total_failed == 0
        assert len(collector.packet_metrics) == 1

    def test_record_packet_end_failure(self):
        """测试记录数据包处理失败"""
        collector = MetricsCollector(name="test_task")

        packet_id = "packet_003"
        collector.record_packet_start(packet_id)
        collector.record_packet_end(packet_id, success=False, error_type="ValueError")

        assert collector._total_processed == 1
        assert collector._total_failed == 1
        assert "ValueError" in collector._error_breakdown
        assert collector._error_breakdown["ValueError"] == 1

    def test_multiple_error_types(self):
        """测试多种错误类型统计"""
        collector = MetricsCollector(name="test_task")

        # 记录不同类型的错误
        for i, error_type in enumerate(
            ["ValueError", "TypeError", "ValueError", "NetworkError"]
        ):
            packet_id = f"packet_{i:03d}"
            collector.record_packet_start(packet_id)
            collector.record_packet_end(packet_id, success=False, error_type=error_type)

        assert collector._total_failed == 4
        assert collector._error_breakdown["ValueError"] == 2
        assert collector._error_breakdown["TypeError"] == 1
        assert collector._error_breakdown["NetworkError"] == 1

    def test_calculate_tps(self):
        """测试 TPS 计算"""
        collector = MetricsCollector(name="test_task")

        # 模拟处理多个数据包
        for i in range(10):
            packet_id = f"packet_{i:03d}"
            collector.record_packet_start(packet_id)
            collector.record_packet_end(packet_id, success=True)

        time.sleep(0.1)  # 等待一小段时间
        metrics = collector.get_real_time_metrics()

        assert metrics.packets_per_second > 0  # TPS 应该大于0

    def test_calculate_percentiles_empty(self):
        """测试空数据的百分位数计算"""
        collector = MetricsCollector(name="test_task")

        result = collector.calculate_percentiles([])

        assert result["p50"] == 0.0
        assert result["p95"] == 0.0
        assert result["p99"] == 0.0

    def test_calculate_percentiles_with_data(self):
        """测试有数据的百分位数计算"""
        collector = MetricsCollector(name="test_task")

        # 添加一些延迟数据（毫秒）
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        
        result = collector.calculate_percentiles(latencies)

        # 验证百分位数在合理范围内（毫秒）
        assert 40 <= result["p50"] <= 60  # P50 应该在中位数附近
        assert 90 <= result["p95"] <= 100  # P95 应该接近最大值
        assert 95 <= result["p99"] <= 100  # P99 应该非常接近最大值

    def test_get_real_time_metrics(self):
        """测试获取实时指标"""
        collector = MetricsCollector(name="test_task")

        # 处理一些数据包
        for i in range(5):
            packet_id = f"packet_{i:03d}"
            collector.record_packet_start(packet_id)
            time.sleep(0.01)
            collector.record_packet_end(packet_id, success=True)

        # 处理一个失败的包
        collector.record_packet_start("failed_packet")
        collector.record_packet_end("failed_packet", success=False, error_type="Error")

        metrics = collector.get_real_time_metrics()

        assert metrics.task_name == "test_task"
        assert metrics.total_packets_processed == 6
        assert metrics.total_packets_failed == 1
        assert metrics.packets_per_second >= 0
        assert len(metrics.error_breakdown) == 1
        assert metrics.error_breakdown["Error"] == 1

    def test_reset_metrics(self):
        """测试重置指标"""
        collector = MetricsCollector(name="test_task")

        # 添加一些数据
        for i in range(5):
            packet_id = f"packet_{i:03d}"
            collector.record_packet_start(packet_id)
            collector.record_packet_end(packet_id, success=True)

        # 重置
        collector.reset_metrics()

        assert collector._total_processed == 0
        assert collector._total_failed == 0
        assert len(collector.packet_metrics) == 0
        assert len(collector._error_breakdown) == 0
        assert len(collector._in_flight) == 0

    def test_window_size_limit(self):
        """测试滑动窗口大小限制"""
        collector = MetricsCollector(name="test_task", window_size=10)

        # 添加超过窗口大小的数据
        for i in range(20):
            packet_id = f"packet_{i:03d}"
            collector.record_packet_start(packet_id)
            collector.record_packet_end(packet_id, success=True)

        # 验证只保留最近的 10 条数据
        assert len(collector.packet_metrics) == 10

    def test_concurrent_packets(self):
        """测试并发处理多个数据包"""
        collector = MetricsCollector(name="test_task")

        # 同时开始多个数据包
        for i in range(5):
            collector.record_packet_start(f"packet_{i:03d}")

        assert len(collector._in_flight) == 5

        # 完成所有数据包
        for i in range(5):
            collector.record_packet_end(f"packet_{i:03d}", success=True)

        assert len(collector._in_flight) == 0
        assert collector._total_processed == 5


class TestMetricsCollectorEdgeCases:
    """测试 MetricsCollector 边界情况"""

    def test_record_end_without_start(self):
        """测试在没有开始记录的情况下结束"""
        collector = MetricsCollector(name="test_task")

        # 尝试结束一个未开始的数据包
        collector.record_packet_end("nonexistent_packet", success=True)

        # 实际会被记录但不会有详细信息（因为不在_in_flight中）
        assert collector._total_processed == 1

    def test_duplicate_packet_start(self):
        """测试重复开始同一个数据包"""
        collector = MetricsCollector(name="test_task")

        packet_id = "duplicate_packet"
        collector.record_packet_start(packet_id)
        first_start_time = collector._in_flight[packet_id].processing_start_time

        time.sleep(0.01)

        # 再次开始同一个数据包
        collector.record_packet_start(packet_id)
        second_start_time = collector._in_flight[packet_id].processing_start_time

        # 应该覆盖之前的记录
        assert second_start_time > first_start_time

    def test_very_fast_processing(self):
        """测试非常快的处理时间"""
        collector = MetricsCollector(name="test_task")

        packet_id = "fast_packet"
        collector.record_packet_start(packet_id)
        collector.record_packet_end(packet_id, success=True)

        metrics = collector.get_real_time_metrics()

        # 即使处理时间非常短，也应该能正确记录
        assert metrics.total_packets_processed == 1
        assert metrics.min_latency >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
