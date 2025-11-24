"""
Tests for sage.common.core.functions.join_function

Tests the Join function classes for multi-stream data joining.
"""

from sage.common.core.functions.join_function import BaseJoinFunction, UserOrderInnerJoin


class SimpleJoinFunction(BaseJoinFunction):
    """Simple join implementation for testing"""

    def __init__(self):
        super().__init__()
        self.left_data = {}
        self.right_data = {}

    def execute(self, payload, key, tag):
        results = []

        if tag == 0:  # Left stream
            self.left_data[key] = payload
            if key in self.right_data:
                results.append({"left": payload, "right": self.right_data[key], "key": key})

        elif tag == 1:  # Right stream
            self.right_data[key] = payload
            if key in self.left_data:
                results.append({"left": self.left_data[key], "right": payload, "key": key})

        return results


class TestBaseJoinFunction:
    """Tests for BaseJoinFunction class"""

    def test_is_join_property(self):
        """Test is_join property returns True"""
        func = SimpleJoinFunction()

        assert func.is_join is True

    def test_simple_join_left_first(self):
        """Test simple join with left data arriving first"""
        func = SimpleJoinFunction()

        # Left data arrives first
        result = func.execute({"name": "Alice"}, key="user_1", tag=0)
        assert len(result) == 0  # No match yet

        # Right data arrives
        result = func.execute({"order_id": "order_001"}, key="user_1", tag=1)
        assert len(result) == 1
        assert result[0]["left"] == {"name": "Alice"}
        assert result[0]["right"] == {"order_id": "order_001"}
        assert result[0]["key"] == "user_1"

    def test_simple_join_right_first(self):
        """Test simple join with right data arriving first"""
        func = SimpleJoinFunction()

        # Right data arrives first
        result = func.execute({"order_id": "order_002"}, key="user_2", tag=1)
        assert len(result) == 0  # No match yet

        # Left data arrives
        result = func.execute({"name": "Bob"}, key="user_2", tag=0)
        assert len(result) == 1
        assert result[0]["left"] == {"name": "Bob"}
        assert result[0]["right"] == {"order_id": "order_002"}

    def test_no_match_different_keys(self):
        """Test no join when keys don't match"""
        func = SimpleJoinFunction()

        func.execute({"name": "Alice"}, key="user_1", tag=0)
        result = func.execute({"order_id": "order_003"}, key="user_2", tag=1)

        assert len(result) == 0

    def test_multiple_keys(self):
        """Test joins with multiple different keys"""
        func = SimpleJoinFunction()

        # Add data for multiple keys
        func.execute({"name": "Alice"}, key="user_1", tag=0)
        func.execute({"name": "Bob"}, key="user_2", tag=0)

        result1 = func.execute({"order_id": "order_001"}, key="user_1", tag=1)
        result2 = func.execute({"order_id": "order_002"}, key="user_2", tag=1)

        assert len(result1) == 1
        assert result1[0]["left"]["name"] == "Alice"
        assert len(result2) == 1
        assert result2[0]["left"]["name"] == "Bob"


class TestUserOrderInnerJoin:
    """Tests for UserOrderInnerJoin implementation"""

    def test_initialization(self):
        """Test UserOrderInnerJoin initialization"""
        func = UserOrderInnerJoin()

        assert hasattr(func, "user_cache")
        assert hasattr(func, "order_cache")
        assert func.is_join is True

    def test_user_data_cached(self):
        """Test user data is cached"""
        func = UserOrderInnerJoin()

        user_data = {"user_id": "u1", "name": "Alice", "age": 30}
        result = func.execute(user_data, key="u1", tag=0)

        assert len(result) == 0  # No orders yet
        assert "u1" in func.user_cache
        assert func.user_cache["u1"] == user_data

    def test_order_cached_when_no_user(self):
        """Test order is cached when user doesn't exist yet"""
        func = UserOrderInnerJoin()

        order_data = {"order_id": "o1", "amount": 100}
        result = func.execute(order_data, key="u1", tag=1)

        assert len(result) == 0  # No user yet
        assert "u1" in func.order_cache
        assert order_data in func.order_cache["u1"]

    def test_join_when_user_exists(self):
        """Test join when user already exists"""
        func = UserOrderInnerJoin()

        # Add user first
        user_data = {"user_id": "u1", "name": "Alice"}
        func.execute(user_data, key="u1", tag=0)

        # Add order
        order_data = {"order_id": "o1", "amount": 100}
        result = func.execute(order_data, key="u1", tag=1)

        assert len(result) == 1
        joined = result[0]
        assert "user_id" in joined or "name" in joined
        assert "order_id" in joined or "amount" in joined

    def test_join_when_order_exists(self):
        """Test join when order already exists"""
        func = UserOrderInnerJoin()

        # Add order first
        order_data = {"order_id": "o2", "amount": 200}
        func.execute(order_data, key="u2", tag=1)

        # Add user
        user_data = {"user_id": "u2", "name": "Bob"}
        result = func.execute(user_data, key="u2", tag=0)

        assert len(result) == 1

    def test_multiple_orders_for_same_user(self):
        """Test multiple orders for the same user"""
        func = UserOrderInnerJoin()

        # Add multiple orders first
        func.execute({"order_id": "o1", "amount": 100}, key="u1", tag=1)
        func.execute({"order_id": "o2", "amount": 200}, key="u1", tag=1)

        # Add user - should join with all cached orders
        result = func.execute({"user_id": "u1", "name": "Alice"}, key="u1", tag=0)

        assert len(result) == 2

    def test_inner_join_clears_matched_orders(self):
        """Test that matched orders are cleared (inner join behavior)"""
        func = UserOrderInnerJoin()

        # Add orders
        func.execute({"order_id": "o1"}, key="u1", tag=1)
        assert "u1" in func.order_cache

        # Add user - should trigger join and clear orders
        func.execute({"user_id": "u1", "name": "Alice"}, key="u1", tag=0)

        # Orders should be cleared after join
        assert "u1" not in func.order_cache

    def test_different_users(self):
        """Test joins for different users"""
        func = UserOrderInnerJoin()

        # User 1
        func.execute({"user_id": "u1", "name": "Alice"}, key="u1", tag=0)
        result1 = func.execute({"order_id": "o1"}, key="u1", tag=1)

        # User 2
        func.execute({"user_id": "u2", "name": "Bob"}, key="u2", tag=0)
        result2 = func.execute({"order_id": "o2"}, key="u2", tag=1)

        assert len(result1) == 1
        assert len(result2) == 1

    def test_no_cross_user_joins(self):
        """Test that data doesn't join across different users"""
        func = UserOrderInnerJoin()

        func.execute({"user_id": "u1", "name": "Alice"}, key="u1", tag=0)
        result = func.execute({"order_id": "o1"}, key="u2", tag=1)  # Different key

        assert len(result) == 0


class TestJoinFunctionAdvanced:
    """Advanced tests for join functionality"""

    def test_left_outer_join_concept(self):
        """Test concept of left outer join (emit even without right match)"""

        class LeftOuterJoin(BaseJoinFunction):
            def __init__(self):
                super().__init__()
                self.left_data = {}
                self.right_data = {}

            def execute(self, payload, key, tag):
                results = []

                if tag == 0:  # Left
                    self.left_data[key] = payload
                    # Always emit, even if no right match
                    right = self.right_data.get(key, None)
                    results.append({"left": payload, "right": right, "key": key})

                elif tag == 1:  # Right
                    self.right_data[key] = payload
                    # Update if left exists
                    if key in self.left_data:
                        results.append({"left": self.left_data[key], "right": payload, "key": key})

                return results

        func = LeftOuterJoin()

        # Left arrives without right match
        result = func.execute({"name": "Alice"}, key="u1", tag=0)
        assert len(result) == 1
        assert result[0]["left"] == {"name": "Alice"}
        assert result[0]["right"] is None

    def test_windowed_join_concept(self):
        """Test concept of time-windowed join"""

        class WindowedJoin(BaseJoinFunction):
            def __init__(self, window_size=2):
                super().__init__()
                self.window_size = window_size
                self.left_window = {}
                self.right_window = {}

            def execute(self, payload, key, tag):
                results = []

                if tag == 0:
                    # Add to left window
                    if key not in self.left_window:
                        self.left_window[key] = []
                    self.left_window[key].append(payload)

                    # Keep only recent items
                    if len(self.left_window[key]) > self.window_size:
                        self.left_window[key].pop(0)

                    # Join with right window
                    if key in self.right_window:
                        for right_item in self.right_window[key]:
                            results.append({"left": payload, "right": right_item})

                elif tag == 1:
                    # Similar for right
                    if key not in self.right_window:
                        self.right_window[key] = []
                    self.right_window[key].append(payload)

                    if len(self.right_window[key]) > self.window_size:
                        self.right_window[key].pop(0)

                    if key in self.left_window:
                        for left_item in self.left_window[key]:
                            results.append({"left": left_item, "right": payload})

                return results

        func = WindowedJoin(window_size=2)

        # Add items to window
        func.execute({"id": 1}, key="k1", tag=0)
        func.execute({"id": 2}, key="k1", tag=0)
        func.execute({"id": 3}, key="k1", tag=0)  # This evicts id=1

        # Window should only contain id=2 and id=3
        assert len(func.left_window["k1"]) == 2
        assert func.left_window["k1"][0]["id"] == 2
        assert func.left_window["k1"][1]["id"] == 3

    def test_stateful_join_accumulation(self):
        """Test that join function maintains state correctly"""
        func = SimpleJoinFunction()

        # Accumulate state
        for i in range(5):
            func.execute({"value": i}, key=f"key_{i}", tag=0)

        assert len(func.left_data) == 5

        # Join some of them
        result = func.execute({"other": "data"}, key="key_2", tag=1)
        assert len(result) == 1
        assert result[0]["left"]["value"] == 2
