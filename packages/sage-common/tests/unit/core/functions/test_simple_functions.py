"""
Comprehensive tests for simple function classes

Tests cover:
- MapFunction: one-to-one data transformation
- FilterFunction: boolean predicate filtering
- SinkFunction: terminal operations with side effects
- SourceFunction: data generation
- FlatMapFunction: one-to-many transformations
- BatchFunction: data batching
"""

from unittest.mock import MagicMock

import pytest

from sage.common.core.functions.batch_function import BatchFunction
from sage.common.core.functions.filter_function import FilterFunction
from sage.common.core.functions.flatmap_function import FlatMapFunction
from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction


# Concrete implementations for testing
class ConcreteMapFunction(MapFunction):
    """Concrete MapFunction for testing"""

    def execute(self, data):
        return data * 2


class ConcreteFilterFunction(FilterFunction):
    """Concrete FilterFunction for testing"""

    def execute(self, data):
        return data > 10


class ConcreteSinkFunction(SinkFunction):
    """Concrete SinkFunction for testing"""

    def __init__(self):
        super().__init__()
        self.received = []

    def execute(self, data):
        self.received.append(data)


class ConcreteSourceFunction(SourceFunction):
    """Concrete SourceFunction for testing"""

    def __init__(self):
        super().__init__()
        self.counter = 0

    def execute(self):
        self.counter += 1
        return self.counter


class ConcreteFlatMapFunction(FlatMapFunction):
    """Concrete FlatMapFunction for testing"""

    def execute(self, data):
        return [data, data * 2, data * 3]


class ConcreteBatchFunction(BatchFunction):
    """Concrete BatchFunction for testing"""

    def __init__(self, batch_size=3):
        super().__init__()
        self.batch_size = batch_size
        self.batch = []

    def execute(self, data):
        self.batch.append(data)
        if len(self.batch) >= self.batch_size:
            result = list(self.batch)
            self.batch = []
            return result
        return None


class TestMapFunction:
    """Test MapFunction"""

    def test_map_inheritance(self):
        """Test MapFunction inherits from BaseFunction"""
        from sage.common.core.functions.base_function import BaseFunction

        func = ConcreteMapFunction()
        assert isinstance(func, BaseFunction)
        assert isinstance(func, MapFunction)

    def test_map_execute_simple(self):
        """Test execute with simple data"""
        func = ConcreteMapFunction()
        result = func.execute(5)
        assert result == 10

    def test_map_execute_different_types(self):
        """Test execute with different data types"""

        class StringMapFunction(MapFunction):
            def execute(self, data):
                return data.upper()

        func = StringMapFunction()
        assert func.execute("hello") == "HELLO"

    def test_map_execute_dict(self):
        """Test execute with dictionary"""

        class DictMapFunction(MapFunction):
            def execute(self, data):
                return {"value": data["x"] * 2}

        func = DictMapFunction()
        assert func.execute({"x": 5}) == {"value": 10}

    def test_map_with_context(self):
        """Test MapFunction with context"""
        func = ConcreteMapFunction()
        mock_ctx = MagicMock()
        func.ctx = mock_ctx

        result = func.execute(3)
        assert result == 6
        assert func.ctx is mock_ctx


class TestFilterFunction:
    """Test FilterFunction"""

    def test_filter_inheritance(self):
        """Test FilterFunction inherits from BaseFunction"""
        from sage.common.core.functions.base_function import BaseFunction

        func = ConcreteFilterFunction()
        assert isinstance(func, BaseFunction)
        assert isinstance(func, FilterFunction)

    def test_filter_execute_true(self):
        """Test execute returns True for matching condition"""
        func = ConcreteFilterFunction()
        assert func.execute(15) is True
        assert func.execute(20) is True

    def test_filter_execute_false(self):
        """Test execute returns False for non-matching condition"""
        func = ConcreteFilterFunction()
        assert func.execute(5) is False
        assert func.execute(10) is False

    def test_filter_boolean_result(self):
        """Test execute always returns boolean"""

        class AlwaysTrueFilter(FilterFunction):
            def execute(self, data):
                return True

        func = AlwaysTrueFilter()
        assert func.execute("anything") is True

    def test_filter_with_complex_condition(self):
        """Test filter with complex condition"""

        class ComplexFilter(FilterFunction):
            def execute(self, data):
                return data.get("active", False) and data.get("score", 0) > 50

        func = ComplexFilter()
        assert func.execute({"active": True, "score": 60}) is True
        assert func.execute({"active": False, "score": 60}) is False
        assert func.execute({"active": True, "score": 30}) is False

    def test_filter_process_output_truthy(self):
        """Test _process_output converts truthy values to True"""
        func = ConcreteFilterFunction()
        assert func._process_output(1) is True
        assert func._process_output("non-empty") is True
        assert func._process_output([1, 2, 3]) is True
        assert func._process_output({"key": "value"}) is True

    def test_filter_process_output_falsy(self):
        """Test _process_output converts falsy values to False"""
        func = ConcreteFilterFunction()
        assert func._process_output(0) is False
        assert func._process_output("") is False
        assert func._process_output([]) is False
        assert func._process_output({}) is False
        assert func._process_output(None) is False


class TestSinkFunction:
    """Test SinkFunction"""

    def test_sink_inheritance(self):
        """Test SinkFunction inherits from BaseFunction"""
        from sage.common.core.functions.base_function import BaseFunction

        func = ConcreteSinkFunction()
        assert isinstance(func, BaseFunction)
        assert isinstance(func, SinkFunction)

    def test_sink_execute_void_return(self):
        """Test execute returns None"""
        func = ConcreteSinkFunction()
        result = func.execute("data")
        assert result is None

    def test_sink_side_effect(self):
        """Test sink performs side effect"""
        func = ConcreteSinkFunction()
        func.execute("item1")
        func.execute("item2")

        assert func.received == ["item1", "item2"]

    def test_sink_multiple_calls(self):
        """Test sink handles multiple calls"""
        func = ConcreteSinkFunction()
        for i in range(10):
            func.execute(i)

        assert len(func.received) == 10
        assert func.received[0] == 0
        assert func.received[9] == 9

    def test_sink_print_side_effect(self, capsys):
        """Test sink with print side effect"""

        class PrintSink(SinkFunction):
            def execute(self, data):
                print(f"Received: {data}")

        func = PrintSink()
        func.execute("test")

        captured = capsys.readouterr()
        assert "Received: test" in captured.out


class TestSourceFunction:
    """Test SourceFunction"""

    def test_source_inheritance(self):
        """Test SourceFunction inherits from BaseFunction"""
        from sage.common.core.functions.base_function import BaseFunction

        func = ConcreteSourceFunction()
        assert isinstance(func, BaseFunction)
        assert isinstance(func, SourceFunction)

    def test_source_execute_no_args(self):
        """Test execute takes no arguments"""
        func = ConcreteSourceFunction()
        result = func.execute()
        assert result == 1

    def test_source_sequential_execution(self):
        """Test source generates sequential data"""
        func = ConcreteSourceFunction()
        results = [func.execute() for _ in range(5)]
        assert results == [1, 2, 3, 4, 5]

    def test_source_constant_data(self):
        """Test source with constant data"""

        class ConstantSource(SourceFunction):
            def execute(self):
                return "constant_value"

        func = ConstantSource()
        assert func.execute() == "constant_value"
        assert func.execute() == "constant_value"

    def test_source_random_data(self):
        """Test source with random-like data"""
        import random

        class RandomSource(SourceFunction):
            def execute(self):
                return random.randint(1, 100)

        func = RandomSource()
        result1 = func.execute()
        result2 = func.execute()

        assert isinstance(result1, int)
        assert isinstance(result2, int)


class TestFlatMapFunction:
    """Test FlatMapFunction"""

    def test_flatmap_inheritance(self):
        """Test FlatMapFunction inherits from BaseFunction"""
        from sage.common.core.functions.base_function import BaseFunction

        func = ConcreteFlatMapFunction()
        assert isinstance(func, BaseFunction)
        assert isinstance(func, FlatMapFunction)

    def test_flatmap_execute_returns_list(self):
        """Test execute returns list"""
        func = ConcreteFlatMapFunction()
        result = func.execute(5)
        assert isinstance(result, list)
        assert result == [5, 10, 15]

    def test_flatmap_one_to_many(self):
        """Test flatmap produces multiple outputs"""
        func = ConcreteFlatMapFunction()
        result = func.execute(2)
        assert len(result) == 3
        assert result == [2, 4, 6]

    def test_flatmap_empty_list(self):
        """Test flatmap can return empty list"""

        class EmptyFlatMap(FlatMapFunction):
            def execute(self, data):
                return []

        func = EmptyFlatMap()
        assert func.execute("anything") == []

    def test_flatmap_string_split(self):
        """Test flatmap with string splitting"""

        class SplitFlatMap(FlatMapFunction):
            def execute(self, data):
                return data.split(",")

        func = SplitFlatMap()
        result = func.execute("a,b,c")
        assert result == ["a", "b", "c"]

    def test_flatmap_dict_expansion(self):
        """Test flatmap with dictionary expansion"""

        class DictExpandFlatMap(FlatMapFunction):
            def execute(self, data):
                return [{"key": k, "value": v} for k, v in data.items()]

        func = DictExpandFlatMap()
        result = func.execute({"a": 1, "b": 2})
        assert len(result) == 2
        assert {"key": "a", "value": 1} in result

    def test_flatmap_collector_initialization(self):
        """Test FlatMapFunction initializes with None collector"""
        func = ConcreteFlatMapFunction()
        assert func.out is None

    def test_flatmap_insert_collector(self):
        """Test inserting collector into FlatMapFunction"""
        from unittest.mock import PropertyMock, patch

        from sage.common.core.functions.flatmap_collector import Collector

        func = ConcreteFlatMapFunction()
        mock_collector = MagicMock(spec=Collector)
        mock_logger = MagicMock()

        # Mock logger property to avoid initialization issues
        with patch.object(
            type(func), "logger", new_callable=PropertyMock, return_value=mock_logger
        ):
            func.insert_collector(mock_collector)

        assert func.out is mock_collector

    def test_flatmap_collect_method(self):
        """Test collect method with collector"""
        from unittest.mock import PropertyMock, patch

        from sage.common.core.functions.flatmap_collector import Collector

        func = ConcreteFlatMapFunction()
        mock_collector = MagicMock(spec=Collector)
        mock_logger = MagicMock()

        with patch.object(
            type(func), "logger", new_callable=PropertyMock, return_value=mock_logger
        ):
            func.insert_collector(mock_collector)
            func.collect("test_data")

        mock_collector.collect.assert_called_once_with("test_data")

    def test_flatmap_collect_without_collector(self):
        """Test collect raises error without collector"""
        func = ConcreteFlatMapFunction()

        with pytest.raises(RuntimeError, match="Collector not initialized"):
            func.collect("test_data")

    def test_flatmap_with_collector_pattern(self):
        """Test FlatMapFunction using collector pattern"""
        from unittest.mock import PropertyMock, patch

        from sage.common.core.functions.flatmap_collector import Collector

        class CollectorBasedFlatMap(FlatMapFunction):
            def execute(self, data):
                for i in range(data):
                    self.collect(i * 2)
                return None

        func = CollectorBasedFlatMap()
        mock_collector = MagicMock(spec=Collector)
        mock_logger = MagicMock()

        with patch.object(
            type(func), "logger", new_callable=PropertyMock, return_value=mock_logger
        ):
            func.insert_collector(mock_collector)
            func.execute(3)

        assert mock_collector.collect.call_count == 3
        mock_collector.collect.assert_any_call(0)
        mock_collector.collect.assert_any_call(2)
        mock_collector.collect.assert_any_call(4)


class TestBatchFunction:
    """Test BatchFunction"""

    def test_batch_inheritance(self):
        """Test BatchFunction inherits from BaseFunction"""
        from sage.common.core.functions.base_function import BaseFunction

        func = ConcreteBatchFunction()
        assert isinstance(func, BaseFunction)
        assert isinstance(func, BatchFunction)

    def test_batch_accumulation(self):
        """Test batch accumulates data"""
        func = ConcreteBatchFunction(batch_size=3)

        result1 = func.execute(1)
        assert result1 is None  # Not enough for batch

        result2 = func.execute(2)
        assert result2 is None  # Still not enough

        result3 = func.execute(3)
        assert result3 == [1, 2, 3]  # Batch complete

    def test_batch_multiple_batches(self):
        """Test multiple batches"""
        func = ConcreteBatchFunction(batch_size=2)

        assert func.execute(1) is None
        assert func.execute(2) == [1, 2]

        assert func.execute(3) is None
        assert func.execute(4) == [3, 4]

    def test_batch_size_one(self):
        """Test batch size of 1"""
        func = ConcreteBatchFunction(batch_size=1)

        assert func.execute("a") == ["a"]
        assert func.execute("b") == ["b"]

    def test_batch_large_size(self):
        """Test batch with large size"""
        func = ConcreteBatchFunction(batch_size=10)

        for i in range(9):
            assert func.execute(i) is None

        result = func.execute(9)
        assert result == list(range(10))


class TestFunctionIntegration:
    """Integration tests for function combinations"""

    def test_map_filter_pipeline(self):
        """Test map followed by filter"""
        map_func = ConcreteMapFunction()
        filter_func = ConcreteFilterFunction()

        data = [5, 10, 15, 20]
        mapped = [map_func.execute(d) for d in data]  # [10, 20, 30, 40]
        filtered = [d for d in mapped if filter_func.execute(d)]  # [20, 30, 40]

        assert filtered == [20, 30, 40]

    def test_source_sink_pipeline(self):
        """Test source to sink pipeline"""
        source = ConcreteSourceFunction()
        sink = ConcreteSinkFunction()

        for _ in range(5):
            data = source.execute()
            sink.execute(data)

        assert sink.received == [1, 2, 3, 4, 5]

    def test_flatmap_filter_pipeline(self):
        """Test flatmap followed by filter"""
        flatmap_func = ConcreteFlatMapFunction()
        filter_func = ConcreteFilterFunction()

        data = 5
        flattened = flatmap_func.execute(data)  # [5, 10, 15]
        filtered = [d for d in flattened if filter_func.execute(d)]  # [15]

        assert filtered == [15]

    def test_map_batch_pipeline(self):
        """Test map followed by batch"""
        map_func = ConcreteMapFunction()
        batch_func = ConcreteBatchFunction(batch_size=3)

        data = [1, 2, 3, 4, 5]
        batches = []

        for d in data:
            mapped = map_func.execute(d)
            batch = batch_func.execute(mapped)
            if batch is not None:
                batches.append(batch)

        # First 3: [2, 4, 6]
        assert batches[0] == [2, 4, 6]
        # Remaining [8, 10] not batched yet
        assert len(batches) == 1


class TestFunctionEdgeCases:
    """Test edge cases for function classes"""

    def test_map_with_none(self):
        """Test map handles None"""

        class NoneHandlingMap(MapFunction):
            def execute(self, data):
                return data if data is not None else "default"

        func = NoneHandlingMap()
        assert func.execute(None) == "default"
        assert func.execute("value") == "value"

    def test_filter_with_exception(self):
        """Test filter handles exceptions"""

        class SafeFilter(FilterFunction):
            def execute(self, data):
                try:
                    return data["valid"]
                except (KeyError, TypeError):
                    return False

        func = SafeFilter()
        assert func.execute({"valid": True}) is True
        assert func.execute({}) is False
        assert func.execute(None) is False

    def test_flatmap_variable_length(self):
        """Test flatmap with variable length results"""

        class VariableFlatMap(FlatMapFunction):
            def execute(self, data):
                return list(range(data))

        func = VariableFlatMap()
        assert func.execute(0) == []
        assert func.execute(1) == [0]
        assert func.execute(5) == [0, 1, 2, 3, 4]

    def test_source_with_state(self):
        """Test source maintains state across calls"""

        class StatefulSource(SourceFunction):
            def __init__(self):
                super().__init__()
                self.values = iter([1, 2, 3])

            def execute(self):
                try:
                    return next(self.values)
                except StopIteration:
                    return None

        func = StatefulSource()
        assert func.execute() == 1
        assert func.execute() == 2
        assert func.execute() == 3
        assert func.execute() is None
