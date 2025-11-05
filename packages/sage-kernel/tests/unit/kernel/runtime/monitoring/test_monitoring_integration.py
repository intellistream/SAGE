"""
Integration tests for the monitoring system

Tests the monitoring system integrated with BaseTask and task execution.
"""

import time
from unittest.mock import MagicMock

import pytest

from sage.common.core.functions.base_function import BaseFunction
from sage.kernel.api.base_environment import BaseEnvironment
from sage.kernel.api.operator.map_operator import MapOperator
from sage.kernel.api.transformation.base_transformation import BaseTransformation
from sage.kernel.runtime.context.task_context import TaskContext
from sage.kernel.runtime.graph.graph_node import TaskNode
from sage.kernel.runtime.monitoring.metrics_collector import MetricsCollector


class MockFunction(BaseFunction):
    """Mock function class for testing that properly inherits from BaseFunction"""

    __name__ = "MockFunction"
    is_comap = False

    def execute(self, data):
        """Required abstract method implementation"""
        return data


class MockTransformation(BaseTransformation):
    """Mock transformation for testing that properly inherits from BaseTransformation"""

    def __init__(self):
        # Create a minimal mock environment for the base class
        mock_env = MagicMock(spec=BaseEnvironment)
        mock_env.name = "test_env"
        mock_env.platform = "local"
        mock_env.pipeline = []

        # Set operator_class BEFORE calling super().__init__
        self.operator_class = MapOperator

        # Initialize parent with minimal required args
        super().__init__(
            env=mock_env, function=MockFunction, name="MockTransformation", parallelism=1
        )


class MockTaskNode(TaskNode):
    """Mock task node for testing that properly inherits from TaskNode"""

    def __init__(self, name: str = "test_task"):
        # Create minimal mocks for required dependencies
        mock_env = MagicMock(spec=BaseEnvironment)
        mock_env.name = "test_env"
        mock_env.platform = "local"
        mock_env.pipeline = []

        transformation = MockTransformation()

        # Initialize parent
        super().__init__(name=name, transformation=transformation, parallel_index=0, env=mock_env)


class MockEnvironment(BaseEnvironment):
    """Mock environment for testing that properly inherits from BaseEnvironment"""

    def __init__(self, enable_monitoring: bool = False):
        # Initialize parent with required args
        super().__init__(
            name="test_env", config=None, platform="local", enable_monitoring=enable_monitoring
        )

        self.uuid = "test_uuid"

        # Set jobmanager attributes after parent init
        self.jobmanager_host = "127.0.0.1"
        self.jobmanager_port = 19001

        # 使用统一的SAGE路径管理
        from sage.common.config.output_paths import get_test_env_dir

        self.env_base_dir = str(get_test_env_dir("test_logs"))

    def submit(self):
        """Required abstract method implementation"""
        pass


class TestMonitoringIntegration:
    """测试监控系统集成"""

    def test_task_context_with_monitoring_enabled(self):
        """测试启用监控的 TaskContext"""
        env = MockEnvironment(enable_monitoring=True)
        node = MockTaskNode("monitored_task")
        transformation = MockTransformation()

        ctx = TaskContext(node, transformation, env)

        assert ctx.enable_monitoring is True

    def test_task_context_with_monitoring_disabled(self):
        """测试禁用监控的 TaskContext"""
        env = MockEnvironment(enable_monitoring=False)
        node = MockTaskNode("unmonitored_task")
        transformation = MockTransformation()

        ctx = TaskContext(node, transformation, env)

        assert ctx.enable_monitoring is False

    def test_metrics_collector_lifecycle(self):
        """测试 MetricsCollector 生命周期"""
        collector = MetricsCollector(name="lifecycle_test")

        # 模拟处理多个数据包
        packet_ids = [f"packet_{i:03d}" for i in range(10)]

        for packet_id in packet_ids:
            collector.record_packet_start(packet_id)
            time.sleep(0.001)  # 模拟处理时间
            collector.record_packet_end(packet_id, success=True)

        # 获取指标
        metrics = collector.get_real_time_metrics()

        assert metrics.total_packets_processed == 10
        assert metrics.total_packets_failed == 0
        assert metrics.packets_per_second > 0

        # 重置
        collector.reset_metrics()

        metrics = collector.get_real_time_metrics()
        assert metrics.total_packets_processed == 0

    def test_monitoring_with_errors(self):
        """测试监控错误处理"""
        collector = MetricsCollector(name="error_test")

        # 处理成功和失败的包
        for i in range(10):
            packet_id = f"packet_{i:03d}"
            collector.record_packet_start(packet_id)

            if i % 3 == 0:  # 每3个包失败一次
                collector.record_packet_end(packet_id, success=False, error_type="ValueError")
            else:
                collector.record_packet_end(packet_id, success=True)

        metrics = collector.get_real_time_metrics()

        assert metrics.total_packets_processed == 10
        assert metrics.total_packets_failed == 4  # 0, 3, 6, 9
        assert "ValueError" in metrics.error_breakdown
        assert metrics.error_breakdown["ValueError"] == 4

    def test_monitoring_performance_overhead(self):
        """测试监控性能开销"""
        # Baseline: 执行不包含实际监控调用的操作
        # 这包括packet_id生成和一些基本的字典操作
        iterations = 5000
        baseline_dict = {}

        start_time = time.time()
        for i in range(iterations):
            packet_id = f"packet_{i:05d}"
            baseline_dict[packet_id] = {"start": 0, "end": 0}
        no_monitoring_time = time.time() - start_time

        # 使用监控 - 实际调用监控系统
        collector = MetricsCollector(name="overhead_test")
        start_time = time.time()
        for i in range(iterations):
            packet_id = f"packet_{i:05d}"
            collector.record_packet_start(packet_id)
            collector.record_packet_end(packet_id, success=True)
        monitoring_time = time.time() - start_time

        # 监控开销应该相对较小
        # 由于系统负载和计时器精度问题，我们使用较为宽松的阈值
        overhead_ratio = monitoring_time / max(no_monitoring_time, 0.001)
        assert overhead_ratio < 30, f"Monitoring overhead too high: {overhead_ratio}x"

    def test_concurrent_monitoring(self):
        """测试并发监控"""
        import threading

        collector = MetricsCollector(name="concurrent_test")
        errors = []

        def process_packets(start_idx, count):
            try:
                for i in range(count):
                    packet_id = f"thread_{start_idx}_packet_{i:03d}"
                    collector.record_packet_start(packet_id)
                    time.sleep(0.001)
                    collector.record_packet_end(packet_id, success=True)
            except Exception as e:
                errors.append(e)

        # 启动多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=process_packets, args=(i, 20))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0

        # 验证总数正确
        metrics = collector.get_real_time_metrics()
        assert metrics.total_packets_processed == 100  # 5 threads * 20 packets

    def test_latency_percentiles_accuracy(self):
        """测试延迟百分位数准确性"""
        collector = MetricsCollector(name="percentile_test")

        # 创建已知分布的延迟数据
        # 使用较小的延迟值（0.1ms to 10ms）以加快测试
        latencies_ms = [0.1, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        for latency_ms in latencies_ms:
            packet_id = f"packet_{latency_ms}"
            collector.record_packet_start(packet_id)

            # 实际等待
            time.sleep(latency_ms / 1000.0)

            collector.record_packet_end(packet_id, success=True)

        # 获取实时指标（包含百分位数）
        metrics = collector.get_real_time_metrics()

        # 验证收集到数据且有合理的百分位数
        assert metrics.total_packets_processed == len(latencies_ms)
        assert metrics.p50_latency > 0  # P50应该大于0
        assert metrics.p95_latency > metrics.p50_latency  # P95应该大于P50
        assert metrics.p99_latency >= metrics.p95_latency  # P99应该大于等于P95

    def test_monitoring_with_resource_tracking(self):
        """测试带资源监控的完整流程"""
        from sage.kernel.runtime.monitoring.resource_monitor import ResourceMonitor

        collector = MetricsCollector(name="resource_test")
        resource_monitor = ResourceMonitor(sampling_interval=0.1)

        try:
            resource_monitor.start_monitoring()

            # 模拟处理
            for i in range(50):
                packet_id = f"packet_{i:03d}"
                collector.record_packet_start(packet_id)
                time.sleep(0.01)
                collector.record_packet_end(packet_id, success=True)

            # 获取资源统计
            resource_stats = resource_monitor.get_summary()

            # 验证收集到了资源数据（monitoring字段包含采样数）
            assert resource_stats["monitoring"]["sample_count"] > 0

        finally:
            resource_monitor.stop_monitoring()


class TestMonitoringEdgeCases:
    """测试监控系统边界情况"""

    def test_empty_metrics(self):
        """测试空指标"""
        collector = MetricsCollector(name="empty_test")
        metrics = collector.get_real_time_metrics()

        assert metrics.total_packets_processed == 0
        assert metrics.total_packets_failed == 0
        assert metrics.packets_per_second == 0.0

    def test_single_packet(self):
        """测试单个数据包"""
        collector = MetricsCollector(name="single_test")

        collector.record_packet_start("single_packet")
        time.sleep(0.01)
        collector.record_packet_end("single_packet", success=True)

        metrics = collector.get_real_time_metrics()

        assert metrics.total_packets_processed == 1
        assert metrics.p50_latency > 0

    def test_rapid_processing(self):
        """测试快速处理"""
        collector = MetricsCollector(name="rapid_test")

        # 快速处理大量数据包
        for i in range(1000):
            packet_id = f"packet_{i:04d}"
            collector.record_packet_start(packet_id)
            collector.record_packet_end(packet_id, success=True)

        metrics = collector.get_real_time_metrics()

        assert metrics.total_packets_processed == 1000
        assert metrics.packets_per_second > 0

    def test_window_overflow(self):
        """测试窗口溢出"""
        collector = MetricsCollector(name="overflow_test", window_size=100)

        # 处理超过窗口大小的数据包
        for i in range(200):
            packet_id = f"packet_{i:04d}"
            collector.record_packet_start(packet_id)
            collector.record_packet_end(packet_id, success=True)

        # 验证只保留最近的100个
        assert len(collector.packet_metrics) == 100

        # 但总计数应该是200
        metrics = collector.get_real_time_metrics()
        assert metrics.total_packets_processed == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
