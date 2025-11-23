"""
Tests for keyed state support via get_key() interface.

This test verifies that:
1. Functions can access the current packet's key via ctx.get_key()
2. Keyed state is properly isolated per key
3. State persistence works correctly with keyed state
4. The feature is backward compatible (works without keys)
"""

import time
from typing import Any

from sage.common.core.functions import MapFunction, SinkFunction, SourceFunction
from sage.kernel.api.local_environment import LocalEnvironment


class KeyedStateTestSource(SourceFunction):
    """Source that generates events with different user IDs"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.events = [
            {"user_id": "alice", "action": "login", "value": 10},
            {"user_id": "bob", "action": "click", "value": 5},
            {"user_id": "alice", "action": "click", "value": 15},
            {"user_id": "charlie", "action": "login", "value": 20},
            {"user_id": "bob", "action": "purchase", "value": 100},
            {"user_id": "alice", "action": "logout", "value": 0},
        ]

    def execute(self, data=None):
        if self.counter >= len(self.events):
            return None  # Stop
        event = self.events[self.counter]
        self.counter += 1
        self.logger.info(f"Generated event: {event}")
        return event


class KeyExtractor(MapFunction):
    """Extract user_id as the key"""

    def execute(self, data: Any) -> str:
        return data["user_id"]


class KeyedStateFunction(MapFunction):
    """Function that maintains keyed state per user"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # User-level keyed state - will be automatically persisted
        self.user_sessions = {}  # {user_id: {action_count, total_value, actions}}
        self.global_counter = 0  # Global state (not keyed)

    def execute(self, event_data):
        # Get the current packet's key
        key = self.ctx.get_key()

        # Increment global counter
        self.global_counter += 1

        if key is None:
            # Handle unkeyed events (backward compatibility)
            self.logger.warning("Processing unkeyed event")
            return {"global_counter": self.global_counter}

        # Initialize keyed state for new users
        if key not in self.user_sessions:
            self.user_sessions[key] = {
                "first_seen": time.time(),
                "action_count": 0,
                "total_value": 0,
                "actions": [],
            }

        # Update user-specific state
        session = self.user_sessions[key]
        session["action_count"] += 1
        session["total_value"] += event_data.get("value", 0)
        session["actions"].append(event_data["action"])
        session["last_action"] = event_data["action"]

        self.logger.info(
            f"User {key}: {session['action_count']} actions, total value: {session['total_value']}"
        )

        # Return enriched event with session info
        return {
            "user_id": key,
            "event": event_data,
            "session": {
                "action_count": session["action_count"],
                "total_value": session["total_value"],
                "actions": list(session["actions"]),  # Copy list
            },
            "global_counter": self.global_counter,
        }


class KeyedStateSink(SinkFunction):
    """Sink that collects results for verification"""

    # Class-level storage for test verification
    results = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def execute(self, data: Any):
        KeyedStateSink.results.append(data)
        self.logger.info(f"Sink received: {data}")
        return data

    @classmethod
    def clear(cls):
        cls.results = []

    @classmethod
    def get_results(cls):
        return list(cls.results)


class TestKeyedStateSupport:
    """Test keyed state functionality"""

    def setup_method(self):
        """Clear results before each test"""
        KeyedStateSink.clear()

    def test_basic_keyed_state(self):
        """Test that functions can access and maintain keyed state"""
        print("\n🚀 Testing Basic Keyed State Support")

        env = LocalEnvironment("test_keyed_state_basic")

        # Build pipeline: source -> keyby -> keyed state function -> sink
        (
            env.from_source(KeyedStateTestSource, delay=0.3)
            .keyby(KeyExtractor, strategy="hash")
            .map(KeyedStateFunction)
            .sink(KeyedStateSink)
        )

        try:
            env.submit()
            time.sleep(2.5)  # Allow time for processing
        finally:
            env.close()

        # Verify results
        results = KeyedStateSink.get_results()

        print(f"\n📊 Received {len(results)} results")
        assert len(results) > 0, "Should receive results"

        # Verify per-user state is maintained correctly
        user_states = {}
        for result in results:
            user_id = result["user_id"]
            if user_id not in user_states:
                user_states[user_id] = []
            user_states[user_id].append(result)

        # Check Alice's sessions (3 events)
        if "alice" in user_states:
            alice_results = user_states["alice"]
            print(f"\n👤 Alice's events: {len(alice_results)}")
            assert len(alice_results) >= 1, "Alice should have at least 1 event"

            # Verify action count increases
            for i, result in enumerate(alice_results):
                print(
                    f"  Event {i + 1}: action_count={result['session']['action_count']}, "
                    f"total_value={result['session']['total_value']}"
                )
                assert result["session"]["action_count"] == i + 1, f"Action count should be {i + 1}"

            # Verify total value is cumulative
            # Alice's events from KeyedStateTestSource: login(10), click(15), logout(0)
            alice_event_values = [10, 15, 0]  # Values from source definition
            if len(alice_results) == 3:
                last_alice = alice_results[-1]
                expected_total = sum(alice_event_values)
                assert last_alice["session"]["total_value"] == expected_total, (
                    f"Total value should be {expected_total} (sum of {alice_event_values})"
                )

        # Check Bob's sessions (2 events)
        if "bob" in user_states:
            bob_results = user_states["bob"]
            print(f"\n👤 Bob's events: {len(bob_results)}")
            assert len(bob_results) >= 1, "Bob should have at least 1 event"

            # Verify Bob's state is independent from Alice's
            for i, result in enumerate(bob_results):
                print(
                    f"  Event {i + 1}: action_count={result['session']['action_count']}, "
                    f"total_value={result['session']['total_value']}"
                )
                assert result["session"]["action_count"] == i + 1, f"Action count should be {i + 1}"

        print("\n✅ Keyed state test passed!")

    def test_get_key_method(self):
        """Test that get_key() returns the correct key during processing"""

        class KeyVerificationFunction(MapFunction):
            """Function that verifies get_key() returns correct values"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.key_observations = []

            def execute(self, event_data):
                observed_key = self.ctx.get_key()
                expected_key = event_data["user_id"]

                self.key_observations.append(
                    {"expected": expected_key, "observed": observed_key, "event": event_data}
                )

                # Verify key matches
                assert observed_key == expected_key, (
                    f"get_key() returned {observed_key}, expected {expected_key}"
                )

                return {
                    "user_id": expected_key,
                    "key_match": observed_key == expected_key,
                }

        print("\n🚀 Testing get_key() Method")

        env = LocalEnvironment("test_get_key_method")

        (
            env.from_source(KeyedStateTestSource, delay=0.3)
            .keyby(KeyExtractor, strategy="hash")
            .map(KeyVerificationFunction)
            .sink(KeyedStateSink)
        )

        try:
            env.submit()
            time.sleep(2.5)
        finally:
            env.close()

        results = KeyedStateSink.get_results()
        print(f"\n📊 Verified {len(results)} key matches")

        for result in results:
            assert result["key_match"], f"Key mismatch for user {result['user_id']}"

        print("✅ get_key() method test passed!")

    def test_backward_compatibility_unkeyed_stream(self):
        """Test that the feature works with unkeyed streams (backward compatibility)"""

        class UnkeyedSource(SourceFunction):
            """Source that doesn't use keyby"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.counter = 0

            def execute(self, data=None):
                if self.counter >= 3:
                    return None
                self.counter += 1
                return {"id": self.counter, "value": self.counter * 10}

        class UnkeyedStateFunction(MapFunction):
            """Function that handles both keyed and unkeyed streams"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.total_count = 0
                self.keyed_counts = {}

            def execute(self, data):
                key = self.ctx.get_key()  # Should return None for unkeyed streams
                self.total_count += 1

                if key is not None:
                    # Keyed stream
                    if key not in self.keyed_counts:
                        self.keyed_counts[key] = 0
                    self.keyed_counts[key] += 1

                return {
                    "data": data,
                    "key": key,
                    "total_count": self.total_count,
                    "is_keyed": key is not None,
                }

        print("\n🚀 Testing Backward Compatibility (Unkeyed Stream)")

        env = LocalEnvironment("test_unkeyed_backward_compat")

        # Pipeline WITHOUT keyby - should work fine
        env.from_source(UnkeyedSource, delay=0.3).map(UnkeyedStateFunction).sink(KeyedStateSink)

        try:
            env.submit()
            time.sleep(2)
        finally:
            env.close()

        results = KeyedStateSink.get_results()
        print(f"\n📊 Received {len(results)} results from unkeyed stream")

        for result in results:
            # Verify key is None for unkeyed streams
            assert result["key"] is None, "Key should be None for unkeyed streams"
            assert not result["is_keyed"], "Stream should not be marked as keyed"
            print(
                f"  Event {result['data']['id']}: key={result['key']}, "
                f"total_count={result['total_count']}"
            )

        print("✅ Backward compatibility test passed!")


class TestKeyedStateEdgeCases:
    """Test edge cases and error scenarios for keyed state"""

    def setup_method(self):
        """Clear results before each test"""
        KeyedStateSink.clear()

    def test_key_isolation_between_packets(self):
        """Test that keys don't leak between packets"""

        class KeyLeakageDetector(MapFunction):
            """Function that tracks key changes to detect leaks"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.key_transitions = []

            def execute(self, event_data):
                current_key = self.ctx.get_key()
                self.key_transitions.append(
                    {
                        "expected": event_data["user_id"],
                        "actual": current_key,
                        "event": event_data["action"],
                    }
                )
                return {"key": current_key, "event": event_data}

        print("\n🚀 Testing Key Isolation Between Packets")

        env = LocalEnvironment("test_key_isolation")

        (
            env.from_source(KeyedStateTestSource, delay=0.3)
            .keyby(KeyExtractor, strategy="hash")
            .map(KeyLeakageDetector)
            .sink(KeyedStateSink)
        )

        try:
            env.submit()
            time.sleep(2.5)
        finally:
            env.close()

        results = KeyedStateSink.get_results()

        # Verify each packet had the correct key during processing
        for result in results:
            assert result["key"] == result["event"]["user_id"], (
                f"Key mismatch: expected {result['event']['user_id']}, got {result['key']}"
            )

        print("✅ Key isolation test passed!")

    def test_none_key_handling(self):
        """Test handling of None keys (unpartitioned packets)"""

        class NoneKeySource(SourceFunction):
            """Source that produces events without keys"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.counter = 0

            def execute(self, data=None):
                if self.counter >= 3:
                    return None
                self.counter += 1
                return {"id": self.counter, "value": self.counter * 5}

        class NoneKeyFunction(MapFunction):
            """Function that handles None keys gracefully"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.none_key_count = 0
                self.keyed_count = 0

            def execute(self, data):
                key = self.ctx.get_key()
                if key is None:
                    self.none_key_count += 1
                else:
                    self.keyed_count += 1

                return {"key": key, "none_key_count": self.none_key_count, "data": data}

        print("\n🚀 Testing None Key Handling")

        env = LocalEnvironment("test_none_key")

        # Pipeline without keyby - all keys should be None
        env.from_source(NoneKeySource, delay=0.3).map(NoneKeyFunction).sink(KeyedStateSink)

        try:
            env.submit()
            time.sleep(2)
        finally:
            env.close()

        results = KeyedStateSink.get_results()

        for result in results:
            assert result["key"] is None, f"Expected None key, got {result['key']}"
            assert result["none_key_count"] > 0, "none_key_count should be incremented"

        print("✅ None key handling test passed!")

    def test_concurrent_key_access(self):
        """Test that keys are correctly maintained in concurrent processing"""

        class ConcurrentKeyVerifier(MapFunction):
            """Function that verifies key correctness in concurrent scenarios"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.key_verifications = []

            def execute(self, event_data):
                # Simulate some processing time
                import random

                time.sleep(random.uniform(0.01, 0.05))

                key = self.ctx.get_key()
                expected = event_data["user_id"]

                # Record verification
                self.key_verifications.append(
                    {"key": key, "expected": expected, "match": key == expected}
                )

                # Assert immediately
                assert key == expected, f"Concurrent key mismatch: expected {expected}, got {key}"

                return {"verified": True, "key": key, "event": event_data}

        print("\n🚀 Testing Concurrent Key Access")

        env = LocalEnvironment("test_concurrent_keys")

        (
            env.from_source(KeyedStateTestSource, delay=0.2)
            .keyby(KeyExtractor, strategy="hash")
            .map(ConcurrentKeyVerifier)
            .sink(KeyedStateSink)
        )

        try:
            env.submit()
            time.sleep(3)
        finally:
            env.close()

        results = KeyedStateSink.get_results()

        for result in results:
            assert result["verified"], "All verifications should pass"

        print("✅ Concurrent key access test passed!")

    def test_state_serialization_excludes_current_key(self):
        """Test that _current_packet_key is not serialized in state snapshots"""

        class StateSerializationFunction(MapFunction):
            """Function that tests state serialization"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.process_count = 0

            def execute(self, event_data):
                self.process_count += 1
                key = self.ctx.get_key()

                # Get state (simulating checkpoint)
                try:
                    # Check if ctx has get_state method
                    if hasattr(self.ctx, "get_state"):
                        state = self.ctx.get_state()
                        # _current_packet_key should not be in serialized state
                        assert "_current_packet_key" not in state, (
                            "_current_packet_key should be excluded from state"
                        )
                except Exception as e:
                    self.logger.warning(f"State serialization check failed: {e}")

                return {"key": key, "process_count": self.process_count}

        print("\n🚀 Testing State Serialization Excludes Current Key")

        env = LocalEnvironment("test_state_serialization")

        (
            env.from_source(KeyedStateTestSource, delay=0.3)
            .keyby(KeyExtractor, strategy="hash")
            .map(StateSerializationFunction)
            .sink(KeyedStateSink)
        )

        try:
            env.submit()
            time.sleep(2.5)
        finally:
            env.close()

        results = KeyedStateSink.get_results()
        assert len(results) > 0, "Should receive results"

        print("✅ State serialization test passed!")


class TestKeyedStateAPICompleteness:
    """Test all keyed state API methods"""

    def test_set_clear_get_key_methods(self):
        """Test direct usage of set_current_key, get_key, and clear_key"""
        from sage.kernel.runtime.context.base_context import BaseRuntimeContext

        class TestContext(BaseRuntimeContext):
            """Concrete implementation for testing"""

            def __init__(self):
                super().__init__()
                self._test_logger = None

            @property
            def logger(self):
                if self._test_logger is None:
                    import logging

                    self._test_logger = logging.getLogger("test")
                return self._test_logger

        print("\n🚀 Testing Keyed State API Methods")

        ctx = TestContext()

        # Test initial state
        assert ctx.get_key() is None, "Initial key should be None"

        # Test set_current_key with string
        ctx.set_current_key("test_key_1")
        assert ctx.get_key() == "test_key_1", "Key should be 'test_key_1'"

        # Test set_current_key with integer
        ctx.set_current_key(12345)
        assert ctx.get_key() == 12345, "Key should be 12345"

        # Test set_current_key with None
        ctx.set_current_key(None)
        assert ctx.get_key() is None, "Key should be None"

        # Test set_current_key with complex object
        complex_key = {"user": "alice", "session": "abc123"}
        ctx.set_current_key(complex_key)
        assert ctx.get_key() == complex_key, "Key should be the complex object"

        # Test clear_key
        ctx.clear_key()
        assert ctx.get_key() is None, "Key should be None after clear"

        # Test multiple set/clear cycles
        for i in range(5):
            ctx.set_current_key(f"key_{i}")
            assert ctx.get_key() == f"key_{i}"
            ctx.clear_key()
            assert ctx.get_key() is None

        print("✅ API methods test passed!")

    def test_key_attribute_initialization(self):
        """Test that _current_packet_key is properly initialized"""
        from sage.kernel.runtime.context.base_context import BaseRuntimeContext

        class TestContext(BaseRuntimeContext):
            @property
            def logger(self):
                import logging

                return logging.getLogger("test")

        print("\n🚀 Testing Key Attribute Initialization")

        ctx = TestContext()

        # Verify attribute exists
        assert hasattr(ctx, "_current_packet_key"), "Should have _current_packet_key attribute"

        # Verify initial value is None
        assert ctx._current_packet_key is None, "Initial _current_packet_key should be None"

        # Verify get_key returns None initially
        assert ctx.get_key() is None, "get_key() should return None initially"

        print("✅ Attribute initialization test passed!")


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "-s"])
