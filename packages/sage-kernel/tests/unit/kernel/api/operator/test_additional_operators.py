"""
Unit tests for additional Kernel API Operators.

Tests SourceOperator, SinkOperator, KeyByOperator, and JoinOperator.
"""

from unittest.mock import MagicMock

import pytest

from sage.common.core.functions import (
    BaseFunction,
    BaseJoinFunction,
    KeyByFunction,
    SinkFunction,
    SourceFunction,
)
from sage.kernel.api.operator.join_operator import JoinOperator
from sage.kernel.api.operator.keyby_operator import KeyByOperator
from sage.kernel.api.operator.sink_operator import SinkOperator
from sage.kernel.api.operator.source_operator import SourceOperator
from sage.kernel.runtime.communication.packet import Packet, StopSignal

# Mock Functions for Testing


class MockSourceFunction(SourceFunction):
    """Mock source function that generates test data."""

    def __init__(self, data_to_generate=None):
        super().__init__()
        self.ctx = None
        self._logger = None
        self.data_to_generate = data_to_generate if data_to_generate is not None else [1, 2, 3]
        self.index = 0

    def execute(self):
        if self.index < len(self.data_to_generate):
            data = self.data_to_generate[self.index]
            self.index += 1
            return data
        else:
            # Return StopSignal when exhausted
            return StopSignal("data_exhausted")


class MockSinkFunction(SinkFunction):
    """Mock sink function that collects data."""

    def __init__(self):
        super().__init__()
        self.ctx = None
        self._logger = None
        self.collected = []

    def execute(self, data):
        self.collected.append(data)
        return f"Processed: {data}"

    def close(self):
        """Called when receiving stop signal."""
        return f"Final count: {len(self.collected)}"


class MockKeyByFunction(KeyByFunction):
    """Mock keyby function that extracts key from dict."""

    def __init__(self):
        super().__init__()
        self.ctx = None
        self._logger = None

    def execute(self, data):
        if isinstance(data, dict) and "id" in data:
            return data["id"]
        return str(data)


class MockJoinFunction(BaseJoinFunction):
    """Mock join function for testing."""

    def __init__(self):
        super().__init__()
        self.ctx = None
        self._logger = None
        # is_join is a property in BaseJoinFunction, don't set it
        self.stream0_buffer = {}
        self.stream1_buffer = {}

    def execute(self, payload, join_key, stream_tag):
        """Simple join logic: buffer data and match on keys."""
        if stream_tag == 0:
            self.stream0_buffer[join_key] = payload
            # Check if matching key in stream1
            if join_key in self.stream1_buffer:
                return [{"left": payload, "right": self.stream1_buffer[join_key], "key": join_key}]
        elif stream_tag == 1:
            self.stream1_buffer[join_key] = payload
            # Check if matching key in stream0
            if join_key in self.stream0_buffer:
                return [{"left": self.stream0_buffer[join_key], "right": payload, "key": join_key}]
        return []  # Return empty list instead of None


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
    context.router.send = MagicMock(return_value=True)
    context.router.send_stop_signal = MagicMock()
    context.request_stop = MagicMock()
    context.set_stop_signal = MagicMock()
    return context


@pytest.fixture
def mock_function_factory():
    """Create a mock FunctionFactory."""
    factory = MagicMock()
    factory.create_function = MagicMock()
    return factory


# Test Cases - SourceOperator


@pytest.mark.unit
class TestSourceOperator:
    """Test SourceOperator implementation."""

    def test_source_operator_initialization(self, mock_task_context, mock_function_factory):
        """Test SourceOperator initialization."""
        mock_function_factory.create_function.return_value = MockSourceFunction()

        operator = SourceOperator(
            name="test_source",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        assert operator.name == mock_task_context.name
        assert operator.ctx == mock_task_context
        assert operator._stop_signal_sent is False
        assert operator.task is None

    def test_source_generates_data(self, mock_task_context, mock_function_factory):
        """Test source generates and sends data."""
        mock_function_factory.create_function.return_value = MockSourceFunction([10, 20])

        operator = SourceOperator(
            name="test_source",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Generate first data
        operator.process_packet()
        assert mock_task_context.router.send.call_count == 1
        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.payload == 10

        # Generate second data
        operator.process_packet()
        assert mock_task_context.router.send.call_count == 2
        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.payload == 20

    def test_source_handles_stop_signal(self, mock_task_context, mock_function_factory):
        """Test source handles StopSignal."""
        mock_function_factory.create_function.return_value = MockSourceFunction([])

        operator = SourceOperator(
            name="test_source",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Should generate StopSignal when data exhausted
        operator.process_packet()

        # Should send stop signal
        assert mock_task_context.router.send_stop_signal.called
        stop_signal = mock_task_context.router.send_stop_signal.call_args[0][0]
        assert isinstance(stop_signal, StopSignal)
        # Source is set to operator.name which is ctx.name
        assert stop_signal.source == mock_task_context.name

    def test_source_prevents_duplicate_stop_signal(self, mock_task_context, mock_function_factory):
        """Test source prevents duplicate stop signals."""
        source_func = MockSourceFunction([])
        mock_function_factory.create_function.return_value = source_func

        operator = SourceOperator(
            name="test_source",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # First stop signal
        operator.process_packet()
        assert mock_task_context.router.send_stop_signal.call_count == 1

        # Second attempt - should be prevented even if function returns StopSignal again
        # Reset function to generate another StopSignal
        source_func.index = 0
        operator.process_packet()
        # Should still be 1 due to _stop_signal_sent flag
        assert mock_task_context.router.send_stop_signal.call_count == 1

    def test_source_handles_send_failure(self, mock_task_context, mock_function_factory):
        """Test source handles send failure by stopping."""
        mock_function_factory.create_function.return_value = MockSourceFunction([10])
        # Simulate send failure
        mock_task_context.router.send = MagicMock(return_value=False)

        operator = SourceOperator(
            name="test_source",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        operator.process_packet()

        # Should send stop signal on failure
        assert mock_task_context.router.send_stop_signal.called


# Test Cases - SinkOperator


@pytest.mark.unit
class TestSinkOperator:
    """Test SinkOperator implementation."""

    def test_sink_operator_initialization(self, mock_task_context, mock_function_factory):
        """Test SinkOperator initialization."""
        mock_function_factory.create_function.return_value = MockSinkFunction()

        operator = SinkOperator(
            name="test_sink",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        assert operator.name == mock_task_context.name
        assert operator.ctx == mock_task_context

    def test_sink_processes_data(self, mock_task_context, mock_function_factory):
        """Test sink processes incoming data."""
        sink_func = MockSinkFunction()
        mock_function_factory.create_function.return_value = sink_func

        operator = SinkOperator(
            name="test_sink",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Process data
        packet = Packet(payload={"value": 100})
        operator.process_packet(packet)

        # Verify data was collected
        assert len(sink_func.collected) == 1
        assert sink_func.collected[0] == {"value": 100}

    def test_sink_handles_stop_signal(self, mock_task_context, mock_function_factory):
        """Test sink handles stop signal and calls close()."""
        sink_func = MockSinkFunction()
        mock_function_factory.create_function.return_value = sink_func

        operator = SinkOperator(
            name="test_sink",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Add some data
        operator.process_packet(Packet(payload=1))
        operator.process_packet(Packet(payload=2))

        # Handle stop signal
        operator.handle_stop_signal()

        # Verify close() was called (we can't directly check but it should log)
        assert mock_task_context.logger.info.called

    def test_sink_handles_empty_packet(self, mock_task_context, mock_function_factory):
        """Test sink handles empty packet."""
        sink_func = MockSinkFunction()
        mock_function_factory.create_function.return_value = sink_func

        operator = SinkOperator(
            name="test_sink",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        operator.process_packet(None)

        # Should log warning but not crash
        assert mock_task_context.logger.warning.called
        assert len(sink_func.collected) == 0

    def test_sink_handles_exception(self, mock_task_context, mock_function_factory):
        """Test sink handles exception in processing."""

        class FailingSinkFunction(SinkFunction):
            def __init__(self):
                super().__init__()
                self.ctx = None
                self._logger = None

            def execute(self, data):
                raise RuntimeError("Sink processing error")

        mock_function_factory.create_function.return_value = FailingSinkFunction()

        operator = SinkOperator(
            name="test_sink",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload={"value": 100})
        operator.process_packet(packet)

        # Should log error but not crash
        assert mock_task_context.logger.error.called


# Test Cases - KeyByOperator


@pytest.mark.unit
class TestKeyByOperator:
    """Test KeyByOperator implementation."""

    def test_keyby_operator_initialization(self, mock_task_context, mock_function_factory):
        """Test KeyByOperator initialization with different strategies."""
        mock_function_factory.create_function.return_value = MockKeyByFunction()

        operator = KeyByOperator(
            name="test_keyby",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
            partition_strategy="hash",
        )

        assert operator.name == mock_task_context.name
        assert operator.partition_strategy == "hash"

    def test_keyby_extracts_key_hash_strategy(self, mock_task_context, mock_function_factory):
        """Test keyby extracts key with hash strategy."""
        mock_function_factory.create_function.return_value = MockKeyByFunction()

        operator = KeyByOperator(
            name="test_keyby",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
            partition_strategy="hash",
        )

        packet = Packet(payload={"id": "user123", "value": 100})
        operator.process_packet(packet)

        # Verify packet was sent with key
        assert mock_task_context.router.send.called
        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.partition_key == "user123"
        assert sent_packet.partition_strategy == "hash"

    def test_keyby_broadcast_strategy(self, mock_task_context, mock_function_factory):
        """Test keyby with broadcast strategy."""
        mock_function_factory.create_function.return_value = MockKeyByFunction()

        operator = KeyByOperator(
            name="test_keyby",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
            partition_strategy="broadcast",
        )

        packet = Packet(payload={"id": "user456", "value": 200})
        operator.process_packet(packet)

        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.partition_strategy == "broadcast"

    def test_keyby_round_robin_strategy(self, mock_task_context, mock_function_factory):
        """Test keyby with round_robin strategy."""
        mock_function_factory.create_function.return_value = MockKeyByFunction()

        operator = KeyByOperator(
            name="test_keyby",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
            partition_strategy="round_robin",
        )

        packet = Packet(payload={"id": "user789", "value": 300})
        operator.process_packet(packet)

        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.partition_strategy == "round_robin"

    def test_keyby_handles_exception(self, mock_task_context, mock_function_factory):
        """Test keyby handles exception and falls back to original packet."""

        class FailingKeyByFunction(KeyByFunction):
            def __init__(self):
                super().__init__()
                self.ctx = None
                self._logger = None

            def execute(self, data):
                raise ValueError("Key extraction error")

        mock_function_factory.create_function.return_value = FailingKeyByFunction()

        operator = KeyByOperator(
            name="test_keyby",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload={"id": "user123", "value": 100})
        operator.process_packet(packet)

        # Should still send packet (fallback behavior)
        assert mock_task_context.router.send.called

    def test_keyby_handles_empty_packet(self, mock_task_context, mock_function_factory):
        """Test keyby handles empty packet."""
        mock_function_factory.create_function.return_value = MockKeyByFunction()

        operator = KeyByOperator(
            name="test_keyby",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        operator.process_packet(None)

        # Should not send packet
        mock_task_context.router.send.assert_not_called()


# Test Cases - JoinOperator


@pytest.mark.unit
class TestJoinOperator:
    """Test JoinOperator implementation."""

    def test_join_operator_initialization(self, mock_task_context, mock_function_factory):
        """Test JoinOperator initialization."""
        mock_function_factory.create_function.return_value = MockJoinFunction()

        operator = JoinOperator(
            name="test_join",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        assert operator.name == mock_task_context.name
        assert operator._validated is True
        assert operator.processed_count == 0
        assert operator.emitted_count == 0

    def test_join_validation_requires_join_function(self, mock_task_context, mock_function_factory):
        """Test join validation rejects non-join functions."""

        class NonJoinFunction(BaseFunction):
            def __init__(self):
                super().__init__()
                self.ctx = None
                self._logger = None

            def execute(self, data):
                return data

        mock_function_factory.create_function.return_value = NonJoinFunction()

        with pytest.raises(TypeError, match="requires Join function"):
            JoinOperator(
                name="test_join",
                ctx=mock_task_context,
                function_factory=mock_function_factory,
            )

    def test_join_processes_keyed_packets(self, mock_task_context, mock_function_factory):
        """Test join processes keyed packets from two streams."""
        join_func = MockJoinFunction()
        mock_function_factory.create_function.return_value = join_func

        operator = JoinOperator(
            name="test_join",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Stream 0 packet
        packet0 = Packet(payload={"data": "left1"})
        packet0.partition_key = "key1"
        packet0.input_index = 0

        operator.process_packet(packet0)
        assert operator.processed_count == 1

        # Stream 1 packet with matching key - should produce join result
        packet1 = Packet(payload={"data": "right1"})
        packet1.partition_key = "key1"
        packet1.input_index = 1

        operator.process_packet(packet1)
        assert operator.processed_count == 2

        # Should have sent join result
        assert mock_task_context.router.send.called

    def test_join_requires_keyed_packets(self, mock_task_context, mock_function_factory):
        """Test join requires keyed packets."""
        mock_function_factory.create_function.return_value = MockJoinFunction()

        operator = JoinOperator(
            name="test_join",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Non-keyed packet
        packet = Packet(payload={"data": "test"})
        operator.process_packet(packet)

        # Should log warning and not process
        assert mock_task_context.logger.warning.called
        assert operator.processed_count == 0

    def test_join_handles_empty_packet(self, mock_task_context, mock_function_factory):
        """Test join handles empty packet."""
        mock_function_factory.create_function.return_value = MockJoinFunction()

        operator = JoinOperator(
            name="test_join",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        operator.process_packet(None)

        # Should not process
        assert operator.processed_count == 0

    def test_join_handles_none_payload(self, mock_task_context, mock_function_factory):
        """Test join handles keyed packet with None payload."""
        mock_function_factory.create_function.return_value = MockJoinFunction()

        operator = JoinOperator(
            name="test_join",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        packet = Packet(payload=None)
        packet.partition_key = "key1"
        packet.input_index = 0

        operator.process_packet(packet)

        # Should skip None payload
        assert operator.processed_count == 0

    def test_join_non_matching_keys(self, mock_task_context, mock_function_factory):
        """Test join with non-matching keys."""
        join_func = MockJoinFunction()
        mock_function_factory.create_function.return_value = join_func

        operator = JoinOperator(
            name="test_join",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Different keys
        packet0 = Packet(payload={"data": "left"})
        packet0.partition_key = "key1"
        packet0.input_index = 0

        packet1 = Packet(payload={"data": "right"})
        packet1.partition_key = "key2"
        packet1.input_index = 1

        operator.process_packet(packet0)
        operator.process_packet(packet1)

        # Should buffer but not emit join result
        assert operator.processed_count == 2
        # No join output should be sent (function returns None for non-matching)
        # The operator would call send only if function returns non-None list


# Packet Metadata Tests


@pytest.mark.unit
class TestOperatorPacketHandling:
    """Test operators handle packet metadata correctly."""

    def test_keyby_preserves_original_payload(self, mock_task_context, mock_function_factory):
        """Test keyby preserves original payload."""
        mock_function_factory.create_function.return_value = MockKeyByFunction()

        operator = KeyByOperator(
            name="test_keyby",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        original_payload = {"id": "user123", "value": 999}
        packet = Packet(payload=original_payload)
        operator.process_packet(packet)

        sent_packet = mock_task_context.router.send.call_args[0][0]
        assert sent_packet.payload == original_payload

    def test_join_tracks_stream_index(self, mock_task_context, mock_function_factory):
        """Test join correctly tracks stream indices."""
        join_func = MockJoinFunction()
        mock_function_factory.create_function.return_value = join_func

        operator = JoinOperator(
            name="test_join",
            ctx=mock_task_context,
            function_factory=mock_function_factory,
        )

        # Verify different stream indices are tracked
        packet0 = Packet(payload={"data": "stream0"})
        packet0.partition_key = "k1"
        packet0.input_index = 0

        packet1 = Packet(payload={"data": "stream1"})
        packet1.partition_key = "k1"
        packet1.input_index = 1

        operator.process_packet(packet0)
        operator.process_packet(packet1)

        # Both buffers should have data
        assert "k1" in join_func.stream0_buffer
        assert "k1" in join_func.stream1_buffer
