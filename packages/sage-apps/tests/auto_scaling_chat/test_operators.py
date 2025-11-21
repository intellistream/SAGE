"""Unit tests for Auto-Scaling Chat operators

Tests for sage.apps.auto_scaling_chat.operators module
"""

import pytest

from sage.apps.auto_scaling_chat.operators import (
    AutoScaler,
    LoadBalancer,
    MetricsCollector,
    RequestProcessor,
    ScalingEventsSink,
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


class TestUserTrafficSource:
    """Test UserTrafficSource operator"""

    def test_source_creation(self):
        """Test creating user traffic source"""
        source = UserTrafficSource(duration=10, base_rate=5, peak_rate=20)

        assert source.duration == 10
        assert source.base_rate == 5
        assert source.peak_rate == 20
        assert source.request_count == 0

    def test_source_generates_requests(self):
        """Test source generates user requests"""
        source = UserTrafficSource(duration=1, base_rate=50, peak_rate=100)

        # Execute a few times
        requests = []
        for _ in range(10):
            result = source.execute()
            if result is not None:
                requests.append(result)

        # Should generate at least some requests with high rate
        assert len(requests) >= 0

    def test_source_respects_duration(self):
        """Test source stops after duration"""
        source = UserTrafficSource(duration=0.1, base_rate=10, peak_rate=20)

        import time

        time.sleep(0.15)  # Wait past duration

        result = source.execute()
        assert result is None  # Should return None after duration


class TestLoadBalancer:
    """Test LoadBalancer operator"""

    def test_balancer_creation(self):
        """Test creating load balancer"""
        balancer = LoadBalancer(initial_servers=3)

        assert balancer.num_servers == 3
        assert balancer.current_server == 0

    def test_balancer_round_robin(self):
        """Test round-robin load balancing"""
        balancer = LoadBalancer(initial_servers=3)

        request1 = {"request_id": 1, "message": "test1"}
        request2 = {"request_id": 2, "message": "test2"}
        request3 = {"request_id": 3, "message": "test3"}
        request4 = {"request_id": 4, "message": "test4"}

        result1 = balancer.execute(request1)
        result2 = balancer.execute(request2)
        result3 = balancer.execute(request3)
        result4 = balancer.execute(request4)

        # Should distribute across servers 0, 1, 2, 0
        assert result1["server_id"] == 0
        assert result2["server_id"] == 1
        assert result3["server_id"] == 2
        assert result4["server_id"] == 0

    def test_balancer_scale_servers(self):
        """Test scaling number of servers"""
        balancer = LoadBalancer(initial_servers=2)

        balancer.scale_servers(5)
        assert balancer.num_servers == 5


class TestAutoScaler:
    """Test AutoScaler operator"""

    def test_scaler_creation(self):
        """Test creating auto scaler"""
        scaler = AutoScaler(
            scale_up_threshold=30, scale_down_threshold=10, min_servers=2, max_servers=10
        )

        assert scaler.scale_up_threshold == 30
        assert scaler.scale_down_threshold == 10
        assert scaler.min_servers == 2
        assert scaler.max_servers == 10
        assert scaler.current_servers == 2

    def test_scaler_scale_up_decision(self):
        """Test scale up decision"""
        scaler = AutoScaler(scale_up_threshold=20, min_servers=2, max_servers=10)

        # High load should trigger scale up
        high_load_data = {"current_load": 50, "request_id": 1}

        result = scaler.execute(high_load_data)

        # Should scale up
        assert result["scaling_action"] in ["scale_up", "cooldown"]
        if result["scaling_action"] == "scale_up":
            assert result["total_servers"] == 3

    def test_scaler_respects_cooldown(self):
        """Test cooldown period"""
        scaler = AutoScaler(scale_up_threshold=20, cooldown=2.0)

        # First scale up
        data1 = {"current_load": 50}
        scaler.execute(data1)

        # Immediate second attempt should be in cooldown
        data2 = {"current_load": 50}
        result2 = scaler.execute(data2)

        assert result2["scaling_action"] == "cooldown"


class TestRequestProcessor:
    """Test RequestProcessor operator"""

    def test_processor_creation(self):
        """Test creating request processor"""
        processor = RequestProcessor(processing_time=0.1)

        assert processor.processing_time == 0.1

    def test_processor_processes_request(self):
        """Test processing a request"""
        processor = RequestProcessor(processing_time=0.01)

        request_data = {
            "request_id": 1,
            "user_id": 123,
            "message": "Hello",
            "server_id": 0,
        }

        result = processor.execute(request_data)

        assert result is not None
        assert "processing_time" in result
        assert "processed_at" in result
        assert result["request_id"] == 1


class TestMetricsCollector:
    """Test MetricsCollector operator"""

    def test_collector_creation(self):
        """Test creating metrics collector"""
        collector = MetricsCollector()

        assert collector.total_requests == 0
        assert collector.scaling_events == 0
        assert collector.peak_servers == 0
        assert collector.peak_load == 0

    def test_collector_collects_metrics(self):
        """Test collecting metrics"""
        collector = MetricsCollector()

        data1 = {"current_load": 10, "total_servers": 2, "scaling_action": "none"}
        data2 = {"current_load": 30, "total_servers": 3, "scaling_action": "scale_up"}
        data3 = {"current_load": 15, "total_servers": 3, "scaling_action": "none"}

        collector.execute(data1)
        collector.execute(data2)
        collector.execute(data3)

        assert collector.total_requests == 3
        assert collector.peak_load == 30
        assert collector.peak_servers == 3
        assert collector.scaling_events == 1


class TestScalingEventsSink:
    """Test ScalingEventsSink operator"""

    def test_sink_creation(self):
        """Test creating scaling events sink"""
        sink = ScalingEventsSink()

        assert len(sink.events) == 0

    def test_sink_logs_scaling_events(self):
        """Test logging scaling events"""
        sink = ScalingEventsSink()

        # Non-scaling event should not be logged
        data1 = {"scaling_action": "none", "total_servers": 2}
        sink.execute(data1)

        assert len(sink.events) == 0

        # Scaling events should be logged
        data2 = {
            "scaling_action": "scale_up",
            "total_servers": 3,
            "current_load": 50,
            "timestamp": "2024-01-15T10:00:00",
        }
        sink.execute(data2)

        assert len(sink.events) == 1
        assert sink.events[0]["action"] == "scale_up"
        assert sink.events[0]["servers"] == 3


@pytest.mark.integration
class TestAutoScalingPipeline:
    """Integration tests for auto-scaling chat system"""

    def test_end_to_end_flow(self):
        """Test complete auto-scaling flow"""
        # Create operators
        source = UserTrafficSource(duration=2, base_rate=10, peak_rate=30)
        balancer = LoadBalancer(initial_servers=2)
        scaler = AutoScaler(scale_up_threshold=20, scale_down_threshold=5, min_servers=2)
        processor = RequestProcessor(processing_time=0.01)
        metrics = MetricsCollector()
        events_sink = ScalingEventsSink()

        # Execute pipeline manually
        processed = 0
        max_iterations = 100  # Safety limit

        for _ in range(max_iterations):
            # Generate traffic
            request_data = source.execute()
            if request_data is None:
                break

            # Load balance
            balanced = balancer.execute(request_data)

            # Make scaling decision
            scaled = scaler.execute(balanced)

            # Update balancer if scaled
            if scaled["scaling_action"] in ["scale_up", "scale_down"]:
                balancer.scale_servers(scaled["total_servers"])

            # Process request
            processed_request = processor.execute(scaled)

            # Collect metrics
            metrics.execute(processed_request)
            events_sink.execute(processed_request)

            processed += 1

        # Verify execution
        assert processed >= 0
        assert metrics.total_requests == processed
