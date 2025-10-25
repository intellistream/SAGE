"""
Test suite for sage.kernel.runtime.monitoring.metrics module

Tests all metrics data classes and their methods.
"""

import pytest
from sage.kernel.runtime.monitoring.metrics import (
    MethodMetrics,
    PacketMetrics,
    ServicePerformanceMetrics,
    ServiceRequestMetrics,
    TaskPerformanceMetrics,
)


class TestPacketMetrics:
    """测试 PacketMetrics 数据类"""

    def test_packet_metrics_creation(self):
        """测试创建 PacketMetrics 实例"""
        packet = PacketMetrics(packet_id="test_packet_001")

        assert packet.packet_id == "test_packet_001"
        assert packet.arrival_time > 0
        assert packet.processing_start_time is None
        assert packet.processing_end_time is None
        assert packet.queue_wait_time == 0.0
        assert packet.execution_time == 0.0
        assert packet.success is True
        assert packet.error_type is None
        assert packet.packet_size == 0

    def test_calculate_times(self):
        """测试时间计算"""
        packet = PacketMetrics(packet_id="test_packet_002")
        packet.arrival_time = 1000.0
        packet.processing_start_time = 1001.0
        packet.processing_end_time = 1003.5

        packet.calculate_times()

        assert packet.queue_wait_time == 1.0
        assert packet.execution_time == 2.5

    def test_to_dict(self):
        """测试转换为字典"""
        packet = PacketMetrics(
            packet_id="test_packet_003",
            packet_size=1024,
            success=False,
            error_type="ValueError",
        )

        result = packet.to_dict()

        assert isinstance(result, dict)
        assert result["packet_id"] == "test_packet_003"
        assert result["packet_size"] == 1024
        assert result["success"] is False
        assert result["error_type"] == "ValueError"


class TestTaskPerformanceMetrics:
    """测试 TaskPerformanceMetrics 数据类"""

    def test_task_metrics_creation(self):
        """测试创建 TaskPerformanceMetrics 实例"""
        metrics = TaskPerformanceMetrics(task_name="test_task")

        assert metrics.task_name == "test_task"
        assert metrics.uptime == 0.0
        assert metrics.total_packets_processed == 0
        assert metrics.total_packets_failed == 0
        assert metrics.packets_per_second == 0.0

    def test_task_metrics_with_data(self):
        """测试带数据的 TaskPerformanceMetrics"""
        metrics = TaskPerformanceMetrics(
            task_name="retriever_task",
            uptime=120.5,
            total_packets_processed=1000,
            total_packets_failed=5,
            packets_per_second=8.3,
            min_latency=10.0,
            max_latency=500.0,
            avg_latency=123.4,
            p50_latency=120.0,
            p95_latency=450.0,
            p99_latency=490.0,
            cpu_usage_percent=45.2,
            memory_usage_mb=1024.5,
        )

        assert metrics.task_name == "retriever_task"
        assert metrics.total_packets_processed == 1000
        assert metrics.total_packets_failed == 5
        assert metrics.packets_per_second == 8.3
        assert metrics.p50_latency == 120.0
        assert metrics.p95_latency == 450.0
        assert metrics.p99_latency == 490.0
        assert metrics.cpu_usage_percent == 45.2
        assert metrics.memory_usage_mb == 1024.5

    def test_to_dict(self):
        """测试转换为字典"""
        metrics = TaskPerformanceMetrics(
            task_name="test_task",
            total_packets_processed=100,
            total_packets_failed=2,
            packets_per_second=5.0,
            p50_latency=100.0,
            error_breakdown={"ValueError": 1, "TypeError": 1},
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["task_name"] == "test_task"
        assert result["total_packets_processed"] == 100
        assert result["total_packets_failed"] == 2
        assert result["latency"]["p50_ms"] == 100.0
        assert result["errors"]["breakdown"] == {"ValueError": 1, "TypeError": 1}
        assert result["throughput"]["current_tps"] == 5.0

    def test_error_breakdown(self):
        """测试错误分类"""
        metrics = TaskPerformanceMetrics(
            task_name="test_task",
            error_breakdown={"NetworkError": 3, "TimeoutError": 2, "ValueError": 1},
        )

        assert len(metrics.error_breakdown) == 3
        assert metrics.error_breakdown["NetworkError"] == 3
        assert metrics.error_breakdown["TimeoutError"] == 2
        assert metrics.error_breakdown["ValueError"] == 1


class TestServiceRequestMetrics:
    """测试 ServiceRequestMetrics 数据类"""

    def test_service_request_creation(self):
        """测试创建 ServiceRequestMetrics 实例"""
        request = ServiceRequestMetrics(
            request_id="req_001", method_name="process_query"
        )

        assert request.request_id == "req_001"
        assert request.method_name == "process_query"
        assert request.arrival_time > 0
        assert request.processing_start_time is None
        assert request.processing_end_time is None
        assert request.success is True

    def test_calculate_times(self):
        """测试时间计算"""
        request = ServiceRequestMetrics(request_id="req_002", method_name="retrieve")
        request.arrival_time = 1000.0
        request.processing_start_time = 1001.5
        request.processing_end_time = 1005.0

        request.calculate_times()

        assert request.queue_wait_time == 1.5
        assert request.execution_time == 3.5

    def test_to_dict(self):
        """测试转换为字典"""
        request = ServiceRequestMetrics(
            request_id="req_003",
            method_name="generate",
            success=False,
            error_type="TimeoutError",
        )

        result = request.to_dict()

        assert isinstance(result, dict)
        assert result["request_id"] == "req_003"
        assert result["method_name"] == "generate"
        assert result["success"] is False
        assert result["error_type"] == "TimeoutError"


class TestMethodMetrics:
    """测试 MethodMetrics 数据类"""

    def test_method_metrics_creation(self):
        """测试创建 MethodMetrics 实例"""
        metrics = MethodMetrics(method_name="process")

        assert metrics.method_name == "process"
        assert metrics.total_requests == 0
        assert metrics.total_failures == 0
        assert metrics.avg_response_time == 0.0

    def test_method_metrics_with_data(self):
        """测试带数据的 MethodMetrics"""
        metrics = MethodMetrics(
            method_name="retrieve",
            total_requests=500,
            total_failures=5,
            avg_response_time=123.4,
            p50_response_time=120.0,
            p95_response_time=200.0,
            p99_response_time=250.0,
        )

        assert metrics.method_name == "retrieve"
        assert metrics.total_requests == 500
        assert metrics.total_failures == 5
        assert metrics.avg_response_time == 123.4
        assert metrics.p95_response_time == 200.0


class TestServicePerformanceMetrics:
    """测试 ServicePerformanceMetrics 数据类"""

    def test_service_metrics_creation(self):
        """测试创建 ServicePerformanceMetrics 实例"""
        metrics = ServicePerformanceMetrics(service_name="retrieval_service")

        assert metrics.service_name == "retrieval_service"
        assert metrics.uptime == 0.0
        assert metrics.total_requests_processed == 0
        assert metrics.total_requests_failed == 0
        assert len(metrics.method_metrics) == 0

    def test_service_metrics_with_methods(self):
        """测试包含方法统计的 ServicePerformanceMetrics"""
        method1 = MethodMetrics(
            method_name="retrieve", total_requests=100, avg_response_time=50.0
        )
        method2 = MethodMetrics(
            method_name="rerank", total_requests=80, avg_response_time=30.0
        )

        metrics = ServicePerformanceMetrics(
            service_name="rag_service",
            total_requests_processed=180,
            method_metrics={"retrieve": method1, "rerank": method2},
        )

        assert metrics.service_name == "rag_service"
        assert metrics.total_requests_processed == 180
        assert len(metrics.method_metrics) == 2
        assert "retrieve" in metrics.method_metrics
        assert "rerank" in metrics.method_metrics

    def test_to_dict(self):
        """测试转换为字典"""
        metrics = ServicePerformanceMetrics(
            service_name="test_service",
            uptime=300.0,
            total_requests_processed=1000,
            total_requests_failed=10,
            requests_per_second=3.33,
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["service_name"] == "test_service"
        assert result["uptime"] == 300.0
        assert result["total_requests_processed"] == 1000
        assert result["total_requests_failed"] == 10
        assert result["requests_per_second"] == 3.33


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
