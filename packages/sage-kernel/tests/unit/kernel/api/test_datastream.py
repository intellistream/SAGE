"""
Unit tests for DataStream class.

Tests cover:
- DataStream initialization and type resolution
- Transformation methods (map, filter, flatmap, sink, keyby)
- Stream connection (connect)
- Future stream operations (fill_future)
- Helper methods (print)
- Error handling and edge cases
"""

from unittest.mock import MagicMock, patch

import pytest

from sage.common.core import BaseFunction
from sage.kernel.api.connected_streams import ConnectedStreams
from sage.kernel.api.datastream import DataStream
from sage.kernel.api.local_environment import LocalEnvironment

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def local_env():
    """Create LocalEnvironment for testing"""
    return LocalEnvironment(name="test_env")


@pytest.fixture
def mock_transformation():
    """Create mock transformation"""
    transformation = MagicMock()
    transformation.basename = "mock_transformation"
    transformation.function_class = MagicMock(__name__="MockFunction")
    transformation.add_upstream = MagicMock()
    transformation.__name__ = "MockTransformation"
    return transformation


@pytest.fixture
def datastream(local_env, mock_transformation):
    """Create DataStream instance"""
    return DataStream(local_env, mock_transformation)


@pytest.fixture
def mock_function_class():
    """Mock function class for testing"""

    class MockMapFunction(BaseFunction):
        def __call__(self, data):
            return data * 2

    return MockMapFunction


# ============================================================================
# DataStream Initialization Tests
# ============================================================================


@pytest.mark.unit
class TestDataStreamInitialization:
    """Test DataStream initialization"""

    def test_init_basic(self, local_env, mock_transformation):
        """Test basic DataStream initialization"""
        ds = DataStream(local_env, mock_transformation)

        assert ds._environment is local_env
        assert ds.transformation is mock_transformation
        assert ds.logger is not None

    def test_init_stores_environment_reference(self, local_env, mock_transformation):
        """Test DataStream stores environment reference"""
        ds = DataStream(local_env, mock_transformation)

        assert ds._environment is local_env

    def test_init_stores_transformation_reference(self, local_env, mock_transformation):
        """Test DataStream stores transformation reference"""
        ds = DataStream(local_env, mock_transformation)

        assert ds.transformation is mock_transformation

    def test_type_param_resolution(self, local_env, mock_transformation):
        """Test type parameter resolution"""
        ds = DataStream(local_env, mock_transformation)

        # Should resolve to Any if no explicit type
        assert ds._type_param is not None


# ============================================================================
# Transformation Methods Tests
# ============================================================================


@pytest.mark.unit
class TestMapTransformation:
    """Test map transformation"""

    def test_map_with_function_class(self, datastream, mock_function_class):
        """Test map with BaseFunction class"""
        result = datastream.map(mock_function_class, parallelism=2)

        # Verify transformation was added to pipeline
        assert len(datastream._environment.pipeline) == 1
        transformation = datastream._environment.pipeline[0]
        assert transformation.__class__.__name__ == "MapTransformation"

        # Verify result is new DataStream
        assert isinstance(result, DataStream)
        assert result is not datastream

    def test_map_with_lambda(self, datastream):
        """Test map with lambda function"""
        map_func = lambda x: x * 2  # noqa: E731

        result = datastream.map(map_func)

        assert len(datastream._environment.pipeline) == 1
        assert isinstance(result, DataStream)

    def test_map_with_regular_function(self, datastream):
        """Test map with regular function"""

        def double(x):
            return x * 2

        result = datastream.map(double)

        assert len(datastream._environment.pipeline) == 1
        assert isinstance(result, DataStream)

    def test_map_with_parallelism(self, datastream, mock_function_class):
        """Test map respects parallelism parameter"""
        datastream.map(mock_function_class, parallelism=4)

        transformation = datastream._environment.pipeline[0]
        # Transformation should have parallelism set
        assert hasattr(transformation, "parallelism")

    def test_map_default_parallelism(self, datastream, mock_function_class):
        """Test map uses default parallelism when not specified"""
        datastream.map(mock_function_class)

        transformation = datastream._environment.pipeline[0]
        # Should use default parallelism of 1
        assert transformation.parallelism == 1

    def test_map_with_args_kwargs(self, datastream, mock_function_class):
        """Test map passes args and kwargs to transformation"""
        datastream.map(mock_function_class, "arg1", "arg2", key="value", parallelism=2)

        assert len(datastream._environment.pipeline) == 1


@pytest.mark.unit
class TestFilterTransformation:
    """Test filter transformation"""

    def test_filter_with_function_class(self, datastream):
        """Test filter with BaseFunction class"""

        class FilterFunction(BaseFunction):
            def __call__(self, data):
                return data > 10

        result = datastream.filter(FilterFunction)

        assert len(datastream._environment.pipeline) == 1
        transformation = datastream._environment.pipeline[0]
        assert transformation.__class__.__name__ == "FilterTransformation"
        assert isinstance(result, DataStream)

    def test_filter_with_lambda(self, datastream):
        """Test filter with lambda function"""
        result = datastream.filter(lambda x: x > 0)

        assert len(datastream._environment.pipeline) == 1
        assert isinstance(result, DataStream)

    def test_filter_with_parallelism(self, datastream):
        """Test filter respects parallelism parameter"""

        class FilterFunc(BaseFunction):
            pass

        datastream.filter(FilterFunc, parallelism=3)

        transformation = datastream._environment.pipeline[0]
        assert transformation.parallelism == 3

    def test_filter_default_parallelism(self, datastream):
        """Test filter uses default parallelism"""

        class FilterFunc(BaseFunction):
            pass

        datastream.filter(FilterFunc)

        transformation = datastream._environment.pipeline[0]
        assert transformation.parallelism == 1


@pytest.mark.unit
class TestFlatMapTransformation:
    """Test flatmap transformation"""

    def test_flatmap_with_function_class(self, datastream):
        """Test flatmap with BaseFunction class"""

        class FlatMapFunction(BaseFunction):
            def __call__(self, data):
                return [data, data * 2, data * 3]

        result = datastream.flatmap(FlatMapFunction)

        assert len(datastream._environment.pipeline) == 1
        transformation = datastream._environment.pipeline[0]
        assert transformation.__class__.__name__ == "FlatMapTransformation"
        assert isinstance(result, DataStream)

    def test_flatmap_with_lambda(self, datastream):
        """Test flatmap with lambda function"""
        result = datastream.flatmap(lambda x: [x, x * 2])

        assert len(datastream._environment.pipeline) == 1
        assert isinstance(result, DataStream)

    def test_flatmap_with_parallelism(self, datastream):
        """Test flatmap respects parallelism parameter"""

        class FlatMapFunc(BaseFunction):
            pass

        datastream.flatmap(FlatMapFunc, parallelism=5)

        transformation = datastream._environment.pipeline[0]
        assert transformation.parallelism == 5


@pytest.mark.unit
class TestSinkTransformation:
    """Test sink transformation"""

    def test_sink_with_function_class(self, datastream):
        """Test sink with BaseFunction class"""

        class SinkFunction(BaseFunction):
            def __call__(self, data):
                print(data)

        result = datastream.sink(SinkFunction)

        assert len(datastream._environment.pipeline) == 1
        transformation = datastream._environment.pipeline[0]
        assert transformation.__class__.__name__ == "SinkTransformation"

        # Sink returns same datastream
        assert result is datastream

    def test_sink_with_lambda(self, datastream):
        """Test sink with lambda function"""
        result = datastream.sink(lambda x: print(x))

        assert len(datastream._environment.pipeline) == 1
        assert result is datastream

    def test_sink_returns_same_stream(self, datastream):
        """Test sink returns same DataStream (terminal operation)"""

        class SinkFunc(BaseFunction):
            pass

        result = datastream.sink(SinkFunc)

        # Sink returns self, not new stream
        assert result is datastream

    def test_sink_with_parallelism(self, datastream):
        """Test sink respects parallelism parameter"""

        class SinkFunc(BaseFunction):
            pass

        datastream.sink(SinkFunc, parallelism=2)

        transformation = datastream._environment.pipeline[0]
        assert transformation.parallelism == 2


@pytest.mark.unit
class TestKeyByTransformation:
    """Test keyby transformation"""

    def test_keyby_with_function_class(self, datastream):
        """Test keyby with BaseFunction class"""

        class KeyFunction(BaseFunction):
            def __call__(self, data):
                return data % 10

        result = datastream.keyby(KeyFunction)

        assert len(datastream._environment.pipeline) == 1
        transformation = datastream._environment.pipeline[0]
        assert transformation.__class__.__name__ == "KeyByTransformation"
        assert isinstance(result, DataStream)

    def test_keyby_with_lambda(self, datastream):
        """Test keyby with lambda function"""
        result = datastream.keyby(lambda x: x % 5)

        assert len(datastream._environment.pipeline) == 1
        assert isinstance(result, DataStream)

    def test_keyby_default_strategy(self, datastream):
        """Test keyby uses default hash strategy"""

        class KeyFunc(BaseFunction):
            pass

        datastream.keyby(KeyFunc)

        transformation = datastream._environment.pipeline[0]
        # KeyByTransformation created successfully
        assert transformation.__class__.__name__ == "KeyByTransformation"

    def test_keyby_custom_strategy(self, datastream):
        """Test keyby with custom strategy"""

        class KeyFunc(BaseFunction):
            pass

        datastream.keyby(KeyFunc, strategy="range")

        transformation = datastream._environment.pipeline[0]
        # KeyByTransformation created successfully with custom strategy
        assert transformation.__class__.__name__ == "KeyByTransformation"

    def test_keyby_with_parallelism(self, datastream):
        """Test keyby respects parallelism parameter"""

        class KeyFunc(BaseFunction):
            pass

        datastream.keyby(KeyFunc, parallelism=8)

        transformation = datastream._environment.pipeline[0]
        assert transformation.parallelism == 8


# ============================================================================
# Stream Connection Tests
# ============================================================================


@pytest.mark.unit
class TestStreamConnection:
    """Test connect method for stream connections"""

    def test_connect_two_datastreams(self, local_env):
        """Test connecting two DataStream instances"""
        trans1 = MagicMock()
        trans1.basename = "trans1"
        trans1.__name__ = "Trans1"
        trans1.function_class = MagicMock(__name__="FuncClass1")
        trans1.env = local_env  # ConnectedStreams needs env attribute

        trans2 = MagicMock()
        trans2.basename = "trans2"
        trans2.__name__ = "Trans2"
        trans2.function_class = MagicMock(__name__="FuncClass2")
        trans2.env = local_env  # ConnectedStreams needs env attribute

        ds1 = DataStream(local_env, trans1)
        ds2 = DataStream(local_env, trans2)

        result = ds1.connect(ds2)

        # Result should be ConnectedStreams
        assert isinstance(result, ConnectedStreams)
        assert result._environment is local_env
        assert len(result.transformations) == 2
        assert result.transformations[0] is trans1
        assert result.transformations[1] is trans2

    def test_connect_datastream_to_connected_streams(self, local_env):
        """Test connecting DataStream to ConnectedStreams"""
        trans1 = MagicMock()
        trans1.basename = "trans1"
        trans1.__name__ = "Trans1"
        trans1.function_class = MagicMock(__name__="FuncClass1")
        trans1.env = local_env

        trans2 = MagicMock()
        trans2.basename = "trans2"
        trans2.__name__ = "Trans2"
        trans2.function_class = MagicMock(__name__="FuncClass2")
        trans2.env = local_env

        trans3 = MagicMock()
        trans3.basename = "trans3"
        trans3.__name__ = "Trans3"
        trans3.function_class = MagicMock(__name__="FuncClass3")
        trans3.env = local_env

        ds1 = DataStream(local_env, trans1)
        ds2 = DataStream(local_env, trans2)

        # Create connected streams
        connected = ds1.connect(ds2)
        assert len(connected.transformations) == 2

        # Connect another stream
        ds3 = DataStream(local_env, trans3)
        result = ds3.connect(connected)

        assert isinstance(result, ConnectedStreams)
        assert len(result.transformations) == 3
        assert result.transformations[0] is trans3
        assert result.transformations[1] is trans1
        assert result.transformations[2] is trans2

    def test_connect_preserves_order(self, local_env):
        """Test connect preserves transformation order"""
        transformations = []
        for i in range(4):
            t = MagicMock()
            t.basename = f"trans{i}"
            t.__name__ = f"Trans{i}"
            t.function_class = MagicMock(__name__=f"FuncClass{i}")
            t.env = local_env  # ConnectedStreams needs env attribute
            transformations.append(t)

        streams = [DataStream(local_env, t) for t in transformations]

        # Connect in sequence: ds0.connect(ds1).connect(ds2).connect(ds3)
        result = streams[0].connect(streams[1])
        result = result.connect(streams[2])
        result = result.connect(streams[3])

        # Order should be preserved
        assert len(result.transformations) == 4
        for i, t in enumerate(result.transformations):
            assert t is transformations[i]


# ============================================================================
# Future Stream Tests
# ============================================================================


@pytest.mark.unit
class TestFutureStream:
    """Test fill_future for feedback loops"""

    def test_fill_future_success(self, local_env):
        """Test successfully filling a future stream"""
        from sage.kernel.api.transformation.future_transformation import (
            FutureTransformation,
        )

        # Create future transformation
        future_trans = FutureTransformation(local_env, "feedback_loop")
        future_stream = DataStream(local_env, future_trans)

        # Create source stream
        source_trans = MagicMock()
        source_trans.basename = "source"
        source_trans.__name__ = "SourceTrans"
        source_trans.function_class = MagicMock(__name__="SourceFunc")
        source_stream = DataStream(local_env, source_trans)

        # Fill future
        source_stream.fill_future(future_stream)

        # Verify future is filled
        assert future_trans.filled is True

    def test_fill_future_with_non_future_raises_error(self, datastream):
        """Test fill_future raises error if target is not future stream"""
        # Create regular transformation
        regular_trans = MagicMock()
        regular_trans.basename = "regular"
        regular_trans.__name__ = "RegularTrans"
        regular_trans.function_class = MagicMock(__name__="RegularFunc")
        regular_stream = DataStream(datastream._environment, regular_trans)

        # Should raise ValueError
        with pytest.raises(ValueError, match="Target stream must be a future stream"):
            datastream.fill_future(regular_stream)

    def test_fill_future_already_filled_raises_error(self, local_env):
        """Test fill_future raises error if future already filled"""
        from sage.kernel.api.transformation.future_transformation import (
            FutureTransformation,
        )

        # Create and fill future
        future_trans = FutureTransformation(local_env, "test_future")
        future_stream = DataStream(local_env, future_trans)

        source1 = MagicMock()
        source1.basename = "source1"
        source1.__name__ = "Source1"
        source1.function_class = MagicMock(__name__="SourceFunc1")
        stream1 = DataStream(local_env, source1)

        # Fill once
        stream1.fill_future(future_stream)

        # Try to fill again - should raise RuntimeError
        source2 = MagicMock()
        source2.basename = "source2"
        source2.__name__ = "Source2"
        source2.function_class = MagicMock(__name__="SourceFunc2")
        stream2 = DataStream(local_env, source2)

        with pytest.raises(RuntimeError, match="has already been filled"):
            stream2.fill_future(future_stream)


# ============================================================================
# Helper Methods Tests
# ============================================================================


@pytest.mark.unit
class TestPrintHelper:
    """Test print helper method"""

    def test_print_default_params(self, datastream):
        """Test print with default parameters"""
        result = datastream.print()

        # Should create sink transformation
        assert len(datastream._environment.pipeline) == 1
        transformation = datastream._environment.pipeline[0]
        assert transformation.__class__.__name__ == "SinkTransformation"

        # Print returns new stream (for chaining)
        assert isinstance(result, DataStream)

    def test_print_with_prefix(self, datastream):
        """Test print with custom prefix"""
        result = datastream.print(prefix="DEBUG: ")

        assert len(datastream._environment.pipeline) == 1
        assert isinstance(result, DataStream)

    def test_print_with_separator(self, datastream):
        """Test print with custom separator"""
        datastream.print(separator=" -> ")

        assert len(datastream._environment.pipeline) == 1

    def test_print_with_colored(self, datastream):
        """Test print with colored parameter"""
        datastream.print(colored=False)

        assert len(datastream._environment.pipeline) == 1

    def test_print_chainable(self, datastream):
        """Test print is chainable"""

        class MapFunc(BaseFunction):
            pass

        result = datastream.print("Step 1: ").map(MapFunc).print("Step 2: ")

        # Should have 3 transformations: print, map, print
        assert len(datastream._environment.pipeline) == 3
        assert isinstance(result, DataStream)


# ============================================================================
# Internal Methods Tests
# ============================================================================


@pytest.mark.unit
class TestInternalMethods:
    """Test internal DataStream methods"""

    def test_apply_adds_upstream(self, datastream, mock_function_class):
        """Test _apply connects transformation to upstream"""
        # Create new transformation
        new_trans = MagicMock()
        new_trans.add_upstream = MagicMock()
        new_trans.__name__ = "NewTransformation"
        new_trans.function_class = MagicMock(__name__="NewFunc")

        # Apply it
        datastream._apply(new_trans)

        # Verify upstream was added
        new_trans.add_upstream.assert_called_once_with(datastream.transformation, input_index=0)

    def test_apply_adds_to_pipeline(self, datastream):
        """Test _apply adds transformation to environment pipeline"""
        initial_count = len(datastream._environment.pipeline)

        new_trans = MagicMock()
        new_trans.add_upstream = MagicMock()
        new_trans.__name__ = "NewTransformation"
        new_trans.function_class = MagicMock(__name__="NewFunc")

        datastream._apply(new_trans)

        assert len(datastream._environment.pipeline) == initial_count + 1
        assert datastream._environment.pipeline[-1] is new_trans

    def test_apply_returns_new_datastream(self, datastream):
        """Test _apply returns new DataStream instance"""
        new_trans = MagicMock()
        new_trans.add_upstream = MagicMock()
        new_trans.__name__ = "NewTransformation"
        new_trans.function_class = MagicMock(__name__="NewFunc")

        result = datastream._apply(new_trans)

        assert isinstance(result, DataStream)
        assert result is not datastream
        assert result.transformation is new_trans

    def test_get_transformation_classes_caches_imports(self, datastream):
        """Test _get_transformation_classes caches imports"""
        # First call
        classes1 = datastream._get_transformation_classes()

        # Second call
        classes2 = datastream._get_transformation_classes()

        # Should return same cached dict
        assert classes1 is classes2

    def test_get_transformation_classes_includes_expected_types(self, datastream):
        """Test _get_transformation_classes includes all expected types"""
        classes = datastream._get_transformation_classes()

        expected_keys = [
            "BaseTransformation",
            "FilterTransformation",
            "FlatMapTransformation",
            "MapTransformation",
            "SinkTransformation",
            "SourceTransformation",
            "KeyByTransformation",
        ]

        for key in expected_keys:
            assert key in classes


# ============================================================================
# Chaining and Integration Tests
# ============================================================================


@pytest.mark.unit
class TestTransformationChaining:
    """Test chaining multiple transformations"""

    def test_chain_multiple_transformations(self, local_env):
        """Test chaining multiple transformation methods"""

        class SourceFunc(BaseFunction):
            pass

        class MapFunc(BaseFunction):
            pass

        class FilterFunc(BaseFunction):
            pass

        class SinkFunc(BaseFunction):
            pass

        # Create source
        with patch("sage.kernel.api.datastream.DataStream", wraps=DataStream):
            stream = local_env.from_source(SourceFunc)

        # Chain transformations
        (
            stream.map(MapFunc)
            .filter(FilterFunc)
            .flatmap(lambda x: [x, x * 2])
            .keyby(lambda x: x % 10)
            .sink(SinkFunc)
        )

        # Pipeline should have all transformations
        # from_source adds SourceTransformation
        # Then: map, filter, flatmap, keyby, sink
        assert len(local_env.pipeline) >= 6

    def test_parallel_branches(self, local_env):
        """Test creating parallel branches from same source"""

        class SourceFunc(BaseFunction):
            pass

        class MapFunc1(BaseFunction):
            pass

        class MapFunc2(BaseFunction):
            pass

        with patch("sage.kernel.api.datastream.DataStream", wraps=DataStream):
            source = local_env.from_source(SourceFunc)

        # Create two branches
        source.map(MapFunc1)
        source.map(MapFunc2)

        # Both branches should exist in pipeline
        # Pipeline: SourceTransformation, MapTransformation (branch1), MapTransformation (branch2)
        assert len(local_env.pipeline) >= 3

    def test_multiple_sinks(self, local_env):
        """Test multiple sink operations"""

        class SourceFunc(BaseFunction):
            pass

        class SinkFunc1(BaseFunction):
            pass

        class SinkFunc2(BaseFunction):
            pass

        with patch("sage.kernel.api.datastream.DataStream", wraps=DataStream):
            stream = local_env.from_source(SourceFunc)

        # Add multiple sinks
        stream.sink(SinkFunc1)
        stream.sink(SinkFunc2)

        # Should have source + 2 sinks
        assert len(local_env.pipeline) >= 3


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_transformation_with_no_parallelism_uses_default(self, datastream):
        """Test transformation without parallelism parameter uses default"""

        class TestFunc(BaseFunction):
            pass

        datastream.map(TestFunc)

        transformation = datastream._environment.pipeline[0]
        assert transformation.parallelism == 1

    def test_transformation_with_zero_parallelism(self, datastream):
        """Test transformation with parallelism=0 (edge case)"""

        class TestFunc(BaseFunction):
            pass

        # parallelism=0 should still be accepted (even if unusual)
        datastream.map(TestFunc, parallelism=0)

        transformation = datastream._environment.pipeline[0]
        assert transformation.parallelism == 0

    def test_transformation_with_none_args(self, datastream):
        """Test transformation with None as argument"""

        class TestFunc(BaseFunction):
            pass

        datastream.map(TestFunc, None, key=None)

        # Should complete without error
        assert len(datastream._environment.pipeline) == 1

    def test_empty_lambda_function(self, datastream):
        """Test transformation with minimal lambda"""
        datastream.map(lambda x: x)

        assert len(datastream._environment.pipeline) == 1

    def test_complex_lambda_function(self, datastream):
        """Test transformation with complex lambda"""
        datastream.filter(lambda x: x > 10 and x < 100 and x % 2 == 0)

        assert len(datastream._environment.pipeline) == 1

    def test_keyby_with_multiple_strategies(self, datastream):
        """Test keyby with different strategy values"""

        class KeyFunc(BaseFunction):
            pass

        for strategy in ["hash", "range", "custom"]:
            env = LocalEnvironment(name="test")
            trans = MagicMock()
            trans.__name__ = "MockTransformation"
            trans.function_class = MagicMock(__name__="MockFunc")
            ds = DataStream(env, trans)

            ds.keyby(KeyFunc, strategy=strategy)

            transformation = ds._environment.pipeline[0]
            # KeyByTransformation created with specified strategy
            assert transformation.__class__.__name__ == "KeyByTransformation"


@pytest.mark.unit
class TestTypeResolution:
    """Test type parameter resolution"""

    def test_resolve_type_param_without_explicit_type(self, datastream):
        """Test type resolution when no explicit type provided"""
        # Should fall back to Any
        from typing import Any

        assert datastream._type_param == Any or datastream._type_param is not None

    def test_multiple_datastreams_independent_types(self, local_env):
        """Test multiple DataStreams have independent type parameters"""
        trans1 = MagicMock()
        trans1.__name__ = "Trans1"
        trans1.function_class = MagicMock(__name__="Func1")
        trans2 = MagicMock()
        trans2.__name__ = "Trans2"
        trans2.function_class = MagicMock(__name__="Func2")

        ds1 = DataStream(local_env, trans1)
        ds2 = DataStream(local_env, trans2)

        # Each should have its own type parameter
        assert hasattr(ds1, "_type_param")
        assert hasattr(ds2, "_type_param")
