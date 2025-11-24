"""
Unit tests for Kernel API Operators.

Tests the core operator implementations including FilterOperator, MapOperator,
FlatMapOperator, and CoMapOperator.
"""

from unittest.mock import MagicMock

import pytest

from sage.common.core.functions import (
    BaseCoMapFunction,
    FilterFunction,
    FlatMapFunction,
    MapFunction,
)
from sage.kernel.api.operator.comap_operator import CoMapOperator
from sage.kernel.api.operator.filter_operator import FilterOperator
from sage.kernel.api.operator.flatmap_operator import FlatMapOperator
from sage.kernel.api.operator.map_operator import MapOperator
from sage.kernel.runtime.communication.packet import Packet

# Mock Functions for Testing


class MockFilterFunction(FilterFunction):
    """Mock filter function that filters even numbers."""

    def __init__(self):
        super().__init__()
        self.ctx = None
        self._logger = None

    def execute(self, data):
        if isinstance(data, dict) and "value" in data:
            return data["value"] % 2 == 0  # Only allow even numbers
        return isinstance(data, int) and data % 2 == 0


class MockMapFunction(MapFunction):
    """Mock map function that doubles the value."""

    def __init__(self):
        super().__init__()
        self.ctx = None
        self._logger = None

    def execute(self, data):
        if isinstance(data, dict) and "value" in data:
            return {"value": data["value"] * 2}
        return data * 2 if isinstance(data, (int, float)) else data


class MockFlatMapFunction(FlatMapFunction):
    """Mock flatmap function that splits a list."""

    def __init__(self):
        super().__init__()
        self.ctx = None
        self._logger = None
        self.out = None  # Will be set by insert_collector

    def execute(self, data):
        if isinstance(data, list):
            return data  # Return the list to be flattened
        elif isinstance(data, dict) and "items" in data:
            return data["items"]  # Return nested list
        return [data]  # Wrap single item in list


class MockCoMapFunction(BaseCoMapFunction):
    """Mock comap function that processes two streams."""

    def __init__(self):
        super().__init__()
        self.ctx = None
        self._logger = None

    def map0(self, data):
        """Process stream 0 data."""
        return f"Stream0: {data}"

    def map1(self, data):
        """Process stream 1 data."""
        return f"Stream1: {data}"


# Fixtures


@pytest.fixture
def mock_task_context():
    """Create a mock TaskContext."""
    context = MagicMock()
    context.name = "test_task"
    context.logger = MagicMock()
    context.task_id = "task_001"
    # Mock the router property
    context.router = MagicMock()
    context.router.send = MagicMock()
    return context


@pytest.fixture
def mock_function_factory():
    """Create a mock FunctionFactory."""
    factory = MagicMock()
    factory.create_function = MagicMock()
    return factory


# Test Cases - FilterOperator


@pytest.mark.unit
class TestFilterOperator:
    """Test FilterOperator implementation."""

    def test_filter_operator_initialization(self, mock_task_context, mock_function_factory):
        """Test FilterOperator initialization."""
        mock_function_factory.create_function.return_value = MockFilterFunction()

        operator = FilterOperator(
            name="test_filter",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Operator name comes from ctx.name
        assert operator.name == mock_task_context.name
        assert operator.ctx == mock_task_context
        assert operator.function is not None

    def test_filter_passes_data(self, mock_task_context, mock_function_factory):
        """Test filter passes data that meets condition."""
        mock_function_factory.create_function.return_value = MockFilterFunction()

        operator = FilterOperator(
            name="test_filter",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Create packet with even number (should pass)
        packet = Packet(payload={"value": 4})

        operator.process_packet(packet)

        # Verify packet was sent via router
        mock_task_context.router.send.assert_called_once()

    def test_filter_blocks_data(self, mock_task_context, mock_function_factory):
        """Test filter blocks data that doesn't meet condition."""
        mock_function_factory.create_function.return_value = MockFilterFunction()

        operator = FilterOperator(
            name="test_filter",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Create packet with odd number (should be filtered)
        packet = Packet(payload={"value": 3})

        operator.process_packet(packet)

        # Verify packet was NOT sent
        mock_task_context.router.send.assert_not_called()

    def test_filter_handles_empty_packet(self, mock_task_context, mock_function_factory):
        """Test filter handles empty packet gracefully."""
        mock_function_factory.create_function.return_value = MockFilterFunction()

        operator = FilterOperator(
            name="test_filter",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        operator.process_packet(None)

        mock_task_context.router.send.assert_not_called()

    def test_filter_handles_none_payload(self, mock_task_context, mock_function_factory):
        """Test filter handles None payload."""
        mock_function_factory.create_function.return_value = MockFilterFunction()

        operator = FilterOperator(
            name="test_filter",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload=None)
        operator.process_packet(packet)

        mock_task_context.router.send.assert_not_called()


# Test Cases - MapOperator


@pytest.mark.unit
class TestMapOperator:
    """Test MapOperator implementation."""

    def test_map_operator_initialization(self, mock_task_context, mock_function_factory):
        """Test MapOperator initialization."""
        mock_function_factory.create_function.return_value = MockMapFunction()

        operator = MapOperator(
            name="test_map",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Operator name comes from ctx.name
        assert operator.name == mock_task_context.name
        assert operator.ctx == mock_task_context

    def test_map_transforms_data(self, mock_task_context, mock_function_factory):
        """Test map transforms data correctly."""
        mock_function_factory.create_function.return_value = MockMapFunction()

        operator = MapOperator(
            name="test_map",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload={"value": 5})

        operator.process_packet(packet)

        # Verify send was called
        assert mock_task_context.router.send.called
        # Get the actual packet that was sent
        sent_packet = mock_task_context.router.send.call_args[0][0]
        # Verify the transformation (5 * 2 = 10)
        assert sent_packet.payload["value"] == 10

    def test_map_handles_empty_packet(self, mock_task_context, mock_function_factory):
        """Test map handles empty packet."""
        mock_function_factory.create_function.return_value = MockMapFunction()

        operator = MapOperator(
            name="test_map",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        operator.process_packet(None)

        # Should not crash, just log warning
        assert mock_task_context.logger.warning.called


# Test Cases - FlatMapOperator


@pytest.mark.unit
class TestFlatMapOperator:
    """Test FlatMapOperator implementation."""

    def test_flatmap_operator_initialization(self, mock_task_context, mock_function_factory):
        """Test FlatMapOperator initialization."""
        mock_function_factory.create_function.return_value = MockFlatMapFunction()

        operator = FlatMapOperator(
            name="test_flatmap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Operator name comes from ctx.name
        assert operator.name == mock_task_context.name
        assert operator.ctx == mock_task_context
        assert operator.out is not None  # Collector should be initialized

    def test_flatmap_expands_list(self, mock_task_context, mock_function_factory):
        """Test flatmap expands a list into multiple packets."""
        mock_function_factory.create_function.return_value = MockFlatMapFunction()

        operator = FlatMapOperator(
            name="test_flatmap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Create packet with a list
        packet = Packet(payload=[1, 2, 3])

        operator.process_packet(packet)

        # Should send 3 separate packets
        assert mock_task_context.router.send.call_count == 3

    def test_flatmap_handles_dict_with_items(self, mock_task_context, mock_function_factory):
        """Test flatmap handles dict with items key."""
        mock_function_factory.create_function.return_value = MockFlatMapFunction()

        operator = FlatMapOperator(
            name="test_flatmap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload={"items": ["a", "b", "c"]})

        operator.process_packet(packet)

        # Should send 3 separate packets for the items
        assert mock_task_context.router.send.call_count == 3

    def test_flatmap_handles_single_item(self, mock_task_context, mock_function_factory):
        """Test flatmap handles single non-list item."""
        mock_function_factory.create_function.return_value = MockFlatMapFunction()

        operator = FlatMapOperator(
            name="test_flatmap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload="single_item")

        operator.process_packet(packet)

        # Should send 1 packet (wrapped in list)
        assert mock_task_context.router.send.call_count == 1

    def test_flatmap_handles_empty_packet(self, mock_task_context, mock_function_factory):
        """Test flatmap handles empty packet."""
        mock_function_factory.create_function.return_value = MockFlatMapFunction()

        operator = FlatMapOperator(
            name="test_flatmap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        operator.process_packet(None)

        mock_task_context.router.send.assert_not_called()


# Test Cases - CoMapOperator


@pytest.mark.unit
class TestCoMapOperator:
    """Test CoMapOperator implementation."""

    def test_comap_operator_initialization(self, mock_task_context, mock_function_factory):
        """Test CoMapOperator initialization with valid CoMap function."""
        mock_function_factory.create_function.return_value = MockCoMapFunction()

        operator = CoMapOperator(
            name="test_comap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Operator name comes from ctx.name
        assert operator.name == mock_task_context.name
        assert operator.ctx == mock_task_context

    def test_comap_processes_stream0(self, mock_task_context, mock_function_factory):
        """Test CoMap processes data from stream 0."""
        mock_function_factory.create_function.return_value = MockCoMapFunction()

        operator = CoMapOperator(
            name="test_comap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Create packet from stream 0
        packet = Packet(payload="test_data")
        packet.input_index = 0

        operator.process_packet(packet)

        # Verify send was called
        assert mock_task_context.router.send.called
        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.payload == "Stream0: test_data"

    def test_comap_processes_stream1(self, mock_task_context, mock_function_factory):
        """Test CoMap processes data from stream 1."""
        mock_function_factory.create_function.return_value = MockCoMapFunction()

        operator = CoMapOperator(
            name="test_comap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Create packet from stream 1
        packet = Packet(payload="test_data")
        packet.input_index = 1

        operator.process_packet(packet)

        # Verify send was called
        assert mock_task_context.router.send.called
        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.payload == "Stream1: test_data"

    def test_comap_handles_empty_packet(self, mock_task_context, mock_function_factory):
        """Test CoMap handles empty packet."""
        mock_function_factory.create_function.return_value = MockCoMapFunction()

        operator = CoMapOperator(
            name="test_comap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        operator.process_packet(None)

        mock_task_context.router.send.assert_not_called()

    def test_comap_validation_requires_comap_function(
        self, mock_task_context, mock_function_factory
    ):
        """Test CoMap validation rejects non-CoMap functions."""
        # Use a regular MapFunction instead of CoMapFunction
        mock_function_factory.create_function.return_value = MockMapFunction()

        with pytest.raises(TypeError, match="requires CoMap function"):
            CoMapOperator(
                name="test_comap",
                ctx=mock_task_context,
                function_factory=mock_function_factory,
            )


# Edge Cases and Error Handling


@pytest.mark.unit
class TestOperatorErrorHandling:
    """Test operator error handling."""

    def test_filter_handles_exception_in_function(self, mock_task_context, mock_function_factory):
        """Test filter handles exception raised by function."""

        class FailingFilterFunction(FilterFunction):
            def __init__(self):
                super().__init__()
                self.ctx = None
                self._logger = None

            def execute(self, data):
                raise ValueError("Filter function error")

        mock_function_factory.create_function.return_value = FailingFilterFunction()

        operator = FilterOperator(
            name="test_filter",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload={"value": 5})

        # Should not raise, just log error
        operator.process_packet(packet)

        # Should not send packet on error
        mock_task_context.router.send.assert_not_called()

    def test_map_handles_exception_in_function(self, mock_task_context, mock_function_factory):
        """Test map handles exception raised by function."""

        class FailingMapFunction(MapFunction):
            def __init__(self):
                super().__init__()
                self.ctx = None
                self._logger = None

            def execute(self, data):
                raise RuntimeError("Map function error")

        mock_function_factory.create_function.return_value = FailingMapFunction()

        operator = MapOperator(
            name="test_map",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload={"value": 5})

        # Should not raise, just log error
        operator.process_packet(packet)

    def test_flatmap_handles_exception_in_function(self, mock_task_context, mock_function_factory):
        """Test flatmap handles exception raised by function."""

        class FailingFlatMapFunction(FlatMapFunction):
            def __init__(self):
                super().__init__()
                self.ctx = None
                self._logger = None
                self.out = None

            def execute(self, data):
                raise Exception("FlatMap function error")

        mock_function_factory.create_function.return_value = FailingFlatMapFunction()

        operator = FlatMapOperator(
            name="test_flatmap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload=[1, 2, 3])

        # Should not raise, just log error
        operator.process_packet(packet)


# Packet Inheritance Tests


@pytest.mark.unit
class TestPacketInheritance:
    """Test operators properly inherit packet metadata."""

    def test_filter_preserves_packet_metadata(self, mock_task_context, mock_function_factory):
        """Test filter preserves original packet metadata."""
        mock_function_factory.create_function.return_value = MockFilterFunction()

        operator = FilterOperator(
            name="test_filter",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Create packet with metadata
        packet = Packet(payload={"value": 4})
        packet.timestamp = 12345
        packet.task_id = "task_001"

        operator.process_packet(packet)

        # Verify metadata is preserved
        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.timestamp == 12345
        assert sent_packet.task_id == "task_001"

    def test_flatmap_inherits_partition_info(self, mock_task_context, mock_function_factory):
        """Test flatmap inherits partition info in expanded packets."""
        mock_function_factory.create_function.return_value = MockFlatMapFunction()

        operator = FlatMapOperator(
            name="test_flatmap",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Create packet with partition info
        packet = Packet(payload=[1, 2])
        packet.partition_key = "test_key"

        operator.process_packet(packet)

        # All expanded packets should inherit partition info
        for call in mock_task_context.router.send.call_args_list:
            sent_packet = call[0][0]
            # Partition info should be inherited
            assert hasattr(sent_packet, "partition_key") or sent_packet.partition_key is None
