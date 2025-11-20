"""Unit tests for Pipeline Service

Tests for sage.kernel.api.service.pipeline_service module
"""

import pytest

from sage.kernel.api.service.pipeline_service import PipelineService
from sage.kernel.api.service.pipeline_service.pipeline_bridge import PipelineBridge
from sage.kernel.api.service.pipeline_service.pipeline_sink import PipelineSink
from sage.kernel.api.service.pipeline_service.pipeline_source import PipelineSource


class TestPipelineService:
    """Test Pipeline Service functionality"""

    def test_service_creation(self):
        """Test creating a pipeline service"""
        service = PipelineService(service_id="test_service", port=50051)

        assert service.service_id == "test_service"
        assert service.port == 50051
        assert service.is_running() is False

    @pytest.mark.asyncio
    async def test_service_lifecycle(self):
        """Test service start and stop"""
        service = PipelineService(service_id="lifecycle_test", port=50052)

        # Service should not be running initially
        assert service.is_running() is False

        # Start service
        await service.start()
        assert service.is_running() is True

        # Stop service
        await service.stop()
        assert service.is_running() is False

    def test_service_registration(self):
        """Test registering pipelines with service"""
        service = PipelineService(service_id="registration_test", port=50053)

        # Register a test pipeline
        pipeline_id = service.register_pipeline("test_pipeline")
        assert pipeline_id is not None
        assert pipeline_id in service.list_pipelines()

    def test_multiple_pipeline_registration(self):
        """Test registering multiple pipelines"""
        service = PipelineService(service_id="multi_test", port=50054)

        pipeline1 = service.register_pipeline("pipeline1")
        pipeline2 = service.register_pipeline("pipeline2")

        pipelines = service.list_pipelines()
        assert pipeline1 in pipelines
        assert pipeline2 in pipelines
        assert len(pipelines) >= 2


class TestPipelineBridge:
    """Test Pipeline Bridge for cross-pipeline communication"""

    def test_bridge_creation(self):
        """Test creating a pipeline bridge"""
        bridge = PipelineBridge(
            source_service="service_a", target_service="service_b", bridge_id="bridge_1"
        )

        assert bridge.source_service == "service_a"
        assert bridge.target_service == "service_b"
        assert bridge.bridge_id == "bridge_1"

    def test_bridge_connection(self):
        """Test establishing bridge connection"""
        bridge = PipelineBridge(
            source_service="service_a", target_service="service_b", bridge_id="bridge_2"
        )

        # Connection should not be active initially
        assert bridge.is_connected() is False

        # Connect bridge
        bridge.connect()
        assert bridge.is_connected() is True

        # Disconnect bridge
        bridge.disconnect()
        assert bridge.is_connected() is False

    def test_bridge_data_transfer(self):
        """Test transferring data through bridge"""
        bridge = PipelineBridge(
            source_service="service_a", target_service="service_b", bridge_id="bridge_3"
        )

        bridge.connect()

        # Send test data
        test_data = {"key": "value", "count": 42}
        bridge.send(test_data)

        # Verify data can be received
        received = bridge.receive()
        assert received is not None
        # Note: Actual data verification depends on implementation

        bridge.disconnect()


class TestPipelineSource:
    """Test Pipeline Source operator"""

    def test_source_creation(self):
        """Test creating a pipeline source"""
        source = PipelineSource(
            service_id="test_service", pipeline_id="test_pipeline", source_id="source_1"
        )

        assert source.service_id == "test_service"
        assert source.pipeline_id == "test_pipeline"
        assert source.source_id == "source_1"

    def test_source_data_emission(self):
        """Test source data emission"""
        source = PipelineSource(
            service_id="test_service", pipeline_id="test_pipeline", source_id="source_2"
        )

        # Emit test data
        test_data = [1, 2, 3, 4, 5]
        for item in test_data:
            source.emit(item)

        # Verify emission count or similar metric
        # Implementation depends on how source tracks emissions
        assert source.get_emission_count() >= len(test_data)


class TestPipelineSink:
    """Test Pipeline Sink operator"""

    def test_sink_creation(self):
        """Test creating a pipeline sink"""
        sink = PipelineSink(
            service_id="test_service", pipeline_id="test_pipeline", sink_id="sink_1"
        )

        assert sink.service_id == "test_service"
        assert sink.pipeline_id == "test_pipeline"
        assert sink.sink_id == "sink_1"

    def test_sink_data_collection(self):
        """Test sink data collection"""
        sink = PipelineSink(
            service_id="test_service", pipeline_id="test_pipeline", sink_id="sink_2"
        )

        # Collect test data
        test_data = ["a", "b", "c"]
        for item in test_data:
            sink.collect(item)

        # Verify collection
        collected = sink.get_collected_data()
        assert len(collected) == len(test_data)

    def test_sink_callback(self):
        """Test sink with custom callback"""
        results = []

        def callback(data):
            results.append(data)

        sink = PipelineSink(
            service_id="test_service",
            pipeline_id="test_pipeline",
            sink_id="sink_3",
            callback=callback,
        )

        # Send data to sink
        test_data = [10, 20, 30]
        for item in test_data:
            sink.collect(item)

        # Verify callback was invoked
        assert len(results) == len(test_data)
        assert results == test_data


@pytest.mark.integration
class TestPipelineServiceIntegration:
    """Integration tests for Pipeline Service"""

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline_service(self):
        """Test complete pipeline service workflow"""
        # Create service
        service = PipelineService(service_id="e2e_service", port=50055)

        # Start service
        await service.start()

        try:
            # Register pipeline
            pipeline_id = service.register_pipeline("e2e_pipeline")

            # Create source and sink
            source = PipelineSource(
                service_id="e2e_service", pipeline_id=pipeline_id, source_id="source"
            )
            sink = PipelineSink(service_id="e2e_service", pipeline_id=pipeline_id, sink_id="sink")

            # Process data through pipeline
            test_data = range(10)
            for item in test_data:
                source.emit(item)

            # Verify data reached sink
            collected = sink.get_collected_data()
            assert len(collected) > 0

        finally:
            # Stop service
            await service.stop()

    @pytest.mark.asyncio
    async def test_cross_service_bridge(self):
        """Test bridge between two pipeline services"""
        # Create two services
        service_a = PipelineService(service_id="service_a", port=50056)
        service_b = PipelineService(service_id="service_b", port=50057)

        await service_a.start()
        await service_b.start()

        try:
            # Create bridge
            bridge = PipelineBridge(
                source_service="service_a", target_service="service_b", bridge_id="cross_bridge"
            )

            bridge.connect()

            # Send data from service_a to service_b
            test_data = {"message": "cross-service test"}
            bridge.send(test_data)

            # Verify data transfer
            received = bridge.receive()
            assert received is not None

            bridge.disconnect()

        finally:
            await service_a.stop()
            await service_b.stop()
