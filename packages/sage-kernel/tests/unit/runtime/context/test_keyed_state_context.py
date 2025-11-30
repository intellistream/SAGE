"""
Unit tests for keyed state support in BaseRuntimeContext.

These tests directly test the set_current_key, get_key, and clear_key methods
to ensure high coverage of the new keyed state functionality.
"""

import pytest

from sage.kernel.runtime.context.base_context import BaseRuntimeContext


class ConcreteContext(BaseRuntimeContext):
    """Concrete implementation of BaseRuntimeContext for testing"""

    def __init__(self):
        super().__init__()
        self._test_logger = None

    @property
    def logger(self):
        """Return a test logger"""
        if self._test_logger is None:
            import logging

            self._test_logger = logging.getLogger("test_context")
        return self._test_logger


class TestBaseRuntimeContextKeyedState:
    """Test keyed state functionality in BaseRuntimeContext"""

    def test_initial_key_is_none(self):
        """Test that initial key is None"""
        ctx = ConcreteContext()
        assert ctx.get_key() is None
        assert ctx._current_packet_key is None

    def test_set_current_key_string(self):
        """Test setting a string key"""
        ctx = ConcreteContext()
        ctx.set_current_key("test_key")
        assert ctx.get_key() == "test_key"
        assert ctx._current_packet_key == "test_key"

    def test_set_current_key_integer(self):
        """Test setting an integer key"""
        ctx = ConcreteContext()
        ctx.set_current_key(42)
        assert ctx.get_key() == 42
        assert ctx._current_packet_key == 42

    def test_set_current_key_tuple(self):
        """Test setting a tuple key"""
        ctx = ConcreteContext()
        key = ("user", "session", 123)
        ctx.set_current_key(key)
        assert ctx.get_key() == key
        assert ctx._current_packet_key == key

    def test_set_current_key_dict(self):
        """Test setting a dict key"""
        ctx = ConcreteContext()
        key = {"user_id": "alice", "session": "abc123"}
        ctx.set_current_key(key)
        assert ctx.get_key() == key
        assert ctx._current_packet_key == key

    def test_set_current_key_none(self):
        """Test setting None as key (for unkeyed streams)"""
        ctx = ConcreteContext()
        ctx.set_current_key("initial")
        ctx.set_current_key(None)
        assert ctx.get_key() is None
        assert ctx._current_packet_key is None

    def test_clear_key(self):
        """Test clearing the current key"""
        ctx = ConcreteContext()
        ctx.set_current_key("test_key")
        assert ctx.get_key() == "test_key"

        ctx.clear_key()
        assert ctx.get_key() is None
        assert ctx._current_packet_key is None

    def test_clear_key_when_none(self):
        """Test clearing key when it's already None"""
        ctx = ConcreteContext()
        ctx.clear_key()
        assert ctx.get_key() is None

    def test_multiple_set_clear_cycles(self):
        """Test multiple set/clear cycles"""
        ctx = ConcreteContext()

        for i in range(10):
            key = f"key_{i}"
            ctx.set_current_key(key)
            assert ctx.get_key() == key

            ctx.clear_key()
            assert ctx.get_key() is None

    def test_key_overwrite(self):
        """Test that setting a new key overwrites the old one"""
        ctx = ConcreteContext()

        ctx.set_current_key("key1")
        assert ctx.get_key() == "key1"

        ctx.set_current_key("key2")
        assert ctx.get_key() == "key2"

        ctx.set_current_key(123)
        assert ctx.get_key() == 123

    def test_get_key_does_not_modify_state(self):
        """Test that get_key() doesn't modify the key"""
        ctx = ConcreteContext()
        ctx.set_current_key("test")

        # Call get_key multiple times
        for _ in range(5):
            assert ctx.get_key() == "test"

        # Key should still be set
        assert ctx._current_packet_key == "test"

    def test_attribute_exists_after_init(self):
        """Test that _current_packet_key attribute exists after initialization"""
        ctx = ConcreteContext()
        assert hasattr(ctx, "_current_packet_key")
        assert ctx._current_packet_key is None

    def test_key_isolation(self):
        """Test that keys are isolated between different context instances"""
        ctx1 = ConcreteContext()
        ctx2 = ConcreteContext()

        ctx1.set_current_key("key1")
        ctx2.set_current_key("key2")

        assert ctx1.get_key() == "key1"
        assert ctx2.get_key() == "key2"

        ctx1.clear_key()
        assert ctx1.get_key() is None
        assert ctx2.get_key() == "key2"  # ctx2 should be unaffected


class TestKeyedStateDocumentation:
    """Test that documentation examples work correctly"""

    def test_docstring_example(self):
        """Test the example from get_key() docstring"""
        # Simulate the example (without actual function execution)
        ctx = ConcreteContext()

        # Simulate processing a packet for user "alice"
        ctx.set_current_key("alice")

        user_sessions = {}
        user_id = ctx.get_key()

        if user_id not in user_sessions:
            user_sessions[user_id] = {"count": 0}
        user_sessions[user_id]["count"] += 1

        assert user_sessions["alice"]["count"] == 1

        # Process another event for alice
        user_id = ctx.get_key()
        user_sessions[user_id]["count"] += 1
        assert user_sessions["alice"]["count"] == 2

        # Clear and process for bob
        ctx.clear_key()
        ctx.set_current_key("bob")

        user_id = ctx.get_key()
        if user_id not in user_sessions:
            user_sessions[user_id] = {"count": 0}
        user_sessions[user_id]["count"] += 1

        assert user_sessions["bob"]["count"] == 1
        assert user_sessions["alice"]["count"] == 2  # alice unchanged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
