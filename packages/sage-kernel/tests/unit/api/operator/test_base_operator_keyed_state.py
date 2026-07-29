"""
Unit tests for keyed state support in BaseOperator.

These tests verify that receive_packet() correctly sets and clears keys
during packet processing.
"""

from unittest.mock import Mock

import pytest

from sage.kernel.api.operator.base_operator import BaseOperator
from sage.kernel.runtime.communication.packet import Packet


class ConcreteOperator(BaseOperator):
    """Concrete implementation of BaseOperator for testing"""

    def process_packet(self, packet=None):
        """Process packet implementation"""
        # Track that process_packet was called
        if not hasattr(self, "processed_packets"):
            self.processed_packets = []
        self.processed_packets.append(packet)


class TestBaseOperatorKeyedState:
    """Test keyed state functionality in BaseOperator"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create mock context
        self.mock_ctx = Mock()
        self.mock_ctx.name = "test_task"
        self.mock_ctx.logger = Mock()
        self.mock_ctx.set_current_key = Mock()
        self.mock_ctx.clear_key = Mock()
        self.mock_ctx.get_key = Mock(return_value=None)

        # Create mock function factory
        self.mock_factory = Mock()
        self.mock_function = Mock()
        self.mock_factory.create_function = Mock(return_value=self.mock_function)

    def test_receive_packet_sets_key(self):
        """Test that receive_packet sets the packet's key"""
        operator = ConcreteOperator(self.mock_factory, self.mock_ctx)

        # Create packet with a key
        packet = Mock(spec=Packet)
        packet.partition_key = "test_key_123"

        operator.receive_packet(packet)

        # Verify set_current_key was called with the packet's key
        self.mock_ctx.set_current_key.assert_called_once_with("test_key_123")

    def test_receive_packet_clears_key_after_processing(self):
        """Test that receive_packet clears the key after processing"""
        operator = ConcreteOperator(self.mock_factory, self.mock_ctx)

        packet = Mock(spec=Packet)
        packet.partition_key = "test_key"

        operator.receive_packet(packet)

        # Verify clear_key was called
        self.mock_ctx.clear_key.assert_called_once()

    def test_receive_packet_clears_key_on_exception(self):
        """Test that receive_packet clears key even if processing raises an exception"""

        class FailingOperator(BaseOperator):
            def process_packet(self, packet=None):
                raise ValueError("Processing failed")

        operator = FailingOperator(self.mock_factory, self.mock_ctx)

        packet = Mock(spec=Packet)
        packet.partition_key = "test_key"

        # Process should raise, but clear_key should still be called
        with pytest.raises(ValueError, match="Processing failed"):
            operator.receive_packet(packet)

        # Verify clear_key was called despite the exception
        self.mock_ctx.clear_key.assert_called_once()

    def test_receive_packet_with_none_key(self):
        """Test receive_packet with None as partition_key (unkeyed stream)"""
        operator = ConcreteOperator(self.mock_factory, self.mock_ctx)

        packet = Mock(spec=Packet)
        packet.partition_key = None

        operator.receive_packet(packet)

        # Should still call set_current_key with None
        self.mock_ctx.set_current_key.assert_called_once_with(None)
        self.mock_ctx.clear_key.assert_called_once()

    def test_receive_packet_none_packet(self):
        """Test receive_packet with None packet"""
        operator = ConcreteOperator(self.mock_factory, self.mock_ctx)

        operator.receive_packet(None)

        # Should log warning and not process
        self.mock_ctx.logger.warning.assert_called_once()
        # Should not call set_current_key or clear_key for None packet
        self.mock_ctx.set_current_key.assert_not_called()
        self.mock_ctx.clear_key.assert_not_called()

    def test_receive_packet_calls_process_packet(self):
        """Test that receive_packet calls process_packet"""
        operator = ConcreteOperator(self.mock_factory, self.mock_ctx)

        packet = Mock(spec=Packet)
        packet.partition_key = "key"

        operator.receive_packet(packet)

        # Verify packet was processed
        assert len(operator.processed_packets) == 1
        assert operator.processed_packets[0] == packet

    def test_receive_packet_key_lifecycle(self):
        """Test the complete lifecycle of key setting and clearing"""

        class KeyTrackingOperator(BaseOperator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.key_during_processing = None

            def process_packet(self, packet=None):
                # Capture the key during processing
                self.key_during_processing = self.ctx.get_key()

        # Configure mock to track key state
        current_key = [None]  # Use list to allow modification in nested function

        def set_key(key):
            current_key[0] = key

        def get_key():
            return current_key[0]

        def clear_key():
            current_key[0] = None

        self.mock_ctx.set_current_key = set_key
        self.mock_ctx.get_key = get_key
        self.mock_ctx.clear_key = clear_key

        operator = KeyTrackingOperator(self.mock_factory, self.mock_ctx)

        # Before processing, key should be None
        assert operator.ctx.get_key() is None

        packet = Mock(spec=Packet)
        packet.partition_key = "test_key"

        operator.receive_packet(packet)

        # After processing, key should be cleared
        assert operator.ctx.get_key() is None
        # But during processing, it should have been set
        assert operator.key_during_processing == "test_key"

    def test_receive_packet_with_complex_key(self):
        """Test receive_packet with complex object as key"""
        operator = ConcreteOperator(self.mock_factory, self.mock_ctx)

        complex_key = {"user_id": "alice", "session_id": "xyz", "shard": 3}
        packet = Mock(spec=Packet)
        packet.partition_key = complex_key

        operator.receive_packet(packet)

        self.mock_ctx.set_current_key.assert_called_once_with(complex_key)
        self.mock_ctx.clear_key.assert_called_once()

    def test_multiple_packets_sequential(self):
        """Test processing multiple packets sequentially"""
        operator = ConcreteOperator(self.mock_factory, self.mock_ctx)

        packets = [
            Mock(spec=Packet, partition_key="key1"),
            Mock(spec=Packet, partition_key="key2"),
            Mock(spec=Packet, partition_key="key3"),
        ]

        for packet in packets:
            operator.receive_packet(packet)

        # Each packet should have triggered set and clear
        assert self.mock_ctx.set_current_key.call_count == 3
        assert self.mock_ctx.clear_key.call_count == 3

        # Verify keys were set in order
        calls = self.mock_ctx.set_current_key.call_args_list
        assert calls[0][0][0] == "key1"
        assert calls[1][0][0] == "key2"
        assert calls[2][0][0] == "key3"


class TestBaseOperatorKeyedStateIntegration:
    """Integration tests for keyed state with real context"""

    def test_with_real_task_context(self):
        """Test receive_packet with a real TaskContext (if available)"""
        # This would require more complex setup with real TaskContext
        # For now, we rely on the integration test in test_keyed_state.py
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
