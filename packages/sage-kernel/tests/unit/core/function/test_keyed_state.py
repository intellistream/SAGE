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


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "-s"])
