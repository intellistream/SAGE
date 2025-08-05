#!/usr/bin/envfrom sage.api.base_environment import BaseEnvironment
from sage.api.datastream import DataStream
from sage.api.transformation.source_transformation import SourceTransformation
from sage.api.transformation.batch_transformation import BatchTransformation
from sage.api.transformation.future_transformation import FutureTransformation
from sage.api.function.base_function import BaseFunction
from sage.runtime.factory.service_factory import ServiceFactory
"""
Tests for sage.core.api.base_environment module

This module provides comprehensive unit tests for the BaseEnvironment class,
following the testing organization structure outlined in the issue.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from typing import Any

from sage.api.base_environment import BaseEnvironment
from sage.api.datastream import DataStream
from sage.api.transformation.source_transformation import SourceTransformation
from sage.api.transformation.batch_transformation import BatchTransformation
from sage.api.transformation.future_transformation import FutureTransformation
from sage.api.function.base_function import BaseFunction
from sage.runtime.factory.service_factory import ServiceFactory
from sage.runtime.communication.queue_descriptor.base_queue_descriptor import BaseQueueDescriptor


class MockEnvironment(BaseEnvironment):
    """Mock implementation of BaseEnvironment for testing"""
    
    def submit(self):
        """Mock implementation of submit method"""
        return "mock_job_uuid"
    
    def get_qd(self, name: str, maxsize: int = 10000):
        """Mock implementation of get_qd method"""
        # Create a mock queue descriptor
        from unittest.mock import Mock
        mock_qd = Mock()
        mock_qd.queue_id = name
        mock_qd.maxsize = maxsize
        return mock_qd


class CustomBatchFunction(BaseFunction):
    """Custom batch function for testing"""
    
    def __init__(self, start=0, end=10, **kwargs):
        super().__init__()
        self.start = start
        self.end = end
        
    def get_data_iterator(self):
        return iter(range(self.start, self.end))
        
    def get_total_count(self):
        return self.end - self.start


class MockServiceClass:
    """Mock service class for testing service registration"""
    
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


@pytest.fixture
def mock_env():
    """Fixture providing a mock environment instance"""
    return MockEnvironment("test_env", {"test_key": "test_value"})


@pytest.fixture
def mock_logger():
    """Fixture providing a mock logger"""
    with patch('sage.core.api.base_environment.CustomLogger') as mock_logger_class:
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        yield mock_logger_instance


class TestBaseEnvironmentInit:
    """Test BaseEnvironment initialization"""
    
    @pytest.mark.unit
    def test_init_with_defaults(self):
        """Test BaseEnvironment initialization with default values"""
        env = MockEnvironment("test_env", None)
        
        assert "test_env" in env.name  # name may be modified by get_name
        assert env.config == {}
        assert env.platform == "local"
        assert env.pipeline == []
        assert env._filled_futures == {}
        assert env.service_factories == {}
        assert env.service_task_factories == {}
        assert env.env_base_dir is None
        assert env._jobmanager is None
        assert env._engine_client is None
        assert env.env_uuid is None
        assert env.console_log_level == "INFO"
    
    @pytest.mark.unit
    def test_init_with_config(self):
        """Test BaseEnvironment initialization with config"""
        config = {"key": "value", "num": 42}
        env = MockEnvironment("test_env", config, platform="remote")
        
        assert env.config == config
        assert env.platform == "remote"
    
    @pytest.mark.unit
    def test_init_with_empty_config(self):
        """Test BaseEnvironment initialization with empty config"""
        env = MockEnvironment("test_env", {})
        assert env.config == {}


class TestBaseEnvironmentConsoleLogLevel:
    """Test console log level configuration"""
    
    @pytest.mark.unit
    def test_set_console_log_level_valid(self, mock_env):
        """Test setting valid console log levels"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        
        for level in valid_levels:
            mock_env.set_console_log_level(level)
            assert mock_env.console_log_level == level.upper()
    
    @pytest.mark.unit
    def test_set_console_log_level_case_insensitive(self, mock_env):
        """Test that log level setting is case insensitive"""
        mock_env.set_console_log_level("debug")
        assert mock_env.console_log_level == "DEBUG"
        
        mock_env.set_console_log_level("Info")
        assert mock_env.console_log_level == "INFO"
    
    @pytest.mark.unit
    def test_set_console_log_level_invalid(self, mock_env):
        """Test setting invalid console log level raises ValueError"""
        with pytest.raises(ValueError, match="Invalid log level"):
            mock_env.set_console_log_level("INVALID")
    
    @pytest.mark.unit
    def test_set_console_log_level_updates_existing_logger(self, mock_env):
        """Test that setting log level updates existing logger"""
        # Create logger first
        mock_logger = Mock()
        mock_env._logger = mock_logger
        
        mock_env.set_console_log_level("DEBUG")
        
        mock_logger.update_output_level.assert_called_once_with("console", "DEBUG")


class TestBaseEnvironmentServiceRegistration:
    """Test service registration functionality"""
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.ServiceFactory')
    @patch('sage.runtime.factory.service_task_factory.ServiceTaskFactory')
    def test_register_service_local(self, mock_task_factory_class, mock_service_factory_class, mock_env, mock_logger):
        """Test service registration in local environment"""
        # Setup mocks
        mock_service_factory = Mock()
        mock_task_factory = Mock()
        mock_service_factory_class.return_value = mock_service_factory
        mock_task_factory_class.return_value = mock_task_factory
        mock_env._logger = mock_logger
        
        # Test service registration
        result = mock_env.register_service("test_service", MockServiceClass, "arg1", kwarg1="value1")
        
        # Verify ServiceFactory was created correctly
        mock_service_factory_class.assert_called_once_with(
            service_name="test_service",
            service_class=MockServiceClass,
            service_args=("arg1",),
            service_kwargs={"kwarg1": "value1"}
        )
        
        # Verify ServiceTaskFactory was created correctly
        mock_task_factory_class.assert_called_once_with(
            service_factory=mock_service_factory,
            remote=False
        )
        
        # Verify storage
        assert mock_env.service_factories["test_service"] == mock_service_factory
        assert mock_env.service_task_factories["test_service"] == mock_task_factory
        
        # Verify return value
        assert result == mock_service_factory
        
        # Verify logging
        mock_logger.info.assert_called_once_with(
            "Registered local service: test_service (MockServiceClass)"
        )
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.ServiceFactory')
    @patch('sage.runtime.factory.service_task_factory.ServiceTaskFactory')
    def test_register_service_remote(self, mock_task_factory_class, mock_service_factory_class, mock_logger):
        """Test service registration in remote environment"""
        # Create remote environment
        env = MockEnvironment("test_env", {}, platform="remote")
        env._logger = mock_logger
        
        # Setup mocks
        mock_service_factory = Mock()
        mock_task_factory = Mock()
        mock_service_factory_class.return_value = mock_service_factory
        mock_task_factory_class.return_value = mock_task_factory
        
        # Test service registration
        env.register_service("test_service", MockServiceClass)
        
        # Verify ServiceTaskFactory was created with remote=True
        mock_task_factory_class.assert_called_once_with(
            service_factory=mock_service_factory,
            remote=True
        )
        
        # Verify logging mentions remote
        mock_logger.info.assert_called_once_with(
            "Registered remote service: test_service (MockServiceClass)"
        )


class TestBaseEnvironmentKafkaSource:
    """Test Kafka source creation"""
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.KafkaSourceFunction')
    def test_from_kafka_source_basic(self, mock_kafka_function, mock_env, mock_logger):
        """Test basic Kafka source creation"""
        mock_env._logger = mock_logger
        
        result = mock_env.from_kafka_source(
            bootstrap_servers="localhost:9092",
            topic="test_topic",
            group_id="test_group"
        )
        
        # Verify result is DataStream
        assert isinstance(result, DataStream)
        
        # Verify transformation was added to pipeline
        assert len(mock_env.pipeline) == 1
        transformation = mock_env.pipeline[0]
        assert isinstance(transformation, SourceTransformation)
        
        # Verify logging
        mock_logger.info.assert_called_once_with(
            "Kafka source created for topic: test_topic, group: test_group"
        )
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.KafkaSourceFunction')
    def test_from_kafka_source_with_options(self, mock_kafka_function, mock_env):
        """Test Kafka source creation with additional options"""
        result = mock_env.from_kafka_source(
            bootstrap_servers="kafka1:9092,kafka2:9092",
            topic="events",
            group_id="sage_app",
            auto_offset_reset="earliest",
            buffer_size=20000,
            max_poll_records=1000,
            session_timeout_ms=30000,
            security_protocol="SSL"
        )
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1


class TestBaseEnvironmentDataSources:
    """Test data source creation methods"""
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.wrap_lambda')
    def test_from_source_with_function_class(self, mock_wrap_lambda, mock_env):
        """Test from_source with function class"""
        mock_function = Mock()
        
        result = mock_env.from_source(mock_function, "arg1", kwarg1="value1")
        
        # wrap_lambda should not be called for classes
        mock_wrap_lambda.assert_not_called()
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
        transformation = mock_env.pipeline[0]
        assert isinstance(transformation, SourceTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.wrap_lambda')
    def test_from_source_with_lambda(self, mock_wrap_lambda, mock_env):
        """Test from_source with lambda function"""
        lambda_func = lambda x: x * 2
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = mock_env.from_source(lambda_func)
        
        # wrap_lambda should be called for lambda functions
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'flatmap')
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.wrap_lambda')
    def test_from_collection_with_function_class(self, mock_wrap_lambda, mock_env):
        """Test from_collection with function class"""
        mock_function = Mock()
        
        result = mock_env.from_collection(mock_function)
        
        mock_wrap_lambda.assert_not_called()
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
        transformation = mock_env.pipeline[0]
        assert isinstance(transformation, BatchTransformation)
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.wrap_lambda')
    def test_from_collection_with_lambda(self, mock_wrap_lambda, mock_env):
        """Test from_collection with lambda function"""
        lambda_func = lambda x: [x, x*2]
        wrapped_func = Mock()
        mock_wrap_lambda.return_value = wrapped_func
        
        result = mock_env.from_collection(lambda_func)
        
        mock_wrap_lambda.assert_called_once_with(lambda_func, 'flatmap')
        assert isinstance(result, DataStream)


class TestBaseEnvironmentFromBatch:
    """Test from_batch method with different input types"""
    
    @pytest.mark.unit
    def test_from_batch_with_function_class(self, mock_env, mock_logger):
        """Test from_batch with custom function class"""
        mock_env._logger = mock_logger
        
        result = mock_env.from_batch(CustomBatchFunction, start=5, end=15)
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
        transformation = mock_env.pipeline[0]
        assert isinstance(transformation, BatchTransformation)
        
        mock_logger.info.assert_called_once_with(
            "Custom batch source created with CustomBatchFunction"
        )
    
    @pytest.mark.unit
    def test_from_batch_with_list(self, mock_env, mock_logger):
        """Test from_batch with list data"""
        mock_env._logger = mock_logger
        data = ["item1", "item2", "item3"]
        
        result = mock_env.from_batch(data)
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
        
        mock_logger.info.assert_called_once_with(
            "Batch collection source created with 3 items"
        )
    
    @pytest.mark.unit
    def test_from_batch_with_tuple(self, mock_env, mock_logger):
        """Test from_batch with tuple data"""
        mock_env._logger = mock_logger
        data = ("a", "b", "c", "d")
        
        result = mock_env.from_batch(data)
        
        assert isinstance(result, DataStream)
        mock_logger.info.assert_called_once_with(
            "Batch collection source created with 4 items"
        )
    
    @pytest.mark.unit
    def test_from_batch_with_range(self, mock_env, mock_logger):
        """Test from_batch with range object"""
        mock_env._logger = mock_logger
        data = range(10)
        
        result = mock_env.from_batch(data)
        
        assert isinstance(result, DataStream)
        mock_logger.info.assert_called_once_with(
            "Batch iterable source created from range with 10 items"
        )
    
    @pytest.mark.unit
    def test_from_batch_with_set(self, mock_env, mock_logger):
        """Test from_batch with set data"""
        mock_env._logger = mock_logger
        data = {1, 2, 3, 4, 5}
        
        result = mock_env.from_batch(data)
        
        assert isinstance(result, DataStream)
        mock_logger.info.assert_called_once_with(
            "Batch iterable source created from set with 5 items"
        )
    
    @pytest.mark.unit
    def test_from_batch_with_string(self, mock_env, mock_logger):
        """Test from_batch with string (character iteration)"""
        mock_env._logger = mock_logger
        data = "hello"
        
        result = mock_env.from_batch(data)
        
        assert isinstance(result, DataStream)
        mock_logger.info.assert_called_once_with(
            "Batch iterable source created from str with 5 items"
        )
    
    @pytest.mark.unit
    def test_from_batch_with_invalid_type(self, mock_env):
        """Test from_batch with non-iterable object raises TypeError"""
        invalid_data = 42  # int is not iterable
        
        with pytest.raises(TypeError, match="Unsupported source type"):
            mock_env.from_batch(invalid_data)


class TestBaseEnvironmentFromFuture:
    """Test future stream creation"""
    
    @pytest.mark.unit
    def test_from_future(self, mock_env):
        """Test creating future stream"""
        result = mock_env.from_future("feedback_loop")
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
        transformation = mock_env.pipeline[0]
        assert isinstance(transformation, FutureTransformation)
        assert transformation.future_name == "feedback_loop"


class TestBaseEnvironmentProperties:
    """Test BaseEnvironment properties"""
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.CustomLogger')
    def test_logger_property_lazy_creation(self, mock_logger_class, mock_env):
        """Test logger property creates logger lazily"""
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        # First access should create logger
        logger = mock_env.logger
        assert logger == mock_logger_instance
        mock_logger_class.assert_called_once()
        
        # Second access should return same logger
        logger2 = mock_env.logger
        assert logger2 == mock_logger_instance
        # Should not create another logger
        assert mock_logger_class.call_count == 1
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.JobManagerClient')
    def test_client_property_lazy_creation(self, mock_client_class, mock_env):
        """Test client property creates client lazily"""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        # First access should create client
        client = mock_env.client
        assert client == mock_client_instance
        mock_client_class.assert_called_once_with(host="127.0.0.1", port=19000)
        
        # Second access should return same client
        client2 = mock_env.client
        assert client2 == mock_client_instance
        assert mock_client_class.call_count == 1
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.JobManagerClient')
    def test_client_property_with_config(self, mock_client_class):
        """Test client property uses config values"""
        env = MockEnvironment("test_env", {
            "engine_host": "remote.host.com",
            "engine_port": 8080
        })
        
        client = env.client
        mock_client_class.assert_called_once_with(host="remote.host.com", port=8080)


class TestBaseEnvironmentLoggingSetup:
    """Test logging system setup"""
    
    @pytest.mark.unit
    @patch('sage.core.api.base_environment.CustomLogger')
    @patch('sage.core.api.base_environment.Path')
    @patch('sage.jobmanager.utils.name_server.get_name')
    def test_setup_logging_system(self, mock_get_name, mock_path_class, mock_logger_class, mock_env):
        """Test logging system setup"""
        mock_get_name.return_value = "unique_test_env"
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        mock_path_instance = Mock()
        mock_path_class.return_value = mock_path_instance
        
        # Mock datetime
        with patch('sage.core.api.base_environment.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "20240101_120000"
            mock_datetime.now.return_value = mock_now
            
            mock_env.setup_logging_system("/base/log/dir")
        
        # Verify name was set
        assert mock_env.name == "unique_test_env"
        
        # Verify session info was set
        assert mock_env.session_timestamp == mock_now
        assert mock_env.session_id == "20240101_120000"
        
        # Verify env_base_dir was set
        expected_dir = "/base/log/dir/env_unique_test_env_20240101_120000"
        assert mock_env.env_base_dir == expected_dir
        
        # Verify directory creation
        mock_path_class.assert_called_once_with(expected_dir)
        mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        
        # Verify logger creation
        expected_log_configs = [
            ("console", "INFO"),  # Uses default console log level
            (os.path.join(expected_dir, "Environment.log"), "DEBUG"),
            (os.path.join(expected_dir, "Error.log"), "ERROR")
        ]
        mock_logger_class.assert_called_once_with(
            expected_log_configs,
            name="Environment_unique_test_env"
        )
        assert mock_env._logger == mock_logger_instance


class TestBaseEnvironmentAuxiliaryMethods:
    """Test auxiliary methods"""
    
    @pytest.mark.unit
    def test_append_method(self, mock_env):
        """Test _append method adds transformation and returns DataStream"""
        mock_transformation = Mock(spec=SourceTransformation)
        
        result = mock_env._append(mock_transformation)
        
        assert mock_transformation in mock_env.pipeline
        assert isinstance(result, DataStream)
        assert result.transformation == mock_transformation
    
    @pytest.mark.unit
    @patch('sage.core.function.simple_batch_function.SimpleBatchIteratorFunction')
    def test_from_batch_collection_internal(self, mock_batch_function, mock_env, mock_logger):
        """Test internal _from_batch_collection method"""
        mock_env._logger = mock_logger
        data = [1, 2, 3]
        
        result = mock_env._from_batch_collection(data, custom_param="value")
        
        assert isinstance(result, DataStream)
        assert len(mock_env.pipeline) == 1
        transformation = mock_env.pipeline[0]
        assert isinstance(transformation, BatchTransformation)
        
        mock_logger.info.assert_called_once_with(
            "Batch collection source created with 3 items"
        )
    
    @pytest.mark.unit
    @patch('sage.core.function.simple_batch_function.IterableBatchIteratorFunction')
    def test_from_batch_iterable_internal(self, mock_batch_function, mock_env, mock_logger):
        """Test internal _from_batch_iterable method"""
        mock_env._logger = mock_logger
        data = range(5)
        
        result = mock_env._from_batch_iterable(data, custom_param="value")
        
        assert isinstance(result, DataStream)
        mock_logger.info.assert_called_once_with(
            "Batch iterable source created from range with 5 items"
        )
    
    @pytest.mark.unit
    @patch('sage.core.function.simple_batch_function.IterableBatchIteratorFunction')
    def test_from_batch_iterable_without_len(self, mock_batch_function, mock_env, mock_logger):
        """Test _from_batch_iterable with object that has no len()"""
        mock_env._logger = mock_logger
        
        # Create an iterable without __len__
        class CustomIterable:
            def __iter__(self):
                return iter([1, 2, 3])
        
        data = CustomIterable()
        
        result = mock_env._from_batch_iterable(data)
        
        assert isinstance(result, DataStream)
        mock_logger.info.assert_called_once_with(
            "Batch iterable source created from CustomIterable"
        )


class TestBaseEnvironmentEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_empty_config_handling(self):
        """Test handling of None and empty config"""
        env1 = MockEnvironment("test", None)
        assert env1.config == {}
        
        env2 = MockEnvironment("test", {})
        assert env2.config == {}
    
    @pytest.mark.unit
    def test_state_exclude_attribute(self):
        """Test that __state_exclude__ is properly defined"""
        expected_excludes = ["_engine_client", "client", "jobmanager"]
        assert hasattr(BaseEnvironment, '__state_exclude__')
        assert BaseEnvironment.__state_exclude__ == expected_excludes
    
    @pytest.mark.unit
    def test_abstract_methods_exist(self):
        """Test that abstract methods are properly defined"""
        # These should raise TypeError when trying to instantiate BaseEnvironment directly
        with pytest.raises(TypeError):
            BaseEnvironment("test", {})


class TestBaseEnvironmentIntegration:
    """Integration tests for BaseEnvironment"""
    
    @pytest.mark.integration
    def test_full_pipeline_creation(self, mock_env):
        """Test creating a complete pipeline with multiple transformations"""
        # Create various data sources
        future_stream = mock_env.from_future("test_future")
        batch_stream = mock_env.from_batch([1, 2, 3, 4, 5])
        
        # Verify pipeline state
        assert len(mock_env.pipeline) == 2
        
        # Verify transformation types
        transformations = mock_env.pipeline
        future_trans = transformations[0]
        batch_trans = transformations[1]
        
        assert isinstance(future_trans, FutureTransformation)
        assert isinstance(batch_trans, BatchTransformation)
        assert future_trans.future_name == "test_future"
    
    @pytest.mark.integration
    def test_service_registration_workflow(self, mock_env):
        """Test complete service registration workflow"""
        # Register multiple services
        service1 = mock_env.register_service("service1", MockServiceClass, "arg1")
        service2 = mock_env.register_service("service2", MockServiceClass, key="value")
        
        # Verify both services are registered
        assert "service1" in mock_env.service_factories
        assert "service2" in mock_env.service_factories
        assert "service1" in mock_env.service_task_factories
        assert "service2" in mock_env.service_task_factories
        
        # Verify return values
        assert service1 == mock_env.service_factories["service1"]
        assert service2 == mock_env.service_factories["service2"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
