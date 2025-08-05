#!/usr/bin/env python3
"""
Tests for sage.core.api.datastream module

This module provides comprehensive unit tests for the DataStream class,
following the testing organization structure outlined in the issue.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from sage.kernel.api.datastream import DataStream
from sage.kernel.api.transformation.base_transformation import BaseTransformation
from sage.kernel.api.transformation.map_transformation import MapTransformation
from sage.kernel.api.transformation.filter_transformation import FilterTransformation
from sage.kernel.api.transformation.flatmap_transformation import FlatMapTransformation
from sage.kernel.api.transformation.sink_transformation import SinkTransformation
from sage.kernel.api.transformation.keyby_transformation import KeyByTransformation
from sage.kernel.api.transformation.future_transformation import FutureTransformation
from sage.kernel.api.function.base_function import BaseFunction
from sage.kernel.api.connected_streams import ConnectedStreams


class MockEnvironment:
    """Mock environment for testing"""
    def __init__(self):
        self.pipeline = []
        self.name = "mock_env"


class MockTransformation(BaseTransformation):
    """Mock transformation for testing"""
    def __init__(self, env, function_class=None):
        if function_class is None:
            function_class = Mock
        super().__init__(env, function_class)
        self.basename = "mock_transformation"


class MockFunction(BaseFunction):
    """Mock function for testing"""
    def process(self, data):
        return data


@pytest.fixture
def mock_env():
    """Fixture providing a mock environment"""
    return MockEnvironment()


@pytest.fixture
def mock_transformation():
    """Fixture providing a mock transformation"""
    return MockTransformation(MockEnvironment())


@pytest.fixture
def datastream(mock_env, mock_transformation):
    """Fixture providing a DataStream instance"""
    return DataStream(mock_env, mock_transformation)


class TestDataStreamInit:
    """Test DataStream initialization"""
    
    @pytest.mark.unit
    def test_init_basic(self, mock_env, mock_transformation):
        """Test basic DataStream initialization"""
        ds = DataStream(mock_env, mock_transformation)
        
        assert ds._environment == mock_env
        assert ds.transformation == mock_transformation
        assert hasattr(ds, 'logger')
        assert hasattr(ds, '_type_param')
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.CustomLogger')
    def test_init_logger_creation(self, mock_logger_class, mock_env, mock_transformation):
        """Test that logger is created during initialization"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        ds = DataStream(mock_env, mock_transformation)
        
        mock_logger_class.assert_called_once()
        assert ds.logger == mock_logger_instance
    
    @pytest.mark.unit
    def test_init_type_param_resolution(self, mock_env, mock_transformation):
        """Test type parameter resolution"""
        ds = DataStream(mock_env, mock_transformation)
        
        # Should resolve to Any as fallback
        assert ds._type_param == Any


class TestDataStreamTransformations:
    """Test DataStream transformation methods"""
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_map_with_function_class(self, mock_wrap_lambda, datastream):
        """Test map with function class"""
        mock_function = Mock(spec=type)
        
        result = datastream.map(mock_function, "arg1", kwarg1="value1")
        
        # wrap_lambda should not be called for classes
        mock_wrap_lambda.assert_not_called()
        
        assert isinstance(result, DataStream)
        assert len(datastream._environment.pipeline) == 1
        transformation = datastream._environment.pipeline[0]
        assert isinstance(transformation, MapTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_map_with_lambda(self, mock_wrap_lambda, datastream):
        """Test map with lambda function"""
        lambda_func = lambda x: x * 2
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = datastream.map(lambda_func)
        
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'map')
        assert isinstance(result, DataStream)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_filter_with_function_class(self, mock_wrap_lambda, datastream):
        """Test filter with function class"""
        mock_function = Mock(spec=type)
        
        result = datastream.filter(mock_function)
        
        mock_wrap_lambda.assert_not_called()
        assert isinstance(result, DataStream)
        transformation = datastream._environment.pipeline[0]
        assert isinstance(transformation, FilterTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_filter_with_lambda(self, mock_wrap_lambda, datastream):
        """Test filter with lambda function"""
        lambda_func = lambda x: x > 0
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = datastream.filter(lambda_func)
        
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'filter')
        assert isinstance(result, DataStream)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_flatmap_with_function_class(self, mock_wrap_lambda, datastream):
        """Test flatmap with function class"""
        mock_function = Mock(spec=type)
        
        result = datastream.flatmap(mock_function)
        
        mock_wrap_lambda.assert_not_called()
        assert isinstance(result, DataStream)
        transformation = datastream._environment.pipeline[0]
        assert isinstance(transformation, FlatMapTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_flatmap_with_lambda(self, mock_wrap_lambda, datastream):
        """Test flatmap with lambda function"""
        lambda_func = lambda x: [x, x*2]
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = datastream.flatmap(lambda_func)
        
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'flatmap')
        assert isinstance(result, DataStream)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_sink_with_function_class(self, mock_wrap_lambda, datastream):
        """Test sink with function class"""
        mock_function = Mock(spec=type)
        
        result = datastream.sink(mock_function)
        
        mock_wrap_lambda.assert_not_called()
        assert isinstance(result, DataStream)
        assert result == datastream  # sink returns self
        transformation = datastream._environment.pipeline[0]
        assert isinstance(transformation, SinkTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_sink_with_lambda(self, mock_wrap_lambda, datastream):
        """Test sink with lambda function"""
        lambda_func = lambda x: print(x)
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = datastream.sink(lambda_func)
        
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'sink')
        assert result == datastream
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_keyby_with_default_strategy(self, mock_wrap_lambda, datastream):
        """Test keyby with default hash strategy"""
        mock_function = Mock(spec=type)
        
        result = datastream.keyby(mock_function)
        
        assert isinstance(result, DataStream)
        transformation = datastream._environment.pipeline[0]
        assert isinstance(transformation, KeyByTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_keyby_with_custom_strategy(self, mock_wrap_lambda, datastream):
        """Test keyby with custom strategy"""
        mock_function = Mock(spec=type)
        
        result = datastream.keyby(mock_function, strategy="range", custom_param="value")
        
        assert isinstance(result, DataStream)
        transformation = datastream._environment.pipeline[0]
        assert isinstance(transformation, KeyByTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_keyby_with_lambda(self, mock_wrap_lambda, datastream):
        """Test keyby with lambda function"""
        lambda_func = lambda x: x.id
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = datastream.keyby(lambda_func)
        
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'keyby')
        assert isinstance(result, DataStream)


class TestDataStreamConnect:
    """Test DataStream connection functionality"""
    
    @pytest.mark.unit
    def test_connect_with_datastream(self, datastream, mock_env):
        """Test connecting DataStream with another DataStream"""
        other_transformation = MockTransformation(mock_env)
        other_datastream = DataStream(mock_env, other_transformation)
        
        result = datastream.connect(other_datastream)
        
        assert isinstance(result, ConnectedStreams)
        assert len(result.transformations) == 2
        assert result.transformations[0] == datastream.transformation
        assert result.transformations[1] == other_datastream.transformation
    
    @pytest.mark.unit
    def test_connect_with_connected_streams(self, datastream, mock_env):
        """Test connecting DataStream with ConnectedStreams"""
        # Create ConnectedStreams with multiple transformations
        trans1 = MockTransformation(mock_env)
        trans2 = MockTransformation(mock_env)
        connected_streams = ConnectedStreams(mock_env, [trans1, trans2])
        
        result = datastream.connect(connected_streams)
        
        assert isinstance(result, ConnectedStreams)
        assert len(result.transformations) == 3
        assert result.transformations[0] == datastream.transformation
        assert result.transformations[1] == trans1
        assert result.transformations[2] == trans2


class TestDataStreamFillFuture:
    """Test DataStream fill_future functionality"""
    
    @pytest.mark.unit
    def test_fill_future_successful(self, datastream, mock_env):
        """Test successful future stream filling"""
        # Create a future transformation
        future_trans = FutureTransformation(mock_env, "test_future")
        future_stream = DataStream(mock_env, future_trans)
        
        # Fill the future
        datastream.fill_future(future_stream)
        
        # Verify the future was filled
        assert future_trans.filled is True
        assert future_trans.source_transformation == datastream.transformation
    
    @pytest.mark.unit
    def test_fill_future_not_future_stream(self, datastream, mock_env):
        """Test fill_future with non-future stream raises ValueError"""
        other_transformation = MockTransformation(mock_env)
        other_stream = DataStream(mock_env, other_transformation)
        
        with pytest.raises(ValueError, match="Target stream must be a future stream"):
            datastream.fill_future(other_stream)
    
    @pytest.mark.unit
    def test_fill_future_already_filled(self, datastream, mock_env):
        """Test fill_future with already filled future raises RuntimeError"""
        future_trans = FutureTransformation(mock_env, "test_future")
        future_stream = DataStream(mock_env, future_trans)
        
        # Fill it once
        datastream.fill_future(future_stream)
        
        # Try to fill again
        with pytest.raises(RuntimeError, match="Future stream 'test_future' has already been filled"):
            datastream.fill_future(future_stream)


class TestDataStreamPrint:
    """Test DataStream print functionality"""
    
    @pytest.mark.unit
    @patch('sage.lib.io.sink.PrintSink')
    def test_print_with_defaults(self, mock_print_sink, datastream):
        """Test print with default parameters"""
        result = datastream.print()
        
        assert isinstance(result, DataStream)
        # Verify that sink was called with PrintSink
        transformation = datastream._environment.pipeline[0]
        assert isinstance(transformation, SinkTransformation)
    
    @pytest.mark.unit
    @patch('sage.lib.io.sink.PrintSink')
    def test_print_with_custom_params(self, mock_print_sink, datastream):
        """Test print with custom parameters"""
        result = datastream.print(
            prefix="DEBUG:",
            separator=" -> ",
            colored=False
        )
        
        assert isinstance(result, DataStream)
        transformation = datastream._environment.pipeline[0]
        assert isinstance(transformation, SinkTransformation)


class TestDataStreamApply:
    """Test DataStream internal _apply method"""
    
    @pytest.mark.unit
    def test_apply_method(self, datastream, mock_env):
        """Test _apply method adds transformation and returns DataStream"""
        new_transformation = MockTransformation(mock_env)
        
        result = datastream._apply(new_transformation)
        
        # Verify upstream connection
        new_transformation.add_upstream.assert_called_once_with(
            datastream.transformation, input_index=0
        )
        
        # Verify transformation added to pipeline
        assert new_transformation in datastream._environment.pipeline
        
        # Verify returned DataStream
        assert isinstance(result, DataStream)
        assert result.transformation == new_transformation
        assert result._environment == mock_env


class TestDataStreamTypeResolution:
    """Test DataStream type parameter resolution"""
    
    @pytest.mark.unit
    def test_resolve_type_param_fallback(self, datastream):
        """Test type parameter resolution fallback to Any"""
        # Default resolution should fallback to Any
        assert datastream._type_param == Any
    
    @pytest.mark.unit
    def test_resolve_type_param_with_orig_class(self, mock_env, mock_transformation):
        """Test type parameter resolution with __orig_class__"""
        from typing import get_origin, get_args
        
        # This is a more complex test that would require proper generic setup
        # For now, we test the fallback behavior
        ds = DataStream(mock_env, mock_transformation)
        assert ds._type_param == Any


class TestDataStreamChaining:
    """Test DataStream method chaining"""
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_chaining_transformations(self, mock_wrap_lambda, datastream):
        """Test chaining multiple transformations"""
        mock_function = Mock(spec=type)
        
        # Chain multiple operations
        result = (datastream
                 .map(mock_function)
                 .filter(mock_function)
                 .flatmap(mock_function))
        
        assert isinstance(result, DataStream)
        
        # Should have 3 transformations in pipeline
        assert len(datastream._environment.pipeline) == 3
        
        # Verify transformation types
        transformations = datastream._environment.pipeline
        assert isinstance(transformations[0], MapTransformation)
        assert isinstance(transformations[1], FilterTransformation)
        assert isinstance(transformations[2], FlatMapTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_chaining_with_sink(self, mock_wrap_lambda, datastream):
        """Test chaining ending with sink"""
        mock_function = Mock(spec=type)
        
        result = (datastream
                 .map(mock_function)
                 .filter(mock_function)
                 .sink(mock_function))
        
        # Sink should return the same DataStream (self)
        assert result == datastream
        
        # Should have 3 transformations
        assert len(datastream._environment.pipeline) == 3
        transformations = datastream._environment.pipeline
        assert isinstance(transformations[2], SinkTransformation)


class TestDataStreamIntegration:
    """Integration tests for DataStream"""
    
    @pytest.mark.integration
    @patch('sage.core.api.datastream.wrap_lambda')
    def test_complex_pipeline(self, mock_wrap_lambda, mock_env):
        """Test complex pipeline with multiple operations"""
        # Create initial transformation and datastream
        source_trans = MockTransformation(mock_env)
        datastream = DataStream(mock_env, source_trans)
        
        mock_function = Mock(spec=type)
        
        # Build complex pipeline
        result = (datastream
                 .map(mock_function)
                 .filter(mock_function)
                 .keyby(mock_function, strategy="hash")
                 .flatmap(mock_function))
        
        # Connect with another stream
        other_trans = MockTransformation(mock_env)
        other_stream = DataStream(mock_env, other_trans)
        
        connected = result.connect(other_stream)
        assert isinstance(connected, ConnectedStreams)
        
        # Verify final pipeline state
        pipeline = mock_env.pipeline
        assert len(pipeline) >= 4  # At least 4 transformations added
    
    @pytest.mark.integration
    def test_future_stream_workflow(self, mock_env):
        """Test complete future stream workflow"""
        # Create source stream
        source_trans = MockTransformation(mock_env)
        source_stream = DataStream(mock_env, source_trans)
        
        # Create future stream
        future_trans = FutureTransformation(mock_env, "feedback")
        future_stream = DataStream(mock_env, future_trans)
        
        # Connect and process
        connected = source_stream.connect(future_stream)
        assert isinstance(connected, ConnectedStreams)
        
        # Process and fill future (simulate processing result)
        mock_function = Mock(spec=type)
        with patch('sage.core.api.datastream.wrap_lambda'):
            processed = source_stream.map(mock_function)
        
        # Fill the future
        processed.fill_future(future_stream)
        
        # Verify future was filled
        assert future_trans.filled is True


class TestDataStreamEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_empty_pipeline_operations(self, mock_env):
        """Test operations on stream with empty pipeline"""
        trans = MockTransformation(mock_env)
        ds = DataStream(mock_env, trans)
        
        # Operations should still work
        mock_function = Mock(spec=type)
        with patch('sage.core.api.datastream.wrap_lambda'):
            result = ds.map(mock_function)
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
    
    @pytest.mark.unit
    def test_none_function_handling(self, datastream):
        """Test handling of None function (should raise appropriate error)"""
        # This would typically raise an error in the transformation creation
        # We test that the error bubbles up appropriately
        with pytest.raises((TypeError, AttributeError)):
            datastream.map(None)
    
    @pytest.mark.unit
    def test_multiple_sink_operations(self, datastream):
        """Test multiple sink operations on same stream"""
        mock_function = Mock(spec=type)
        
        with patch('sage.core.api.datastream.wrap_lambda'):
            result1 = datastream.sink(mock_function)
            result2 = datastream.sink(mock_function)
        
        # Both should return the same datastream
        assert result1 == datastream
        assert result2 == datastream
        
        # Should have 2 sink transformations
        assert len(datastream._environment.pipeline) == 2
        assert all(isinstance(t, SinkTransformation) 
                  for t in datastream._environment.pipeline)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
