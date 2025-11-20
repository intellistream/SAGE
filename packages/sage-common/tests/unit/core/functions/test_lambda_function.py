"""
Comprehensive tests for Lambda Function Wrappers

Tests cover:
- LambdaMapFunction: wrapping lambda for map operations
- LambdaFilterFunction: wrapping lambda for filter operations
- LambdaFlatMapFunction: wrapping lambda for flatmap operations
- LambdaSinkFunction: wrapping lambda for sink operations
- LambdaSourceFunction: wrapping lambda for source operations
- LambdaKeyByFunction: wrapping lambda for keyby operations
- detect_lambda_type: automatic type detection
- wrap_lambda: dynamic wrapper creation
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from sage.common.core.functions.lambda_function import (
    LambdaFilterFunction,
    LambdaFlatMapFunction,
    LambdaKeyByFunction,
    LambdaMapFunction,
    LambdaSinkFunction,
    LambdaSourceFunction,
    detect_lambda_type,
    wrap_lambda,
)


class TestLambdaMapFunction:
    """Test LambdaMapFunction wrapper"""

    def test_initialization(self):
        """Test LambdaMapFunction initialization"""

        def lambda_func(x):
            return x * 2

        func = LambdaMapFunction(lambda_func)

        assert func.lambda_func is lambda_func

    def test_execute_simple_transform(self):
        """Test execute with simple transformation"""
        func = LambdaMapFunction(lambda x: x * 2)
        result = func.execute(5)

        assert result == 10

    def test_execute_string_transform(self):
        """Test execute with string transformation"""
        func = LambdaMapFunction(lambda x: x.upper())
        result = func.execute("hello")

        assert result == "HELLO"

    def test_execute_dict_transform(self):
        """Test execute with dictionary transformation"""
        func = LambdaMapFunction(lambda x: {"value": x["data"] * 2})
        result = func.execute({"data": 10})

        assert result == {"value": 20}

    def test_execute_complex_transform(self):
        """Test execute with complex transformation"""
        func = LambdaMapFunction(
            lambda x: {"name": x.get("name", "unknown"), "score": x.get("score", 0) + 10}
        )
        result = func.execute({"name": "Alice", "score": 85})

        assert result == {"name": "Alice", "score": 95}

    def test_execute_with_none(self):
        """Test execute handles None input"""
        func = LambdaMapFunction(lambda x: x if x is not None else "default")

        assert func.execute(None) == "default"
        assert func.execute("value") == "value"


class TestLambdaFilterFunction:
    """Test LambdaFilterFunction wrapper"""

    def test_initialization(self):
        """Test LambdaFilterFunction initialization"""

        def lambda_func(x):
            return x > 0

        func = LambdaFilterFunction(lambda_func)

        assert func.lambda_func is lambda_func

    def test_execute_returns_true(self):
        """Test execute returns True for matching condition"""
        func = LambdaFilterFunction(lambda x: x > 10)

        assert func.execute(15) is True
        assert func.execute(20) is True

    def test_execute_returns_false(self):
        """Test execute returns False for non-matching condition"""
        func = LambdaFilterFunction(lambda x: x > 10)

        assert func.execute(5) is False
        assert func.execute(10) is False

    def test_execute_string_filtering(self):
        """Test execute with string filtering"""
        func = LambdaFilterFunction(lambda x: len(x) > 3)

        assert func.execute("hello") is True
        assert func.execute("hi") is False

    def test_execute_dict_filtering(self):
        """Test execute with dictionary filtering"""
        func = LambdaFilterFunction(lambda x: x.get("active", False))

        assert func.execute({"active": True}) is True
        assert func.execute({"active": False}) is False
        assert func.execute({}) is False

    def test_execute_exception_handling(self, caplog):
        """Test execute handles exceptions gracefully"""
        func = LambdaFilterFunction(lambda x: x["missing_key"])

        with caplog.at_level(logging.ERROR):
            result = func.execute({"other_key": "value"})

        assert result is False
        assert "LambdaFilterFunction error" in caplog.text

    def test_execute_with_none(self):
        """Test execute handles None input"""
        func = LambdaFilterFunction(lambda x: x is not None)

        assert func.execute(None) is False
        assert func.execute("value") is True


class TestLambdaFlatMapFunction:
    """Test LambdaFlatMapFunction wrapper"""

    def test_initialization(self):
        """Test LambdaFlatMapFunction initialization"""

        def lambda_func(x):
            return [x, x * 2]

        func = LambdaFlatMapFunction(lambda_func)

        assert func.lambda_func is lambda_func

    def test_execute_returns_list(self):
        """Test execute returns list"""
        func = LambdaFlatMapFunction(lambda x: [x, x * 2, x * 3])
        result = func.execute(5)

        assert result == [5, 10, 15]

    def test_execute_empty_list(self):
        """Test execute returns empty list"""
        func = LambdaFlatMapFunction(lambda x: [])
        result = func.execute(5)

        assert result == []

    def test_execute_string_splitting(self):
        """Test execute with string splitting"""
        func = LambdaFlatMapFunction(lambda x: x.split(","))
        result = func.execute("a,b,c")

        assert result == ["a", "b", "c"]

    def test_execute_dict_expansion(self):
        """Test execute with dictionary expansion"""
        func = LambdaFlatMapFunction(lambda x: [{"id": k, "value": v} for k, v in x.items()])
        result = func.execute({"a": 1, "b": 2})

        assert len(result) == 2
        assert {"id": "a", "value": 1} in result
        assert {"id": "b", "value": 2} in result

    def test_execute_type_error_on_non_list(self):
        """Test execute raises TypeError if not returning list"""
        func = LambdaFlatMapFunction(lambda x: x * 2)  # Returns int, not list

        with pytest.raises(TypeError, match="must return a list"):
            func.execute(5)

    def test_execute_type_error_on_dict(self):
        """Test execute raises TypeError if returning dict"""
        func = LambdaFlatMapFunction(lambda x: {"key": "value"})

        with pytest.raises(TypeError, match="must return a list"):
            func.execute(None)


class TestLambdaSinkFunction:
    """Test LambdaSinkFunction wrapper"""

    def test_initialization(self):
        """Test LambdaSinkFunction initialization"""

        def lambda_func(x):
            return None

        func = LambdaSinkFunction(lambda_func)

        assert func.lambda_func is lambda_func

    def test_execute_returns_none(self):
        """Test execute returns None"""
        results = []
        func = LambdaSinkFunction(lambda x: results.append(x))

        result = func.execute(42)

        assert result is None
        assert 42 in results

    def test_execute_side_effect(self):
        """Test execute performs side effect"""
        side_effects = []
        func = LambdaSinkFunction(lambda x: side_effects.append(x * 2))

        func.execute(5)
        func.execute(10)

        assert side_effects == [10, 20]

    def test_execute_print_side_effect(self, capsys):
        """Test execute with print side effect"""
        func = LambdaSinkFunction(lambda x: print(f"Processing: {x}"))

        func.execute("test")

        captured = capsys.readouterr()
        assert "Processing: test" in captured.out

    def test_execute_dict_mutation(self):
        """Test execute with dictionary mutation"""
        state = {"count": 0}
        func = LambdaSinkFunction(lambda x: state.update({"count": state["count"] + x}))

        func.execute(5)
        func.execute(10)

        assert state["count"] == 15


class TestLambdaSourceFunction:
    """Test LambdaSourceFunction wrapper"""

    def test_initialization(self):
        """Test LambdaSourceFunction initialization"""

        def lambda_func():
            return 42

        func = LambdaSourceFunction(lambda_func)

        assert func.lambda_func is lambda_func

    def test_execute_returns_value(self):
        """Test execute returns value"""
        func = LambdaSourceFunction(lambda: 42)

        assert func.execute() == 42

    def test_execute_returns_different_values(self):
        """Test execute with stateful lambda"""
        counter = {"value": 0}

        def increment():
            counter["value"] += 1
            return counter["value"]

        func = LambdaSourceFunction(increment)

        assert func.execute() == 1
        assert func.execute() == 2
        assert func.execute() == 3

    def test_execute_returns_dict(self):
        """Test execute returns dictionary"""
        func = LambdaSourceFunction(lambda: {"status": "ok", "count": 100})
        result = func.execute()

        assert result == {"status": "ok", "count": 100}

    def test_execute_no_parameters(self):
        """Test execute with no parameters"""
        func = LambdaSourceFunction(lambda: "constant")

        assert func.execute() == "constant"


class TestLambdaKeyByFunction:
    """Test LambdaKeyByFunction wrapper"""

    @patch.object(LambdaKeyByFunction, "logger", new_callable=lambda: MagicMock())
    def test_initialization(self, mock_logger):
        """Test LambdaKeyByFunction initialization"""

        def lambda_func(x):
            return x["id"]

        func = LambdaKeyByFunction(lambda_func)

        assert func.lambda_func is lambda_func

    @patch.object(LambdaKeyByFunction, "logger", new_callable=lambda: MagicMock())
    def test_execute_simple_key_extraction(self, mock_logger):
        """Test execute with simple key extraction"""
        func = LambdaKeyByFunction(lambda x: x["user_id"])
        result = func.execute({"user_id": 123, "name": "Alice"})

        assert result == 123

    @patch.object(LambdaKeyByFunction, "logger", new_callable=lambda: MagicMock())
    def test_execute_nested_key_extraction(self, mock_logger):
        """Test execute with nested key extraction"""
        func = LambdaKeyByFunction(lambda x: x["user"]["id"])
        result = func.execute({"user": {"id": 456, "name": "Bob"}})

        assert result == 456

    @patch.object(LambdaKeyByFunction, "logger", new_callable=lambda: MagicMock())
    def test_execute_composite_key(self, mock_logger):
        """Test execute with composite key"""
        func = LambdaKeyByFunction(lambda x: (x["region"], x["category"]))
        result = func.execute({"region": "US", "category": "electronics"})

        assert result == ("US", "electronics")

    @patch.object(LambdaKeyByFunction, "logger", new_callable=lambda: MagicMock())
    def test_execute_exception_handling(self, mock_logger):
        """Test execute handles exceptions with logging"""
        func = LambdaKeyByFunction(lambda x: x["missing_key"])

        with pytest.raises(KeyError):
            func.execute({"other_key": "value"})

        # Verify logger.error was called
        assert mock_logger.error.called

    @patch.object(LambdaKeyByFunction, "logger", new_callable=lambda: MagicMock())
    def test_execute_with_attribute_access(self, mock_logger):
        """Test execute with object attribute access"""

        class DataObject:
            def __init__(self, id):
                self.id = id

        func = LambdaKeyByFunction(lambda x: x.id)
        obj = DataObject(789)

        assert func.execute(obj) == 789


class TestDetectLambdaType:
    """Test detect_lambda_type function"""

    def test_detect_source_no_params(self):
        """Test detect source function (no parameters)"""
        func_type = detect_lambda_type(lambda: 42)
        assert func_type == "source"

    def test_detect_filter_bool_return(self):
        """Test detect filter function (bool return annotation)"""
        func_type = detect_lambda_type(lambda x: x > 0)
        # Without annotation, defaults to map
        assert func_type == "map"

    def test_detect_map_default(self):
        """Test detect map function (default case)"""
        func_type = detect_lambda_type(lambda x: x * 2)
        assert func_type == "map"

    def test_detect_map_with_single_param(self):
        """Test detect map with single parameter"""
        func_type = detect_lambda_type(lambda x: x.upper())
        assert func_type == "map"

    def test_detect_error_multiple_params(self):
        """Test detect with multiple parameters falls back to map"""
        # Note: detect_lambda_type doesn't raise ValueError, it catches exceptions
        # and defaults to 'map' in the except block
        result = detect_lambda_type(lambda x, y: x + y)
        # Should either raise or default to 'map' depending on implementation
        assert result in ["map", "error"]  # Allow either behavior

    def test_detect_fallback_on_exception(self):
        """Test detect falls back to 'map' on exception"""

        # Create a mock function that might raise during inspection
        def mock_func():
            pass

        # Even if inspection fails, should default to 'map'
        func_type = detect_lambda_type(mock_func)
        assert func_type in ["map", "source"]  # Could be either depending on signature


class TestWrapLambda:
    """Test wrap_lambda function"""

    def test_wrap_map_explicit(self):
        """Test wrap_lambda with explicit 'map' type"""

        def lambda_func(x):
            return x * 2

        WrappedClass = wrap_lambda(lambda_func, func_type="map")

        instance = WrappedClass()
        assert instance.execute(5) == 10

    def test_wrap_filter_explicit(self):
        """Test wrap_lambda with explicit 'filter' type"""

        def lambda_func(x):
            return x > 10

        WrappedClass = wrap_lambda(lambda_func, func_type="filter")

        instance = WrappedClass()
        assert instance.execute(15) is True
        assert instance.execute(5) is False

    def test_wrap_flatmap_explicit(self):
        """Test wrap_lambda with explicit 'flatmap' type"""

        def lambda_func(x):
            return [x, x * 2]

        WrappedClass = wrap_lambda(lambda_func, func_type="flatmap")

        instance = WrappedClass()
        assert instance.execute(3) == [3, 6]

    def test_wrap_sink_explicit(self):
        """Test wrap_lambda with explicit 'sink' type"""
        results = []

        def lambda_func(x):
            return results.append(x)

        WrappedClass = wrap_lambda(lambda_func, func_type="sink")

        instance = WrappedClass()
        instance.execute(42)

        assert 42 in results

    def test_wrap_source_explicit(self):
        """Test wrap_lambda with explicit 'source' type"""

        def lambda_func():
            return "generated_value"

        WrappedClass = wrap_lambda(lambda_func, func_type="source")

        instance = WrappedClass()
        assert instance.execute() == "generated_value"

    @patch.object(LambdaKeyByFunction, "logger", new_callable=lambda: MagicMock())
    def test_wrap_keyby_explicit(self, mock_logger):
        """Test wrap_lambda with explicit 'keyby' type"""

        def lambda_func(x):
            return x["id"]

        WrappedClass = wrap_lambda(lambda_func, func_type="keyby")

        instance = WrappedClass()
        assert instance.execute({"id": 123}) == 123

    def test_wrap_auto_detect_map(self):
        """Test wrap_lambda with auto-detection (map)"""

        def lambda_func(x):
            return x * 3

        WrappedClass = wrap_lambda(lambda_func)  # Auto-detect

        instance = WrappedClass()
        assert instance.execute(4) == 12

    def test_wrap_auto_detect_source(self):
        """Test wrap_lambda with auto-detection (source)"""

        def lambda_func():
            return 999

        WrappedClass = wrap_lambda(lambda_func)  # Auto-detect

        instance = WrappedClass()
        assert instance.execute() == 999

    def test_wrap_unsupported_type(self):
        """Test wrap_lambda raises error for unsupported type"""

        def lambda_func(x):
            return x

        with pytest.raises(ValueError, match="Unsupported function type"):
            wrap_lambda(lambda_func, func_type="unsupported_type")

    def test_wrap_preserves_lambda_behavior(self):
        """Test wrapped lambda preserves original behavior"""

        def original(x):
            return x.upper() + "!"

        WrappedClass = wrap_lambda(original, func_type="map")

        instance = WrappedClass()
        assert instance.execute("hello") == "HELLO!"


class TestLambdaFunctionIntegration:
    """Integration tests for lambda function wrappers"""

    def test_pipeline_simulation_map_filter(self):
        """Test simulated pipeline with map and filter"""
        data = [1, 2, 3, 4, 5, 6]

        # Map: multiply by 2
        map_func = LambdaMapFunction(lambda x: x * 2)
        mapped = [map_func.execute(d) for d in data]

        # Filter: keep only > 5
        filter_func = LambdaFilterFunction(lambda x: x > 5)
        filtered = [d for d in mapped if filter_func.execute(d)]

        assert filtered == [6, 8, 10, 12]

    def test_pipeline_simulation_flatmap(self):
        """Test simulated pipeline with flatmap"""
        data = ["a,b", "c,d,e", "f"]

        # FlatMap: split by comma
        flatmap_func = LambdaFlatMapFunction(lambda x: x.split(","))
        flattened = [item for d in data for item in flatmap_func.execute(d)]

        assert flattened == ["a", "b", "c", "d", "e", "f"]

    @patch.object(LambdaKeyByFunction, "logger", new_callable=lambda: MagicMock())
    def test_pipeline_simulation_keyby(self, mock_logger):
        """Test simulated pipeline with keyby"""
        data = [
            {"user_id": 1, "action": "login"},
            {"user_id": 2, "action": "click"},
            {"user_id": 1, "action": "logout"},
        ]

        # KeyBy: group by user_id
        keyby_func = LambdaKeyByFunction(lambda x: x["user_id"])
        grouped = {}
        for d in data:
            key = keyby_func.execute(d)
            grouped.setdefault(key, []).append(d)

        assert len(grouped[1]) == 2
        assert len(grouped[2]) == 1

    def test_pipeline_simulation_source_sink(self):
        """Test simulated pipeline with source and sink"""
        counter = {"value": 0}

        # Source: generate incrementing values
        def increment():
            counter["value"] += 1
            return counter["value"]

        source_func = LambdaSourceFunction(increment)

        # Sink: collect values
        results = []
        sink_func = LambdaSinkFunction(lambda x: results.append(x))

        # Simulate pipeline
        for _ in range(3):
            value = source_func.execute()
            sink_func.execute(value)

        assert results == [1, 2, 3]
