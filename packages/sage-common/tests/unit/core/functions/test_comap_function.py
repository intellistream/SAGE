"""
Tests for CoMap Function class

CoMap functions process multiple input streams independently through
dedicated mapN methods (map0, map1, map2, etc.).

Tests cover:
- BaseCoMapFunction inheritance and properties
- Required abstract methods (map0, map1)
- Optional methods (map2, map3, map4)
- Execute method error handling
- Multi-stream processing patterns
"""

from unittest.mock import MagicMock

import pytest

from sage.common.core.functions.base_function import BaseFunction
from sage.common.core.functions.comap_function import BaseCoMapFunction


class ConcreteCoMapFunction(BaseCoMapFunction):
    """Concrete implementation of BaseCoMapFunction for testing"""

    def map0(self, data):
        """Process stream 0: double the value"""
        return data * 2

    def map1(self, data):
        """Process stream 1: add 10 to the value"""
        return data + 10


class FullCoMapFunction(BaseCoMapFunction):
    """CoMapFunction implementing all optional methods"""

    def map0(self, data):
        return data * 2

    def map1(self, data):
        return data + 10

    def map2(self, data):
        return data * 3

    def map3(self, data):
        return data - 5

    def map4(self, data):
        return data**2


class TestCoMapFunctionInheritance:
    """Test CoMapFunction inheritance and basic properties"""

    def test_comap_inherits_from_base_function(self):
        """Test BaseCoMapFunction inherits from BaseFunction"""
        func = ConcreteCoMapFunction()
        assert isinstance(func, BaseFunction)
        assert isinstance(func, BaseCoMapFunction)

    def test_is_comap_property(self):
        """Test is_comap property returns True"""
        func = ConcreteCoMapFunction()
        assert func.is_comap is True

    def test_is_comap_property_type(self):
        """Test is_comap returns boolean"""
        func = ConcreteCoMapFunction()
        assert isinstance(func.is_comap, bool)


class TestCoMapRequiredMethods:
    """Test required abstract methods map0 and map1"""

    def test_map0_basic_operation(self):
        """Test map0 processes stream 0 data"""
        func = ConcreteCoMapFunction()
        result = func.map0(5)
        assert result == 10

    def test_map1_basic_operation(self):
        """Test map1 processes stream 1 data"""
        func = ConcreteCoMapFunction()
        result = func.map1(5)
        assert result == 15

    def test_map0_with_different_types(self):
        """Test map0 with various data types"""

        class TypeFlexibleCoMap(BaseCoMapFunction):
            def map0(self, data):
                return str(data).upper()

            def map1(self, data):
                return data

        func = TypeFlexibleCoMap()
        assert func.map0("hello") == "HELLO"
        assert func.map0(123) == "123"

    def test_map1_with_different_types(self):
        """Test map1 with various data types"""

        class DictCoMap(BaseCoMapFunction):
            def map0(self, data):
                return data

            def map1(self, data):
                return {"value": data, "stream": 1}

        func = DictCoMap()
        result = func.map1(42)
        assert result == {"value": 42, "stream": 1}


class TestCoMapOptionalMethods:
    """Test optional methods map2, map3, map4"""

    def test_map2_default_returns_none(self):
        """Test map2 returns None by default"""
        func = ConcreteCoMapFunction()
        result = func.map2("any_data")
        assert result is None

    def test_map3_default_returns_none(self):
        """Test map3 returns None by default"""
        func = ConcreteCoMapFunction()
        result = func.map3("any_data")
        assert result is None

    def test_map4_default_returns_none(self):
        """Test map4 returns None by default"""
        func = ConcreteCoMapFunction()
        result = func.map4("any_data")
        assert result is None

    def test_map2_can_be_overridden(self):
        """Test map2 can be overridden"""
        func = FullCoMapFunction()
        result = func.map2(5)
        assert result == 15  # 5 * 3

    def test_map3_can_be_overridden(self):
        """Test map3 can be overridden"""
        func = FullCoMapFunction()
        result = func.map3(10)
        assert result == 5  # 10 - 5

    def test_map4_can_be_overridden(self):
        """Test map4 can be overridden"""
        func = FullCoMapFunction()
        result = func.map4(3)
        assert result == 9  # 3^2

    def test_all_optional_methods_together(self):
        """Test all optional methods work together"""
        func = FullCoMapFunction()
        assert func.map2(2) == 6
        assert func.map3(15) == 10
        assert func.map4(4) == 16


class TestCoMapExecuteMethod:
    """Test execute method raises NotImplementedError"""

    def test_execute_raises_not_implemented(self):
        """Test execute() raises NotImplementedError"""
        func = ConcreteCoMapFunction()

        with pytest.raises(NotImplementedError):
            func.execute("any_data")

    def test_execute_error_message_contains_class_name(self):
        """Test error message includes class name"""
        func = ConcreteCoMapFunction()

        with pytest.raises(NotImplementedError, match="ConcreteCoMapFunction"):
            func.execute("data")

    def test_execute_error_message_mentions_mapn(self):
        """Test error message mentions mapN methods"""
        func = ConcreteCoMapFunction()

        with pytest.raises(NotImplementedError, match="mapN methods"):
            func.execute("data")

    def test_execute_error_message_mentions_operator(self):
        """Test error message mentions CoMapOperator"""
        func = ConcreteCoMapFunction()

        with pytest.raises(NotImplementedError, match="CoMapOperator"):
            func.execute("data")


class TestCoMapMultiStreamProcessing:
    """Test multi-stream processing patterns"""

    def test_process_two_streams(self):
        """Test processing data from two different streams"""
        func = ConcreteCoMapFunction()

        # Simulate data from stream 0
        result0 = func.map0(10)
        assert result0 == 20

        # Simulate data from stream 1
        result1 = func.map1(10)
        assert result1 == 20

        # Same input, different outputs based on stream
        assert result0 == result1  # In this case equal, but processed differently

    def test_process_five_streams(self):
        """Test processing data from all five streams"""
        func = FullCoMapFunction()

        results = [
            func.map0(10),  # 20
            func.map1(10),  # 20
            func.map2(10),  # 30
            func.map3(10),  # 5
            func.map4(10),  # 100
        ]

        assert results == [20, 20, 30, 5, 100]

    def test_different_stream_transformations(self):
        """Test each stream applies different transformation"""

        class TransformCoMap(BaseCoMapFunction):
            def map0(self, data):
                return {"stream": 0, "data": data, "type": "double"}

            def map1(self, data):
                return {"stream": 1, "data": data, "type": "increment"}

            def map2(self, data):
                return {"stream": 2, "data": data, "type": "triple"}

        func = TransformCoMap()

        r0 = func.map0("test")
        r1 = func.map1("test")
        r2 = func.map2("test")

        assert r0["stream"] == 0
        assert r1["stream"] == 1
        assert r2["stream"] == 2

    def test_stateful_comap_processing(self):
        """Test CoMap with stateful processing per stream"""

        class StatefulCoMap(BaseCoMapFunction):
            def __init__(self):
                super().__init__()
                self.count0 = 0
                self.count1 = 0

            def map0(self, data):
                self.count0 += 1
                return f"Stream0-{self.count0}: {data}"

            def map1(self, data):
                self.count1 += 1
                return f"Stream1-{self.count1}: {data}"

        func = StatefulCoMap()

        assert func.map0("A") == "Stream0-1: A"
        assert func.map0("B") == "Stream0-2: B"
        assert func.map1("X") == "Stream1-1: X"
        assert func.map1("Y") == "Stream1-2: Y"
        assert func.map0("C") == "Stream0-3: C"


class TestCoMapIntegration:
    """Integration tests for CoMap functions"""

    def test_comap_with_filtering_logic(self):
        """Test CoMap with filtering logic per stream"""

        class FilteringCoMap(BaseCoMapFunction):
            def map0(self, data):
                # Stream 0: only pass positive numbers
                return data if data > 0 else None

            def map1(self, data):
                # Stream 1: only pass even numbers
                return data if data % 2 == 0 else None

        func = FilteringCoMap()

        assert func.map0(10) == 10
        assert func.map0(-5) is None
        assert func.map1(4) == 4
        assert func.map1(5) is None

    def test_comap_with_aggregation_logic(self):
        """Test CoMap with aggregation per stream"""

        class AggregatingCoMap(BaseCoMapFunction):
            def __init__(self):
                super().__init__()
                self.sum0 = 0
                self.sum1 = 0

            def map0(self, data):
                self.sum0 += data
                return self.sum0

            def map1(self, data):
                self.sum1 += data
                return self.sum1

        func = AggregatingCoMap()

        assert func.map0(10) == 10
        assert func.map0(5) == 15
        assert func.map1(3) == 3
        assert func.map1(7) == 10

    def test_comap_context_integration(self):
        """Test CoMap with context"""
        func = ConcreteCoMapFunction()
        mock_ctx = MagicMock()
        func.ctx = mock_ctx

        result = func.map0(5)
        assert result == 10
        assert func.ctx is mock_ctx


class TestCoMapEdgeCases:
    """Test edge cases for CoMap functions"""

    def test_comap_with_none_data(self):
        """Test CoMap handling None data"""

        class NoneHandlingCoMap(BaseCoMapFunction):
            def map0(self, data):
                return data if data is not None else "default0"

            def map1(self, data):
                return data if data is not None else "default1"

        func = NoneHandlingCoMap()
        assert func.map0(None) == "default0"
        assert func.map1(None) == "default1"
        assert func.map0("real") == "real"

    def test_comap_with_exception_handling(self):
        """Test CoMap with exception handling"""

        class SafeCoMap(BaseCoMapFunction):
            def map0(self, data):
                try:
                    return data["value"]
                except (KeyError, TypeError):
                    return "error"

            def map1(self, data):
                try:
                    return data.upper()
                except AttributeError:
                    return "error"

        func = SafeCoMap()
        assert func.map0({"value": 42}) == 42
        assert func.map0({}) == "error"
        assert func.map1("hello") == "HELLO"
        assert func.map1(123) == "error"

    def test_comap_with_complex_transformations(self):
        """Test CoMap with complex data transformations"""

        class ComplexCoMap(BaseCoMapFunction):
            def map0(self, data):
                # Stream 0: extract and transform list
                return [x * 2 for x in data] if isinstance(data, list) else []

            def map1(self, data):
                # Stream 1: flatten nested structure
                if isinstance(data, dict):
                    return list(data.values())
                return [data]

        func = ComplexCoMap()
        assert func.map0([1, 2, 3]) == [2, 4, 6]
        assert func.map1({"a": 1, "b": 2}) == [1, 2]
