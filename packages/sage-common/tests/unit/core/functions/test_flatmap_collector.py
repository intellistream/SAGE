"""
Tests for FlatMap Collector class

Tests cover:
- Collector initialization
- Data collection (collect method)
- Getting collected data
- Getting count
- Clearing data
- Logger integration
"""

from unittest.mock import MagicMock

from sage.common.core.functions.flatmap_collector import Collector


class TestCollectorInitialization:
    """Test Collector initialization"""

    def test_collector_basic_initialization(self):
        """Test Collector initializes with empty data"""
        collector = Collector()
        assert collector._collected_data == []
        assert collector.logger is None

    def test_collector_with_logger(self):
        """Test Collector initialization with logger"""
        mock_logger = MagicMock()
        collector = Collector(logger=mock_logger)
        assert collector._collected_data == []
        assert collector.logger is mock_logger

    def test_collector_with_args(self):
        """Test Collector handles arbitrary args/kwargs"""
        collector = Collector("arg1", "arg2", key1="value1", key2="value2")
        assert collector._collected_data == []


class TestCollectorCollect:
    """Test Collector collect method"""

    def test_collect_single_item(self):
        """Test collecting single item"""
        collector = Collector()
        collector.collect("data1")
        assert len(collector._collected_data) == 1
        assert collector._collected_data[0] == "data1"

    def test_collect_multiple_items(self):
        """Test collecting multiple items"""
        collector = Collector()
        collector.collect("item1")
        collector.collect("item2")
        collector.collect("item3")

        assert len(collector._collected_data) == 3
        assert collector._collected_data == ["item1", "item2", "item3"]

    def test_collect_different_types(self):
        """Test collecting different data types"""
        collector = Collector()
        collector.collect(42)
        collector.collect("string")
        collector.collect({"key": "value"})
        collector.collect([1, 2, 3])
        collector.collect(None)

        assert len(collector._collected_data) == 5
        assert 42 in collector._collected_data
        assert "string" in collector._collected_data

    def test_collect_with_logger(self):
        """Test collect logs debug message"""
        mock_logger = MagicMock()
        collector = Collector(logger=mock_logger)

        collector.collect("test_data")

        mock_logger.debug.assert_called_once()
        assert "test_data" in str(mock_logger.debug.call_args)

    def test_collect_without_logger(self):
        """Test collect works without logger"""
        collector = Collector()
        collector.collect("data")
        # Should not raise any errors
        assert collector._collected_data == ["data"]


class TestCollectorGetData:
    """Test getting collected data"""

    def test_get_collected_data_empty(self):
        """Test getting data when empty"""
        collector = Collector()
        data = collector.get_collected_data()
        assert data == []

    def test_get_collected_data_returns_copy(self):
        """Test get_collected_data returns a copy"""
        collector = Collector()
        collector.collect("item1")
        collector.collect("item2")

        data = collector.get_collected_data()
        data.append("item3")  # Modify returned list

        # Original should be unchanged
        assert len(collector._collected_data) == 2
        assert "item3" not in collector._collected_data

    def test_get_collected_data_with_items(self):
        """Test getting data with items"""
        collector = Collector()
        items = ["a", "b", "c", "d", "e"]
        for item in items:
            collector.collect(item)

        data = collector.get_collected_data()
        assert data == items

    def test_get_collected_count_empty(self):
        """Test count when empty"""
        collector = Collector()
        assert collector.get_collected_count() == 0

    def test_get_collected_count_with_items(self):
        """Test count with items"""
        collector = Collector()
        for i in range(10):
            collector.collect(i)

        assert collector.get_collected_count() == 10

    def test_get_collected_count_after_multiple_operations(self):
        """Test count changes with operations"""
        collector = Collector()
        assert collector.get_collected_count() == 0

        collector.collect("a")
        assert collector.get_collected_count() == 1

        collector.collect("b")
        collector.collect("c")
        assert collector.get_collected_count() == 3


class TestCollectorClear:
    """Test Collector clear method"""

    def test_clear_empty_collector(self):
        """Test clearing empty collector"""
        collector = Collector()
        collector.clear()
        assert collector._collected_data == []
        assert collector.get_collected_count() == 0

    def test_clear_with_data(self):
        """Test clearing collector with data"""
        collector = Collector()
        collector.collect("item1")
        collector.collect("item2")
        collector.collect("item3")

        assert collector.get_collected_count() == 3

        collector.clear()
        assert collector._collected_data == []
        assert collector.get_collected_count() == 0

    def test_clear_with_logger(self):
        """Test clear logs debug message"""
        mock_logger = MagicMock()
        collector = Collector(logger=mock_logger)

        collector.collect("item1")
        collector.collect("item2")

        collector.clear()

        # Should have logged collection (2 times) and clear (1 time)
        assert mock_logger.debug.call_count == 3
        # Last call should be about clearing
        last_call = str(mock_logger.debug.call_args_list[-1])
        assert "Cleared" in last_call or "cleared" in last_call.lower()

    def test_clear_empty_with_logger(self):
        """Test clearing empty collector doesn't log"""
        mock_logger = MagicMock()
        collector = Collector(logger=mock_logger)

        collector.clear()

        # Should not log when clearing empty collector
        mock_logger.debug.assert_not_called()

    def test_clear_multiple_times(self):
        """Test clearing multiple times"""
        collector = Collector()
        for i in range(5):
            collector.collect(i)

        collector.clear()
        assert collector.get_collected_count() == 0

        collector.clear()  # Clear again
        assert collector.get_collected_count() == 0


class TestCollectorIntegration:
    """Integration tests for Collector"""

    def test_collector_full_lifecycle(self):
        """Test complete lifecycle: collect -> get -> clear -> collect"""
        collector = Collector()

        # Phase 1: Collect
        collector.collect("a")
        collector.collect("b")
        assert collector.get_collected_count() == 2

        # Phase 2: Get data
        data = collector.get_collected_data()
        assert data == ["a", "b"]

        # Phase 3: Clear
        collector.clear()
        assert collector.get_collected_count() == 0

        # Phase 4: Collect again
        collector.collect("c")
        collector.collect("d")
        assert collector.get_collected_count() == 2
        assert collector.get_collected_data() == ["c", "d"]

    def test_collector_with_flatmap_pattern(self):
        """Test Collector in FlatMap-like usage pattern"""
        collector = Collector()

        # Simulate FlatMap operation: one input -> multiple outputs
        input_data = "hello,world,test"
        words = input_data.split(",")
        for word in words:
            collector.collect(word)

        assert collector.get_collected_count() == 3
        assert collector.get_collected_data() == ["hello", "world", "test"]

    def test_collector_batch_processing(self):
        """Test Collector for batch processing"""
        collector = Collector()
        batch_size = 5

        # Collect batch
        for i in range(batch_size):
            collector.collect(i)

        assert collector.get_collected_count() == batch_size

        # Process batch
        batch = collector.get_collected_data()
        assert len(batch) == batch_size

        # Clear for next batch
        collector.clear()
        assert collector.get_collected_count() == 0

    def test_collector_with_complex_data(self):
        """Test Collector with complex nested data"""
        collector = Collector()

        complex_items = [
            {"id": 1, "data": [1, 2, 3]},
            {"id": 2, "data": [4, 5, 6]},
            {"id": 3, "data": {"nested": "value"}},
        ]

        for item in complex_items:
            collector.collect(item)

        assert collector.get_collected_count() == 3
        retrieved = collector.get_collected_data()
        assert retrieved == complex_items
