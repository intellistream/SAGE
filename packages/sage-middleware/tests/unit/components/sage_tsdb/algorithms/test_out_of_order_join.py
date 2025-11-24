"""
Tests for OutOfOrderStreamJoin Algorithm

Comprehensive test coverage for out-of-order stream join functionality.
"""

import pytest

from sage.middleware.components.sage_tsdb.python.algorithms.out_of_order_join import (
    JoinConfig,
    OutOfOrderStreamJoin,
    StreamBuffer,
)
from sage.middleware.components.sage_tsdb.python.sage_tsdb import TimeSeriesData


@pytest.fixture
def sample_left_data():
    """Sample left stream data"""
    return [
        TimeSeriesData(timestamp=1000, value=10.0, tags={"key": "A"}),
        TimeSeriesData(timestamp=2000, value=20.0, tags={"key": "B"}),
        TimeSeriesData(timestamp=3000, value=30.0, tags={"key": "A"}),
    ]


@pytest.fixture
def sample_right_data():
    """Sample right stream data"""
    return [
        TimeSeriesData(timestamp=1500, value=15.0, tags={"key": "A"}),
        TimeSeriesData(timestamp=2500, value=25.0, tags={"key": "B"}),
        TimeSeriesData(timestamp=3500, value=35.0, tags={"key": "C"}),
    ]


class TestStreamBuffer:
    """Test StreamBuffer functionality"""

    def test_buffer_initialization(self):
        """Test buffer initialization"""
        buffer = StreamBuffer(max_delay=5000)
        assert buffer.max_delay == 5000
        assert buffer.buffer == []
        assert buffer.watermark == 0

    def test_add_single_data(self):
        """Test adding single data point"""
        buffer = StreamBuffer(max_delay=1000)
        data = TimeSeriesData(timestamp=5000, value=10.0)

        buffer.add(data)

        assert buffer.size() == 1
        assert buffer.watermark == 4000  # 5000 - 1000

    def test_add_batch(self):
        """Test adding batch of data"""
        buffer = StreamBuffer(max_delay=1000)
        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
            TimeSeriesData(timestamp=3000, value=30.0),
        ]

        buffer.add_batch(data)

        assert buffer.size() == 3
        assert buffer.watermark == 2000  # 3000 - 1000

    def test_buffer_sorts_data(self):
        """Test that buffer sorts data by timestamp"""
        buffer = StreamBuffer(max_delay=1000)
        # Add out of order
        buffer.add(TimeSeriesData(timestamp=3000, value=30.0))
        buffer.add(TimeSeriesData(timestamp=1000, value=10.0))
        buffer.add(TimeSeriesData(timestamp=2000, value=20.0))

        # Buffer should be sorted
        assert buffer.buffer[0].timestamp == 1000
        assert buffer.buffer[1].timestamp == 2000
        assert buffer.buffer[2].timestamp == 3000

    def test_get_ready_data_empty_buffer(self):
        """Test getting ready data from empty buffer"""
        buffer = StreamBuffer(max_delay=1000)
        ready = buffer.get_ready_data()

        assert ready == []

    def test_get_ready_data_nothing_ready(self):
        """Test get_ready_data when nothing is ready"""
        buffer = StreamBuffer(max_delay=1000)
        buffer.add(TimeSeriesData(timestamp=5000, value=10.0))

        # Watermark is 4000, data at 5000 is not ready
        ready = buffer.get_ready_data()

        assert ready == []
        assert buffer.size() == 1

    def test_get_ready_data_some_ready(self):
        """Test get_ready_data when some data is ready"""
        buffer = StreamBuffer(max_delay=1000)
        buffer.add_batch(
            [
                TimeSeriesData(timestamp=1000, value=10.0),
                TimeSeriesData(timestamp=2000, value=20.0),
                TimeSeriesData(timestamp=5000, value=50.0),
            ]
        )

        # Watermark is 4000 (5000-1000)
        ready = buffer.get_ready_data()

        assert len(ready) == 2
        assert ready[0].timestamp == 1000
        assert ready[1].timestamp == 2000
        assert buffer.size() == 1  # Only one left in buffer

    def test_watermark_update(self):
        """Test watermark updates correctly"""
        buffer = StreamBuffer(max_delay=2000)

        buffer.add(TimeSeriesData(timestamp=5000, value=10.0))
        assert buffer.watermark == 3000

        buffer.add(TimeSeriesData(timestamp=8000, value=20.0))
        assert buffer.watermark == 6000

    def test_buffer_size(self):
        """Test buffer size tracking"""
        buffer = StreamBuffer(max_delay=1000)

        assert buffer.size() == 0

        buffer.add(TimeSeriesData(timestamp=1000, value=10.0))
        assert buffer.size() == 1

        buffer.add_batch(
            [
                TimeSeriesData(timestamp=2000, value=20.0),
                TimeSeriesData(timestamp=3000, value=30.0),
            ]
        )
        assert buffer.size() == 3


class TestOutOfOrderStreamJoin:
    """Test OutOfOrderStreamJoin algorithm"""

    def test_initialization_default_config(self):
        """Test initialization with default config"""
        join = OutOfOrderStreamJoin()

        assert join.window_size == 10000
        assert join.max_delay == 5000
        assert join.join_key is None
        assert join.join_predicate is None

    def test_initialization_custom_config(self):
        """Test initialization with custom config"""
        config = {
            "window_size": 20000,
            "max_delay": 10000,
            "join_key": "sensor_id",
        }
        join = OutOfOrderStreamJoin(config)

        assert join.window_size == 20000
        assert join.max_delay == 10000
        assert join.join_key == "sensor_id"

    def test_add_left_stream(self, sample_left_data):
        """Test adding data to left stream"""
        join = OutOfOrderStreamJoin()
        join.add_left_stream(sample_left_data)

        assert join.left_buffer.size() == 3

    def test_add_right_stream(self, sample_right_data):
        """Test adding data to right stream"""
        join = OutOfOrderStreamJoin()
        join.add_right_stream(sample_right_data)

        assert join.right_buffer.size() == 3

    def test_process_with_streams(self, sample_left_data, sample_right_data):
        """Test process with left and right streams"""
        config = {"window_size": 2000, "max_delay": 1000}
        join = OutOfOrderStreamJoin(config)

        result = join.process(left_stream=sample_left_data, right_stream=sample_right_data)

        # Result should be a list of tuples
        assert isinstance(result, list)
        assert len(result) > 0

    def test_nested_loop_join(self):
        """Test nested loop join without join key"""
        join = OutOfOrderStreamJoin({"window_size": 1000, "max_delay": 500})

        left = [TimeSeriesData(timestamp=1000, value=10.0)]
        right = [TimeSeriesData(timestamp=1500, value=15.0)]

        result = join._nested_loop_join(left, right)

        # Should join because within window (|1000-1500| = 500 <= 1000)
        assert len(result) == 1
        assert result[0][0].timestamp == 1000
        assert result[0][1].timestamp == 1500

    def test_nested_loop_join_outside_window(self):
        """Test nested loop join with data outside window"""
        join = OutOfOrderStreamJoin({"window_size": 200, "max_delay": 100})

        left = [TimeSeriesData(timestamp=1000, value=10.0)]
        right = [TimeSeriesData(timestamp=2000, value=20.0)]

        result = join._nested_loop_join(left, right)

        # Should not join (|1000-2000| = 1000 > 200)
        assert len(result) == 0

    def test_hash_join_with_key(self):
        """Test hash join with join key"""
        config = {"window_size": 2000, "max_delay": 1000, "join_key": "sensor"}
        join = OutOfOrderStreamJoin(config)

        left = [
            TimeSeriesData(timestamp=1000, value=10.0, tags={"sensor": "A"}),
            TimeSeriesData(timestamp=2000, value=20.0, tags={"sensor": "B"}),
        ]
        right = [
            TimeSeriesData(timestamp=1500, value=15.0, tags={"sensor": "A"}),
            TimeSeriesData(timestamp=2500, value=25.0, tags={"sensor": "C"}),
        ]

        result = join._hash_join(left, right)

        # Should only join sensor A (matching key and within window)
        assert len(result) == 1
        assert result[0][0].tags["sensor"] == "A"
        assert result[0][1].tags["sensor"] == "A"

    def test_hash_join_no_matching_keys(self):
        """Test hash join with no matching keys"""
        config = {"window_size": 2000, "max_delay": 1000, "join_key": "sensor"}
        join = OutOfOrderStreamJoin(config)

        left = [TimeSeriesData(timestamp=1000, value=10.0, tags={"sensor": "A"})]
        right = [TimeSeriesData(timestamp=1500, value=15.0, tags={"sensor": "B"})]

        result = join._hash_join(left, right)

        assert len(result) == 0

    def test_join_with_custom_predicate(self):
        """Test join with custom predicate function"""

        def custom_pred(left, right):
            return left.value < right.value

        config = {
            "window_size": 2000,
            "max_delay": 1000,
            "join_predicate": custom_pred,
        }
        join = OutOfOrderStreamJoin(config)

        left = [TimeSeriesData(timestamp=1000, value=10.0)]
        right = [
            TimeSeriesData(timestamp=1500, value=15.0),  # 10 < 15, should join
            TimeSeriesData(timestamp=1600, value=5.0),  # 10 < 5 is False
        ]

        result = join._nested_loop_join(left, right)

        # Only first pair should match predicate
        assert len(result) == 1
        assert result[0][1].value == 15.0

    def test_stats_tracking(self):
        """Test statistics tracking"""
        config = {"window_size": 2000, "max_delay": 1000}
        join = OutOfOrderStreamJoin(config)

        left = [TimeSeriesData(timestamp=1000, value=10.0)]
        right = [TimeSeriesData(timestamp=1500, value=15.0)]

        join.process(left_stream=left, right_stream=right)

        stats = join.get_stats()
        assert "total_joined" in stats
        assert "left_buffer_size" in stats
        assert "right_buffer_size" in stats
        assert "left_watermark" in stats
        assert "right_watermark" in stats

    def test_reset(self):
        """Test reset functionality"""
        join = OutOfOrderStreamJoin()

        # Add some data
        join.add_left_stream([TimeSeriesData(timestamp=1000, value=10.0)])
        join.add_right_stream([TimeSeriesData(timestamp=1500, value=15.0)])
        join.stats["total_joined"] = 5

        # Reset
        join.reset()

        assert join.left_buffer.size() == 0
        assert join.right_buffer.size() == 0
        assert join.stats["total_joined"] == 0

    def test_multiple_joins_same_key(self):
        """Test multiple joins with same key"""
        config = {"window_size": 3000, "max_delay": 1000, "join_key": "id"}
        join = OutOfOrderStreamJoin(config)

        left = [
            TimeSeriesData(timestamp=1000, value=10.0, tags={"id": "X"}),
            TimeSeriesData(timestamp=2000, value=20.0, tags={"id": "X"}),
        ]
        right = [TimeSeriesData(timestamp=1500, value=15.0, tags={"id": "X"})]

        result = join._hash_join(left, right)

        # Both left entries should join with the right entry
        assert len(result) == 2

    def test_empty_streams(self):
        """Test processing with empty streams"""
        join = OutOfOrderStreamJoin()

        result = join.process(left_stream=[], right_stream=[])

        assert result == []

    def test_one_stream_empty(self):
        """Test processing with one empty stream"""
        join = OutOfOrderStreamJoin()

        left = [TimeSeriesData(timestamp=1000, value=10.0)]
        result = join.process(left_stream=left, right_stream=[])

        # No joins possible
        assert result == []


class TestJoinConfig:
    """Test JoinConfig dataclass"""

    def test_join_config_creation(self):
        """Test JoinConfig creation"""
        config = JoinConfig(window_size=10000, max_delay=5000)

        assert config.window_size == 10000
        assert config.max_delay == 5000
        assert config.join_key is None
        assert config.join_predicate is None

    def test_join_config_with_key(self):
        """Test JoinConfig with join key"""
        config = JoinConfig(window_size=10000, max_delay=5000, join_key="sensor_id")

        assert config.join_key == "sensor_id"

    def test_join_config_with_predicate(self):
        """Test JoinConfig with custom predicate"""

        def pred(left, right):
            return True

        config = JoinConfig(window_size=10000, max_delay=5000, join_predicate=pred)

        assert config.join_predicate is pred


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_window_size(self):
        """Test join with zero window size"""
        join = OutOfOrderStreamJoin({"window_size": 0, "max_delay": 1000})

        left = [TimeSeriesData(timestamp=1000, value=10.0)]
        right = [TimeSeriesData(timestamp=1000, value=15.0)]

        result = join._nested_loop_join(left, right)

        # Should join only exact timestamp matches
        assert len(result) == 1

    def test_very_large_window(self):
        """Test join with very large window"""
        join = OutOfOrderStreamJoin({"window_size": 1000000, "max_delay": 1000})

        left = [TimeSeriesData(timestamp=1000, value=10.0)]
        right = [TimeSeriesData(timestamp=500000, value=15.0)]

        result = join._nested_loop_join(left, right)

        # Should join even with large time difference
        assert len(result) == 1

    def test_zero_max_delay(self):
        """Test buffer with zero max delay"""
        buffer = StreamBuffer(max_delay=0)
        buffer.add(TimeSeriesData(timestamp=1000, value=10.0))

        assert buffer.watermark == 1000
        ready = buffer.get_ready_data()
        assert len(ready) == 1

    def test_many_to_many_join(self):
        """Test many-to-many join scenario"""
        config = {"window_size": 5000, "max_delay": 1000, "join_key": "group"}
        join = OutOfOrderStreamJoin(config)

        left = [
            TimeSeriesData(timestamp=1000, value=1.0, tags={"group": "A"}),
            TimeSeriesData(timestamp=2000, value=2.0, tags={"group": "A"}),
            TimeSeriesData(timestamp=3000, value=3.0, tags={"group": "A"}),
        ]
        right = [
            TimeSeriesData(timestamp=1500, value=1.5, tags={"group": "A"}),
            TimeSeriesData(timestamp=2500, value=2.5, tags={"group": "A"}),
        ]

        result = join._hash_join(left, right)

        # Each left should join with each right (within window)
        # Expected: all combinations within window
        assert len(result) >= 4  # At least some combinations

    def test_out_of_order_arrival(self):
        """Test handling of out-of-order data arrival"""
        buffer = StreamBuffer(max_delay=2000)

        # Add data out of order
        buffer.add(TimeSeriesData(timestamp=5000, value=50.0))
        buffer.add(TimeSeriesData(timestamp=1000, value=10.0))
        buffer.add(TimeSeriesData(timestamp=3000, value=30.0))

        # Buffer should sort and handle correctly
        assert buffer.buffer[0].timestamp == 1000
        assert buffer.watermark == 3000  # 5000 - 2000

    def test_duplicate_timestamps(self):
        """Test handling of duplicate timestamps"""
        join = OutOfOrderStreamJoin({"window_size": 1000, "max_delay": 500})

        left = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=1000, value=11.0),
        ]
        right = [TimeSeriesData(timestamp=1000, value=15.0)]

        result = join._nested_loop_join(left, right)

        # Both left entries should join
        assert len(result) == 2
