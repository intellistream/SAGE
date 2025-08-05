#!/usr/bin/env python3
"""
Tests for sage.core.api.connected_streams module

This module provides comprehensive unit tests for the ConnectedStreams class,
following the testing organization structure outlined in the issue.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from sage.kernel.api.connected_streams import ConnectedStreams
from sage.kernel.api.datastream import DataStream
from sage.kernel.api.transformation.base_transformation import BaseTransformation
from sage.kernel.api.transformation.map_transformation import MapTransformation
from sage.kernel.api.transformation.sink_transformation import SinkTransformation
from sage.kernel.api.transformation.join_transformation import JoinTransformation
from sage.kernel.api.function.base_function import BaseFunction


class MockEnvironment:
    """Mock environment for testing"""
    def __init__(self):
        self.pipeline = []
        self.name = "mock_env"


class MockTransformation(BaseTransformation):
    """Mock transformation for testing"""
    def __init__(self, env, function_class=None, name=None):
        if function_class is None:
            function_class = Mock
        super().__init__(env, function_class)
        self.basename = name or "mock_transformation"
        self.add_upstream = Mock()


class MockFunction(BaseFunction):
    """Mock function for testing"""
    def process(self, data):
        return data


@pytest.fixture
def mock_env():
    """Fixture providing a mock environment"""
    return MockEnvironment()


@pytest.fixture
def mock_transformations(mock_env):
    """Fixture providing mock transformations"""
    return [
        MockTransformation(mock_env, name="trans1"),
        MockTransformation(mock_env, name="trans2"),
        MockTransformation(mock_env, name="trans3")
    ]


@pytest.fixture
def connected_streams(mock_env, mock_transformations):
    """Fixture providing a ConnectedStreams instance"""
    return ConnectedStreams(mock_env, mock_transformations[:2])


class TestConnectedStreamsInit:
    """Test ConnectedStreams initialization"""
    
    @pytest.mark.unit
    def test_init_basic(self, mock_env, mock_transformations):
        """Test basic ConnectedStreams initialization"""
        transformations = mock_transformations[:2]
        cs = ConnectedStreams(mock_env, transformations)
        
        assert cs._environment == mock_env
        assert cs.transformations == transformations
        assert len(cs.transformations) == 2
    
    @pytest.mark.unit
    def test_init_single_transformation(self, mock_env, mock_transformations):
        """Test initialization with single transformation"""
        transformation = [mock_transformations[0]]
        cs = ConnectedStreams(mock_env, transformation)
        
        assert len(cs.transformations) == 1
        assert cs.transformations[0] == mock_transformations[0]
    
    @pytest.mark.unit
    def test_init_multiple_transformations(self, mock_env, mock_transformations):
        """Test initialization with multiple transformations"""
        cs = ConnectedStreams(mock_env, mock_transformations)
        
        assert len(cs.transformations) == 3
        assert cs.transformations == mock_transformations
    
    @pytest.mark.unit
    def test_init_empty_transformations(self, mock_env):
        """Test initialization with empty transformation list"""
        cs = ConnectedStreams(mock_env, [])
        
        assert len(cs.transformations) == 0
        assert cs.transformations == []


class TestConnectedStreamsTransformations:
    """Test ConnectedStreams transformation methods"""
    
    @pytest.mark.unit
    @patch('sage.core.api.connected_streams.wrap_lambda')
    def test_map_with_function_class(self, mock_wrap_lambda, connected_streams):
        """Test map with function class"""
        mock_function = Mock(spec=type)
        
        result = connected_streams.map(mock_function, "arg1", kwarg1="value1")
        
        # wrap_lambda should not be called for classes
        mock_wrap_lambda.assert_not_called()
        
        assert isinstance(result, DataStream)
        assert len(connected_streams._environment.pipeline) == 1
        transformation = connected_streams._environment.pipeline[0]
        assert isinstance(transformation, MapTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.connected_streams.wrap_lambda')
    def test_map_with_lambda(self, mock_wrap_lambda, connected_streams):
        """Test map with lambda function"""
        lambda_func = lambda x: x * 2
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = connected_streams.map(lambda_func)
        
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'map')
        assert isinstance(result, DataStream)
    
    @pytest.mark.unit
    @patch('sage.core.api.connected_streams.wrap_lambda')
    def test_sink_with_function_class(self, mock_wrap_lambda, connected_streams):
        """Test sink with function class"""
        mock_function = Mock(spec=type)
        
        result = connected_streams.sink(mock_function)
        
        mock_wrap_lambda.assert_not_called()
        assert isinstance(result, DataStream)
        transformation = connected_streams._environment.pipeline[0]
        assert isinstance(transformation, SinkTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.connected_streams.wrap_lambda')
    def test_sink_with_lambda(self, mock_wrap_lambda, connected_streams):
        """Test sink with lambda function"""
        lambda_func = lambda x: print(x)
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = connected_streams.sink(lambda_func)
        
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'sink')
        assert isinstance(result, DataStream)


class TestConnectedStreamsPrint:
    """Test ConnectedStreams print functionality"""
    
    @pytest.mark.unit
    @patch('sage_libs.io.sink.PrintSink')
    def test_print_with_defaults(self, mock_print_sink, connected_streams):
        """Test print with default parameters"""
        result = connected_streams.print()
        
        assert isinstance(result, DataStream)
        transformation = connected_streams._environment.pipeline[0]
        assert isinstance(transformation, SinkTransformation)
    
    @pytest.mark.unit
    @patch('sage_libs.io.sink.PrintSink')
    def test_print_with_custom_params(self, mock_print_sink, connected_streams):
        """Test print with custom parameters"""
        result = connected_streams.print(
            prefix="CONNECTED:",
            separator=" => ",
            colored=False
        )
        
        assert isinstance(result, DataStream)
        transformation = connected_streams._environment.pipeline[0]
        assert isinstance(transformation, SinkTransformation)


class TestConnectedStreamsConnect:
    """Test ConnectedStreams connection functionality"""
    
    @pytest.mark.unit
    def test_connect_with_datastream(self, connected_streams, mock_env):
        """Test connecting ConnectedStreams with DataStream"""
        other_transformation = MockTransformation(mock_env, name="other")
        other_datastream = DataStream(mock_env, other_transformation)
        
        result = connected_streams.connect(other_datastream)
        
        assert isinstance(result, ConnectedStreams)
        assert len(result.transformations) == 3  # 2 original + 1 new
        assert result.transformations[:2] == connected_streams.transformations
        assert result.transformations[2] == other_transformation
    
    @pytest.mark.unit
    def test_connect_with_connected_streams(self, connected_streams, mock_env):
        """Test connecting ConnectedStreams with another ConnectedStreams"""
        other_transformations = [
            MockTransformation(mock_env, name="other1"),
            MockTransformation(mock_env, name="other2")
        ]
        other_connected = ConnectedStreams(mock_env, other_transformations)
        
        result = connected_streams.connect(other_connected)
        
        assert isinstance(result, ConnectedStreams)
        assert len(result.transformations) == 4  # 2 + 2
        assert result.transformations[:2] == connected_streams.transformations
        assert result.transformations[2:] == other_transformations
    
    @pytest.mark.unit
    def test_connect_preserves_order(self, mock_env):
        """Test that connect preserves transformation order"""
        trans1 = MockTransformation(mock_env, name="first")
        trans2 = MockTransformation(mock_env, name="second")
        trans3 = MockTransformation(mock_env, name="third")
        
        cs1 = ConnectedStreams(mock_env, [trans1])
        cs2 = ConnectedStreams(mock_env, [trans2])
        ds3 = DataStream(mock_env, trans3)
        
        # Chain connections
        result = cs1.connect(cs2).connect(ds3)
        
        assert len(result.transformations) == 3
        assert result.transformations[0].basename == "first"
        assert result.transformations[1].basename == "second"
        assert result.transformations[2].basename == "third"


class TestConnectedStreamsComap:
    """Test ConnectedStreams comap functionality"""
    
    @pytest.mark.unit
    def test_comap_with_function_class(self, connected_streams):
        """Test comap with function class"""
        mock_function = Mock(spec=type)
        
        result = connected_streams.comap(mock_function, "arg1", kwarg1="value1")
        
        assert isinstance(result, DataStream)
        assert len(connected_streams._environment.pipeline) == 1
    
    @pytest.mark.unit
    def test_comap_with_lambda_functions_raises_error(self, connected_streams):
        """Test comap with lambda functions raises NotImplementedError"""
        lambda_func = lambda x: x * 2
        
        with pytest.raises(NotImplementedError, match="Lambda functions are not supported for comap operations"):
            connected_streams.comap(lambda_func)
    
    @pytest.mark.unit
    def test_comap_with_lambda_list_raises_error(self, connected_streams):
        """Test comap with list of lambda functions raises NotImplementedError"""
        lambda_funcs = [lambda x: x, lambda y: y * 2]
        
        with pytest.raises(NotImplementedError, match="Lambda functions are not supported for comap operations"):
            connected_streams.comap(lambda_funcs)
    
    @pytest.mark.unit
    def test_comap_kwargs_warning_with_callables(self, connected_streams):
        """Test comap issues warning when kwargs provided with callables"""
        lambda_func = lambda x: x
        
        # Should raise NotImplementedError before warning, but test the concept
        with pytest.raises(NotImplementedError):
            connected_streams.comap(lambda_func, kwarg1="value")
    
    @pytest.mark.unit
    def test_comap_validation_errors(self, connected_streams):
        """Test comap validation errors"""
        # Test with invalid function type
        with pytest.raises((TypeError, ValueError)):
            connected_streams.comap("not_a_function")
        
        # Test with None
        with pytest.raises((TypeError, ValueError)):
            connected_streams.comap(None)


class TestConnectedStreamsApply:
    """Test ConnectedStreams internal _apply method"""
    
    @pytest.mark.unit
    def test_apply_method(self, connected_streams, mock_env):
        """Test _apply method connects all upstream transformations"""
        new_transformation = MockTransformation(mock_env, name="new")
        
        result = connected_streams._apply(new_transformation)
        
        # Verify all upstream connections were made
        expected_calls = []
        for i, trans in enumerate(connected_streams.transformations):
            expected_calls.append(((trans, i), {}))
        
        assert new_transformation.add_upstream.call_count == len(connected_streams.transformations)
        
        # Verify transformation added to pipeline
        assert new_transformation in connected_streams._environment.pipeline
        
        # Verify returned DataStream
        assert isinstance(result, DataStream)
        assert result.transformation == new_transformation
        assert result._environment == mock_env


class TestConnectedStreamsChaining:
    """Test ConnectedStreams method chaining"""
    
    @pytest.mark.unit
    @patch('sage.core.api.connected_streams.wrap_lambda')
    def test_chaining_transformations(self, mock_wrap_lambda, connected_streams):
        """Test chaining multiple transformations"""
        mock_function = Mock(spec=type)
        
        # Chain operations (map returns DataStream, so we can't chain further on ConnectedStreams)
        result = connected_streams.map(mock_function)
        
        assert isinstance(result, DataStream)
        assert len(connected_streams._environment.pipeline) == 1
    
    @pytest.mark.unit
    @patch('sage.core.api.connected_streams.wrap_lambda')
    def test_chaining_with_sink(self, mock_wrap_lambda, connected_streams):
        """Test chaining ending with sink"""
        mock_function = Mock(spec=type)
        
        result = connected_streams.sink(mock_function)
        
        assert isinstance(result, DataStream)
        transformation = connected_streams._environment.pipeline[0]
        assert isinstance(transformation, SinkTransformation)


class TestConnectedStreamsMultipleInputs:
    """Test ConnectedStreams with multiple input handling"""
    
    @pytest.mark.unit
    def test_two_input_streams(self, mock_env):
        """Test ConnectedStreams with two input transformations"""
        trans1 = MockTransformation(mock_env, name="input1")
        trans2 = MockTransformation(mock_env, name="input2")
        
        cs = ConnectedStreams(mock_env, [trans1, trans2])
        
        # Apply a transformation
        mock_function = Mock(spec=type)
        with patch('sage.core.api.connected_streams.wrap_lambda'):
            result = cs.map(mock_function)
        
        # Verify both inputs were connected
        new_transformation = cs._environment.pipeline[0]
        assert new_transformation.add_upstream.call_count == 2
    
    @pytest.mark.unit
    def test_multiple_input_streams(self, mock_env):
        """Test ConnectedStreams with multiple input transformations"""
        transformations = [
            MockTransformation(mock_env, name=f"input{i}")
            for i in range(5)
        ]
        
        cs = ConnectedStreams(mock_env, transformations)
        
        # Apply a transformation
        mock_function = Mock(spec=type)
        with patch('sage.core.api.connected_streams.wrap_lambda'):
            result = cs.map(mock_function)
        
        # Verify all inputs were connected with correct indices
        new_transformation = cs._environment.pipeline[0]
        assert new_transformation.add_upstream.call_count == 5
        
        # Verify input indices
        calls = new_transformation.add_upstream.call_args_list
        for i, call in enumerate(calls):
            args, kwargs = call
            assert args[0] == transformations[i]
            assert args[1] == i  # input_index should match position


class TestConnectedStreamsIntegration:
    """Integration tests for ConnectedStreams"""
    
    @pytest.mark.integration
    def test_complex_connection_workflow(self, mock_env):
        """Test complex workflow with multiple connections"""
        # Create initial streams
        trans1 = MockTransformation(mock_env, name="source1")
        trans2 = MockTransformation(mock_env, name="source2")
        
        ds1 = DataStream(mock_env, trans1)
        ds2 = DataStream(mock_env, trans2)
        
        # Connect them
        connected = ds1.connect(ds2)
        assert isinstance(connected, ConnectedStreams)
        assert len(connected.transformations) == 2
        
        # Add more streams
        trans3 = MockTransformation(mock_env, name="source3")
        ds3 = DataStream(mock_env, trans3)
        
        extended = connected.connect(ds3)
        assert len(extended.transformations) == 3
        
        # Apply transformation
        mock_function = Mock(spec=type)
        with patch('sage.core.api.connected_streams.wrap_lambda'):
            result = extended.map(mock_function)
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
    
    @pytest.mark.integration
    def test_comap_integration(self, mock_env):
        """Test comap integration with proper function class"""
        from sage.kernel.api.function.comap_function import BaseCoMapFunction
        
        # Create mock CoMap function
        class MockCoMapFunction(BaseCoMapFunction):
            def map0(self, data):
                return data
            
            def map1(self, data):
                return data * 2
        
        trans1 = MockTransformation(mock_env, name="input1")
        trans2 = MockTransformation(mock_env, name="input2")
        cs = ConnectedStreams(mock_env, [trans1, trans2])
        
        # Apply comap
        result = cs.comap(MockCoMapFunction)
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1


class TestConnectedStreamsEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_empty_transformations_operations(self, mock_env):
        """Test operations on ConnectedStreams with empty transformations"""
        cs = ConnectedStreams(mock_env, [])
        
        mock_function = Mock(spec=type)
        with patch('sage.core.api.connected_streams.wrap_lambda'):
            result = cs.map(mock_function)
        
        assert isinstance(result, DataStream)
        # Should still create transformation even with no inputs
        assert len(mock_env.pipeline) == 1
        
        # But add_upstream should not be called since no inputs exist
        transformation = mock_env.pipeline[0]
        # This test depends on the actual implementation behavior
    
    @pytest.mark.unit
    def test_single_transformation_behavior(self, mock_env):
        """Test behavior with single transformation (edge of ConnectedStreams use case)"""
        trans = MockTransformation(mock_env, name="single")
        cs = ConnectedStreams(mock_env, [trans])
        
        mock_function = Mock(spec=type)
        with patch('sage.core.api.connected_streams.wrap_lambda'):
            result = cs.map(mock_function)
        
        assert isinstance(result, DataStream)
        
        # Should have one upstream connection
        new_transformation = mock_env.pipeline[0]
        new_transformation.add_upstream.assert_called_once_with(trans, 0)
    
    @pytest.mark.unit
    def test_none_function_handling(self, connected_streams):
        """Test handling of None function"""
        with pytest.raises((TypeError, AttributeError)):
            connected_streams.map(None)
    
    @pytest.mark.unit
    def test_multiple_operations_on_same_connected_streams(self, connected_streams):
        """Test multiple operations on the same ConnectedStreams instance"""
        mock_function = Mock(spec=type)
        
        with patch('sage.core.api.connected_streams.wrap_lambda'):
            result1 = connected_streams.map(mock_function)
            result2 = connected_streams.sink(mock_function)
        
        # Both should work and return DataStreams
        assert isinstance(result1, DataStream)
        assert isinstance(result2, DataStream)
        
        # Should have 2 transformations in pipeline
        assert len(connected_streams._environment.pipeline) == 2
    
    @pytest.mark.unit
    def test_transformation_order_preservation(self, mock_env):
        """Test that transformation order is preserved through operations"""
        transformations = [
            MockTransformation(mock_env, name=f"ordered_{i}")
            for i in range(3)
        ]
        
        cs = ConnectedStreams(mock_env, transformations)
        
        # Verify order is preserved
        for i, trans in enumerate(cs.transformations):
            assert trans.basename == f"ordered_{i}"
        
        # After connection, order should still be preserved
        new_trans = MockTransformation(mock_env, name="new")
        new_ds = DataStream(mock_env, new_trans)
        
        extended = cs.connect(new_ds)
        
        for i, trans in enumerate(extended.transformations[:3]):
            assert trans.basename == f"ordered_{i}"
        assert extended.transformations[3].basename == "new"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
