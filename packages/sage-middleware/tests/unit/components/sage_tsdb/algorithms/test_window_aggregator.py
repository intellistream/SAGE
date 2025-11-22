"""
Tests for WindowAggregator Algorithm

Comprehensive test coverage for window-based aggregation functionality.
"""

import pytest

from sage.middleware.components.sage_tsdb.python.algorithms.window_aggregator import (
    WindowAggregator,
    WindowConfig,
    WindowType,
)
from sage.middleware.components.sage_tsdb.python.sage_tsdb import (
    AggregationType,
    TimeSeriesData,
)


@pytest.fixture
def sample_data():
    """Sample time series data"""
    return [
        TimeSeriesData(timestamp=1000, value=10.0, tags={"sensor": "A"}),
        TimeSeriesData(timestamp=2000, value=20.0, tags={"sensor": "A"}),
        TimeSeriesData(timestamp=3000, value=30.0, tags={"sensor": "A"}),
        TimeSeriesData(timestamp=4000, value=40.0, tags={"sensor": "A"}),
        TimeSeriesData(timestamp=5000, value=50.0, tags={"sensor": "A"}),
    ]


class TestWindowAggregator:
    """Test WindowAggregator initialization and basic functionality"""

    def test_initialization_default_config(self):
        """Test initialization with default config"""
        agg = WindowAggregator()

        assert agg.window_type == WindowType.TUMBLING
        assert agg.window_size == 60000
        assert agg.aggregation == AggregationType.AVG

    def test_initialization_tumbling_window(self):
        """Test initialization with tumbling window config"""
        config = {
            "window_type": "tumbling",
            "window_size": 10000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        assert agg.window_type == WindowType.TUMBLING
        assert agg.window_size == 10000
        assert agg.aggregation == AggregationType.SUM

    def test_initialization_sliding_window(self):
        """Test initialization with sliding window config"""
        config = {
            "window_type": "sliding",
            "window_size": 10000,
            "slide_interval": 5000,
            "aggregation": "avg",
        }
        agg = WindowAggregator(config)

        assert agg.window_type == WindowType.SLIDING
        assert agg.slide_interval == 5000

    def test_initialization_session_window(self):
        """Test initialization with session window config"""
        config = {
            "window_type": "session",
            "window_size": 10000,
            "session_gap": 3000,
            "aggregation": "max",
        }
        agg = WindowAggregator(config)

        assert agg.window_type == WindowType.SESSION
        assert agg.session_gap == 3000
        assert agg.aggregation == AggregationType.MAX


class TestTumblingWindow:
    """Test tumbling window aggregation"""

    def test_tumbling_window_basic(self, sample_data):
        """Test basic tumbling window aggregation"""
        config = {
            "window_type": "tumbling",
            "window_size": 2000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        result = agg.process(sample_data)

        # Data spans 1000-5000, window size 2000
        # Windows: [0-2000), [2000-4000), [4000-6000)
        assert len(result) >= 2
        assert all(isinstance(r, TimeSeriesData) for r in result)

    def test_tumbling_window_sum(self):
        """Test tumbling window with SUM aggregation"""
        config = {
            "window_type": "tumbling",
            "window_size": 3000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
            TimeSeriesData(timestamp=4000, value=40.0),
        ]

        result = agg.process(data)

        # First window [0-3000): 10 + 20 = 30
        # Second window [3000-6000): 40
        assert len(result) == 2
        assert result[0].value == 30.0
        assert result[1].value == 40.0

    def test_tumbling_window_avg(self):
        """Test tumbling window with AVG aggregation"""
        config = {
            "window_type": "tumbling",
            "window_size": 2000,
            "aggregation": "avg",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=1500, value=20.0),
            TimeSeriesData(timestamp=3000, value=30.0),
        ]

        result = agg.process(data)

        # First window [0-2000): avg(10, 20) = 15
        # Second window [2000-4000): avg(30) = 30
        assert len(result) == 2
        assert result[0].value == 15.0
        assert result[1].value == 30.0

    def test_tumbling_window_min_max(self):
        """Test tumbling window with MIN/MAX aggregation"""
        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=1500, value=30.0),
            TimeSeriesData(timestamp=2000, value=20.0),
        ]

        # Test MIN
        agg_min = WindowAggregator(
            {"window_type": "tumbling", "window_size": 3000, "aggregation": "min"}
        )
        result_min = agg_min.process(data)
        assert result_min[0].value == 10.0

        # Test MAX
        agg_max = WindowAggregator(
            {"window_type": "tumbling", "window_size": 3000, "aggregation": "max"}
        )
        result_max = agg_max.process(data)
        assert result_max[0].value == 30.0

    def test_tumbling_window_count(self):
        """Test tumbling window with COUNT aggregation"""
        config = {
            "window_type": "tumbling",
            "window_size": 3000,
            "aggregation": "count",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
            TimeSeriesData(timestamp=4000, value=40.0),
            TimeSeriesData(timestamp=5000, value=50.0),
        ]

        result = agg.process(data)

        # First window [0-3000): count=2
        # Second window [3000-6000): count=2
        assert result[0].value == 2
        assert result[1].value == 2

    def test_tumbling_window_first_last(self):
        """Test tumbling window with FIRST/LAST aggregation"""
        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
            TimeSeriesData(timestamp=3000, value=30.0),
        ]

        # Test FIRST
        agg_first = WindowAggregator(
            {"window_type": "tumbling", "window_size": 4000, "aggregation": "first"}
        )
        result_first = agg_first.process(data)
        assert result_first[0].value == 10.0

        # Test LAST
        agg_last = WindowAggregator(
            {"window_type": "tumbling", "window_size": 4000, "aggregation": "last"}
        )
        result_last = agg_last.process(data)
        assert result_last[0].value == 30.0

    def test_tumbling_window_empty_data(self):
        """Test tumbling window with empty data"""
        agg = WindowAggregator({"window_type": "tumbling", "window_size": 1000})

        result = agg.process([])

        assert result == []

    def test_tumbling_window_preserves_tags(self):
        """Test that tumbling window preserves tags"""
        config = {
            "window_type": "tumbling",
            "window_size": 5000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0, tags={"sensor": "A", "location": "room1"}),
            TimeSeriesData(timestamp=2000, value=20.0, tags={"sensor": "A"}),
        ]

        result = agg.process(data)

        # Tags should be merged
        assert "sensor" in result[0].tags
        assert "location" in result[0].tags


class TestSlidingWindow:
    """Test sliding window aggregation"""

    def test_sliding_window_basic(self):
        """Test basic sliding window aggregation"""
        config = {
            "window_type": "sliding",
            "window_size": 3000,
            "slide_interval": 1000,
            "aggregation": "avg",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
            TimeSeriesData(timestamp=3000, value=30.0),
            TimeSeriesData(timestamp=4000, value=40.0),
        ]

        result = agg.process(data)

        # Sliding windows should create overlapping results
        assert len(result) >= 3

    def test_sliding_window_overlapping(self):
        """Test sliding window creates overlapping windows"""
        config = {
            "window_type": "sliding",
            "window_size": 2000,
            "slide_interval": 1000,
            "aggregation": "count",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=500, value=5.0),
            TimeSeriesData(timestamp=1500, value=15.0),
            TimeSeriesData(timestamp=2500, value=25.0),
        ]

        result = agg.process(data)

        # Windows: [0-2000), [1000-3000)
        # First window: 500, 1500 (count=2)
        # Second window: 1500, 2500 (count=2)
        assert len(result) >= 2

    def test_sliding_window_no_overlap(self):
        """Test sliding window with slide_interval = window_size (no overlap)"""
        config = {
            "window_type": "sliding",
            "window_size": 2000,
            "slide_interval": 2000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=3000, value=30.0),
        ]

        result = agg.process(data)

        # Should behave like tumbling window
        assert len(result) == 2

    def test_sliding_window_empty_windows(self):
        """Test sliding window with some empty windows"""
        config = {
            "window_type": "sliding",
            "window_size": 1000,
            "slide_interval": 1000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=5000, value=50.0),
        ]

        result = agg.process(data)

        # Some windows will be empty, only non-empty ones should appear
        assert all(r.fields["window_size"] > 0 for r in result)


class TestSessionWindow:
    """Test session window aggregation"""

    def test_session_window_basic(self):
        """Test basic session window aggregation"""
        config = {
            "window_type": "session",
            "session_gap": 2000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),  # Within gap
            TimeSeriesData(timestamp=5000, value=50.0),  # New session
        ]

        result = agg.process(data)

        # Should create 2 sessions
        assert len(result) == 2
        assert result[0].value == 30.0  # First session: 10 + 20
        assert result[1].value == 50.0  # Second session: 50

    def test_session_window_single_session(self):
        """Test session window with single session"""
        config = {
            "window_type": "session",
            "session_gap": 5000,
            "aggregation": "count",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=3000, value=30.0),
            TimeSeriesData(timestamp=5000, value=50.0),
        ]

        result = agg.process(data)

        # All within gap, should be one session
        assert len(result) == 1
        assert result[0].value == 3

    def test_session_window_multiple_sessions(self):
        """Test session window with multiple sessions"""
        config = {
            "window_type": "session",
            "session_gap": 1000,
            "aggregation": "avg",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=1500, value=20.0),  # Session 1
            TimeSeriesData(timestamp=5000, value=50.0),  # Session 2
            TimeSeriesData(timestamp=10000, value=100.0),  # Session 3
        ]

        result = agg.process(data)

        assert len(result) == 3

    def test_session_window_empty_data(self):
        """Test session window with empty data"""
        agg = WindowAggregator({"window_type": "session", "session_gap": 1000})

        result = agg.process([])

        assert result == []


class TestAggregationFunctions:
    """Test different aggregation functions"""

    def test_stddev_aggregation(self):
        """Test standard deviation aggregation"""
        config = {
            "window_type": "tumbling",
            "window_size": 5000,
            "aggregation": "stddev",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
            TimeSeriesData(timestamp=3000, value=30.0),
        ]

        result = agg.process(data)

        # Stddev should be calculated
        assert result[0].value > 0

    def test_aggregation_with_arrays(self):
        """Test aggregation with array values"""
        import numpy as np

        config = {
            "window_type": "tumbling",
            "window_size": 3000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=np.array([1.0, 2.0])),
            TimeSeriesData(timestamp=2000, value=np.array([3.0, 4.0])),
        ]

        result = agg.process(data)

        # Should flatten and sum: 1+2+3+4 = 10
        assert result[0].value == 10.0


class TestWindowAlignment:
    """Test window alignment and timestamp handling"""

    def test_align_to_window(self):
        """Test timestamp alignment to window boundary"""
        agg = WindowAggregator({"window_type": "tumbling", "window_size": 10000})

        # Test various timestamps
        assert agg._align_to_window(5000) == 0
        assert agg._align_to_window(15000) == 10000
        assert agg._align_to_window(25000) == 20000

    def test_window_key_generation(self):
        """Test window key generation"""
        agg = WindowAggregator({"window_type": "tumbling", "window_size": 10000})

        key1 = agg._get_window_key(5000, 0)
        key2 = agg._get_window_key(15000, 0)

        assert key1 == 0
        assert key2 == 10000

    def test_window_timestamp(self):
        """Test that aggregated points use window start timestamp"""
        config = {
            "window_type": "tumbling",
            "window_size": 10000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=5000, value=50.0),
        ]

        result = agg.process(data)

        # Window timestamp should be aligned
        assert result[0].timestamp == 0


class TestStatistics:
    """Test statistics tracking"""

    def test_stats_tracking(self):
        """Test statistics are tracked correctly"""
        config = {
            "window_type": "tumbling",
            "window_size": 2000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=3000, value=30.0),
        ]

        agg.process(data)

        stats = agg.get_stats()
        assert stats["windows_completed"] >= 1
        assert stats["data_points_processed"] == 2

    def test_reset_statistics(self):
        """Test reset clears statistics"""
        agg = WindowAggregator()

        data = [TimeSeriesData(timestamp=1000, value=10.0)]
        agg.process(data)

        # Reset
        agg.reset()

        stats = agg.get_stats()
        assert stats["windows_created"] == 0
        assert stats["windows_completed"] == 0
        assert stats["data_points_processed"] == 0


class TestWindowConfig:
    """Test WindowConfig dataclass"""

    def test_window_config_creation(self):
        """Test WindowConfig creation"""
        config = WindowConfig(
            window_type=WindowType.TUMBLING, window_size=10000, aggregation=AggregationType.SUM
        )

        assert config.window_type == WindowType.TUMBLING
        assert config.window_size == 10000
        assert config.aggregation == AggregationType.SUM

    def test_window_config_with_slide(self):
        """Test WindowConfig with slide interval"""
        config = WindowConfig(
            window_type=WindowType.SLIDING,
            window_size=10000,
            slide_interval=5000,
        )

        assert config.slide_interval == 5000

    def test_window_config_with_session_gap(self):
        """Test WindowConfig with session gap"""
        config = WindowConfig(
            window_type=WindowType.SESSION,
            window_size=10000,
            session_gap=3000,
        )

        assert config.session_gap == 3000


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_single_data_point(self):
        """Test processing single data point"""
        agg = WindowAggregator({"window_type": "tumbling", "window_size": 1000})

        data = [TimeSeriesData(timestamp=1000, value=10.0)]
        result = agg.process(data)

        assert len(result) == 1
        assert result[0].value == 10.0

    def test_very_small_window(self):
        """Test with very small window size"""
        config = {
            "window_type": "tumbling",
            "window_size": 1,
            "aggregation": "count",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1, value=1.0),
            TimeSeriesData(timestamp=2, value=2.0),
        ]

        result = agg.process(data)

        # Each point in its own window
        assert len(result) >= 2

    def test_very_large_window(self):
        """Test with very large window size"""
        config = {
            "window_type": "tumbling",
            "window_size": 1000000,
            "aggregation": "sum",
        }
        agg = WindowAggregator(config)

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=50000, value=50.0),
        ]

        result = agg.process(data)

        # All data in one window
        assert len(result) == 1
        assert result[0].value == 60.0

    def test_zero_values(self):
        """Test aggregation with zero values"""
        agg = WindowAggregator(
            {"window_type": "tumbling", "window_size": 2000, "aggregation": "sum"}
        )

        data = [
            TimeSeriesData(timestamp=1000, value=0.0),
            TimeSeriesData(timestamp=1500, value=0.0),
        ]

        result = agg.process(data)

        assert result[0].value == 0.0

    def test_negative_values(self):
        """Test aggregation with negative values"""
        agg = WindowAggregator(
            {"window_type": "tumbling", "window_size": 3000, "aggregation": "sum"}
        )

        data = [
            TimeSeriesData(timestamp=1000, value=-10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
        ]

        result = agg.process(data)

        assert result[0].value == 10.0

    def test_window_fields_metadata(self):
        """Test that window results include metadata fields"""
        agg = WindowAggregator({"window_type": "tumbling", "window_size": 3000})

        data = [
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
        ]

        result = agg.process(data)

        # Check metadata fields
        assert "window_size" in result[0].fields
        assert "aggregation" in result[0].fields
        assert result[0].fields["window_size"] == 2

    def test_unsorted_data_gets_sorted(self):
        """Test that unsorted data gets sorted before processing"""
        config = {
            "window_type": "tumbling",
            "window_size": 3000,
            "aggregation": "first",
        }
        agg = WindowAggregator(config)

        # Provide unsorted data
        data = [
            TimeSeriesData(timestamp=3000, value=30.0),
            TimeSeriesData(timestamp=1000, value=10.0),
            TimeSeriesData(timestamp=2000, value=20.0),
        ]

        result = agg.process(data)

        # First value should be 10.0 (after sorting)
        assert result[0].value == 10.0
