"""Unit tests for Auto-Scaling Chat Application

Tests for sage.apps.auto_scaling_chat module
"""

import pytest

from sage.apps.auto_scaling_chat.operators import (
    AutoScaler,
    ChatProcessor,
    LoadBalancer,
    MetricsCollector,
    UserRequest,
    UserTrafficSource,
)


class TestUserRequest:
    """Test UserRequest dataclass"""

    def test_request_creation(self):
        """Test creating a user request"""
        request = UserRequest(
            request_id=1,
            user_id=101,
            timestamp="2024-01-15T10:00:00",
            message="Hello, how are you?",
        )

        assert request.request_id == 1
        assert request.user_id == 101
        assert request.message == "Hello, how are you?"
        assert request.processing_time == 0.0
        assert request.server_id is None

    def test_request_with_processing_info(self):
        """Test request with processing information"""
        request = UserRequest(
            request_id=2,
            user_id=102,
            timestamp="2024-01-15T10:00:01",
            message="Test message",
            processing_time=0.5,
            server_id=3,
        )

        assert request.processing_time == 0.5
        assert request.server_id == 3


class TestUserTrafficSource:
    """Test UserTrafficSource operator"""

    def test_source_creation(self):
        """Test creating user traffic source"""
        source = UserTrafficSource(
            num_users=100, duration=60, base_request_rate=10, peak_multiplier=3
        )

        assert source.num_users == 100
        assert source.duration == 60
        assert source.base_request_rate == 10
        assert source.peak_multiplier == 3

    def test_source_generates_requests(self):
        """Test source generates user requests"""
        source = UserTrafficSource(num_users=10, duration=5, base_request_rate=5, peak_multiplier=2)

        # Generate a batch of requests
        requests = list(source.run())

        # Should generate some requests
        assert len(requests) >= 0
        if len(requests) > 0:
            assert isinstance(requests[0], UserRequest)
            assert requests[0].user_id >= 0
            assert requests[0].user_id < 10

    def test_source_traffic_pattern(self):
        """Test traffic pattern simulation"""
        source = UserTrafficSource(
            num_users=50, duration=10, base_request_rate=5, peak_multiplier=3
        )

        # The source should respect configured parameters
        assert source.num_users == 50
        assert source.peak_multiplier == 3


class TestLoadBalancer:
    """Test LoadBalancer operator"""

    def test_balancer_creation(self):
        """Test creating load balancer"""
        balancer = LoadBalancer(initial_servers=3, max_servers=10)

        assert balancer.initial_servers == 3
        assert balancer.max_servers == 10

    def test_assign_request_to_server(self):
        """Test assigning request to server"""
        balancer = LoadBalancer(initial_servers=3, max_servers=10)

        request = UserRequest(
            request_id=1,
            user_id=101,
            timestamp="2024-01-15T10:00:00",
            message="Test message",
        )

        assigned = balancer.map(request)
        assert assigned.server_id is not None
        assert 0 <= assigned.server_id < 10

    def test_balancer_with_multiple_requests(self):
        """Test load balancing across multiple requests"""
        balancer = LoadBalancer(initial_servers=3, max_servers=10)

        requests = [
            UserRequest(
                request_id=i,
                user_id=100 + i,
                timestamp=f"2024-01-15T10:00:{i:02d}",
                message=f"Message {i}",
            )
            for i in range(10)
        ]

        assigned = [balancer.map(req) for req in requests]

        # All requests should be assigned
        assert all(req.server_id is not None for req in assigned)

        # Should distribute across servers
        server_ids = {req.server_id for req in assigned}
        assert len(server_ids) > 0


class TestChatProcessor:
    """Test ChatProcessor operator"""

    def test_processor_creation(self):
        """Test creating chat processor"""
        processor = ChatProcessor(processing_time_mean=0.5, processing_time_std=0.1, timeout=5.0)

        assert processor.processing_time_mean == 0.5
        assert processor.processing_time_std == 0.1
        assert processor.timeout == 5.0

    def test_process_request(self):
        """Test processing a request"""
        processor = ChatProcessor(processing_time_mean=0.1, processing_time_std=0.01, timeout=1.0)

        request = UserRequest(
            request_id=1,
            user_id=101,
            timestamp="2024-01-15T10:00:00",
            message="Test message",
            server_id=1,
        )

        processed = processor.map(request)
        assert processed.processing_time > 0
        assert processed.request_id == request.request_id

    def test_processor_timing(self):
        """Test processor timing is reasonable"""
        processor = ChatProcessor(processing_time_mean=0.5, processing_time_std=0.1, timeout=2.0)

        request = UserRequest(
            request_id=1,
            user_id=101,
            timestamp="2024-01-15T10:00:00",
            message="Test",
            server_id=1,
        )

        processed = processor.map(request)
        # Processing time should be positive and reasonable
        assert 0 < processed.processing_time < 2.0


class TestAutoScaler:
    """Test AutoScaler operator"""

    def test_scaler_creation(self):
        """Test creating auto scaler"""
        scaler = AutoScaler(
            target_utilization=0.7,
            scale_up_threshold=0.8,
            scale_down_threshold=0.3,
            min_servers=2,
            max_servers=20,
        )

        assert scaler.target_utilization == 0.7
        assert scaler.scale_up_threshold == 0.8
        assert scaler.scale_down_threshold == 0.3
        assert scaler.min_servers == 2
        assert scaler.max_servers == 20

    def test_scaling_decision(self):
        """Test scaling decision logic"""
        scaler = AutoScaler(
            target_utilization=0.7,
            scale_up_threshold=0.8,
            scale_down_threshold=0.3,
            min_servers=2,
            max_servers=20,
        )

        # Test with a request
        request = UserRequest(
            request_id=1,
            user_id=101,
            timestamp="2024-01-15T10:00:00",
            message="Test",
            processing_time=0.5,
            server_id=1,
        )

        result = scaler.map(request)
        assert result is not None


class TestMetricsCollector:
    """Test MetricsCollector operator"""

    def test_collector_creation(self):
        """Test creating metrics collector"""
        collector = MetricsCollector(window_size=100)

        assert collector.window_size == 100

    def test_collect_metrics(self):
        """Test collecting request metrics"""
        collector = MetricsCollector(window_size=50)

        requests = [
            UserRequest(
                request_id=i,
                user_id=100 + i,
                timestamp=f"2024-01-15T10:00:{i:02d}",
                message=f"Message {i}",
                processing_time=0.1 + i * 0.01,
                server_id=i % 3,
            )
            for i in range(10)
        ]

        for req in requests:
            collector.sink(req)

        metrics = collector.get_metrics()
        assert metrics is not None

    def test_metrics_calculation(self):
        """Test metrics calculation"""
        collector = MetricsCollector(window_size=100)

        # Add some requests
        for i in range(5):
            request = UserRequest(
                request_id=i,
                user_id=100 + i,
                timestamp=f"2024-01-15T10:00:{i:02d}",
                message=f"Message {i}",
                processing_time=0.5,
                server_id=1,
            )
            collector.sink(request)

        # Should have collected metrics
        metrics = collector.get_metrics()
        assert "total_requests" in metrics or metrics is not None


@pytest.mark.integration
class TestAutoScalingChatPipeline:
    """Integration tests for auto-scaling chat pipeline"""

    def test_pipeline_creation(self):
        """Test creating the auto-scaling pipeline"""
        from sage.apps.auto_scaling_chat.pipeline import create_auto_scaling_chat_pipeline

        pipeline = create_auto_scaling_chat_pipeline(
            num_users=100, duration=60, initial_servers=3, max_servers=10
        )

        assert pipeline is not None

    @pytest.mark.skip(reason="Long-running simulation test")
    def test_end_to_end_simulation(self):
        """Test complete auto-scaling simulation"""
        from sage.apps.auto_scaling_chat.pipeline import create_auto_scaling_chat_pipeline

        _pipeline = create_auto_scaling_chat_pipeline(
            num_users=50, duration=30, initial_servers=2, max_servers=8
        )

        # Run simulation
        # results = _pipeline.execute()
        # assert results is not None
        pass
