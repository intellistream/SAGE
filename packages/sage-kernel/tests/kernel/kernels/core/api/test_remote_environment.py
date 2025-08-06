#!/usr/bin/env python3
"""
Tests for sage.kernel.api.remote_environment module

This module provides comprehensive unit tests for the RemoteEnvironment class,
following the testing organization structure outlined in the issue.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from sage.kernel.api.remote_environment import RemoteEnvironment
from sage.kernel.kernels.jobmanager.jobmanager_client import JobManagerClient


@pytest.fixture
def remote_env():
    """Fixture providing a RemoteEnvironment instance"""
    return RemoteEnvironment("test_remote_env", {"test_key": "test_value"})


@pytest.fixture
def mock_client():
    """Fixture providing a mock JobManagerClient"""
    mock_client = Mock(spec=JobManagerClient)
    mock_client.submit_job.return_value = {
        "status": "success",
        "job_uuid": "test_job_uuid"
    }
    return mock_client


class TestRemoteEnvironmentInit:
    """Test RemoteEnvironment initialization"""
    
    @pytest.mark.unit
    def test_init_with_defaults(self):
        """Test RemoteEnvironment initialization with default values"""
        env = RemoteEnvironment()
        
        assert "remote_environment" in env.name
        assert env.config["engine_host"] == "127.0.0.1"
        assert env.config["engine_port"] == 19001
        assert env.platform == "remote"
        assert env.daemon_host == "127.0.0.1"
        assert env.daemon_port == 19001
        assert env._engine_client is None
    
    @pytest.mark.unit
    def test_init_with_custom_params(self):
        """Test RemoteEnvironment initialization with custom parameters"""
        config = {"custom_key": "custom_value"}
        env = RemoteEnvironment(
            name="my_remote_env",
            config=config,
            host="remote.host.com",
            port=8080
        )
        
        assert "my_remote_env" in env.name
        assert env.config["custom_key"] == "custom_value"
        assert env.config["engine_host"] == "remote.host.com"
        assert env.config["engine_port"] == 8080
        assert env.platform == "remote"
        assert env.daemon_host == "remote.host.com"
        assert env.daemon_port == 8080
    
    @pytest.mark.unit
    def test_init_with_none_config(self):
        """Test RemoteEnvironment initialization with None config"""
        env = RemoteEnvironment("test_env", None, "example.com", 9000)
        
        assert env.config["engine_host"] == "example.com"
        assert env.config["engine_port"] == 9000
    
    @pytest.mark.unit
    def test_state_exclude_attributes(self):
        """Test that __state_exclude__ includes remote-specific attributes"""
        expected_excludes = [
            'logger', '_logger',
            '_engine_client',
            '_jobmanager'
        ]
        assert RemoteEnvironment.__state_exclude__ == expected_excludes


class TestRemoteEnvironmentClient:
    """Test JobManager client functionality"""
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.JobManagerClient')
    def test_client_property_lazy_creation(self, mock_client_class, remote_env):
        """Test client property creates client lazily"""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        # First access should create client
        client = remote_env.client
        assert client == mock_client_instance
        mock_client_class.assert_called_once_with(
            host="127.0.0.1",
            port=19001
        )
        
        # Second access should return same client
        client2 = remote_env.client
        assert client2 == mock_client_instance
        # Should not create another client
        assert mock_client_class.call_count == 1
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.JobManagerClient')
    def test_client_property_with_custom_host_port(self, mock_client_class):
        """Test client property uses custom host and port"""
        env = RemoteEnvironment("test", {}, host="custom.host.com", port=8888)
        
        client = env.client
        mock_client_class.assert_called_once_with(
            host="custom.host.com",
            port=8888
        )


class TestRemoteEnvironmentSubmit:
    """Test job submission functionality"""
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.serialize_object')
    @patch('sage.kernel.api.remote_environment.trim_object_for_ray')
    def test_submit_successful(self, mock_trim, mock_serialize, remote_env, mock_client):
        """Test successful job submission"""
        # Setup mocks
        trimmed_env = {"trimmed": "environment"}
        serialized_data = b"serialized_data"
        mock_trim.return_value = trimmed_env
        mock_serialize.return_value = serialized_data
        remote_env._engine_client = mock_client
        
        # Submit job
        result = remote_env.submit()
        
        # Verify trimming and serialization
        mock_trim.assert_called_once_with(remote_env)
        mock_serialize.assert_called_once_with(trimmed_env)
        
        # Verify client submission
        mock_client.submit_job.assert_called_once_with(serialized_data)
        
        # Verify result
        assert result == "test_job_uuid"
        assert remote_env.env_uuid == "test_job_uuid"
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.serialize_object')
    @patch('sage.kernel.api.remote_environment.trim_object_for_ray')
    def test_submit_failure_response(self, mock_trim, mock_serialize, remote_env, mock_client):
        """Test job submission with failure response"""
        # Setup mocks
        mock_trim.return_value = {}
        mock_serialize.return_value = b"data"
        mock_client.submit_job.return_value = {
            "status": "error",
            "message": "Invalid environment"
        }
        remote_env._engine_client = mock_client
        
        # Submit should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to submit environment: Invalid environment"):
            remote_env.submit()
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.serialize_object')
    @patch('sage.kernel.api.remote_environment.trim_object_for_ray')
    def test_submit_success_without_uuid(self, mock_trim, mock_serialize, remote_env, mock_client):
        """Test job submission success response without UUID"""
        # Setup mocks
        mock_trim.return_value = {}
        mock_serialize.return_value = b"data"
        mock_client.submit_job.return_value = {
            "status": "success"
            # Missing job_uuid
        }
        remote_env._engine_client = mock_client
        
        # Submit should raise RuntimeError
        with pytest.raises(RuntimeError, match="JobManager returned success but no job UUID"):
            remote_env.submit()
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.serialize_object')
    @patch('sage.kernel.api.remote_environment.trim_object_for_ray')
    def test_submit_serialization_error(self, mock_trim, mock_serialize, remote_env):
        """Test job submission with serialization error"""
        # Setup mocks
        mock_trim.return_value = {}
        mock_serialize.side_effect = Exception("Serialization failed")
        
        # Submit should raise the serialization exception
        with pytest.raises(Exception, match="Serialization failed"):
            remote_env.submit()
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.serialize_object')
    @patch('sage.kernel.api.remote_environment.trim_object_for_ray')
    def test_submit_client_error(self, mock_trim, mock_serialize, remote_env, mock_client):
        """Test job submission with client communication error"""
        # Setup mocks
        mock_trim.return_value = {}
        mock_serialize.return_value = b"data"
        mock_client.submit_job.side_effect = ConnectionError("Connection failed")
        remote_env._engine_client = mock_client
        
        # Submit should re-raise the connection error
        with pytest.raises(ConnectionError, match="Connection failed"):
            remote_env.submit()


class TestRemoteEnvironmentGetQd:
    """Test queue descriptor functionality"""
    
    @pytest.mark.unit
    def test_get_qd_default_params(self, remote_env):
        """Test get_qd with default parameters"""
        qd = remote_env.get_qd("test_queue")
        
        # Test the basic properties instead of specific type
        assert hasattr(qd, 'queue_id')
        assert hasattr(qd, 'maxsize')
        assert qd.queue_id == "test_queue"
        assert qd.maxsize == 10000
    
    @pytest.mark.unit
    def test_get_qd_custom_params(self, remote_env):
        """Test get_qd with custom parameters"""
        qd = remote_env.get_qd("custom_queue", maxsize=5000)
        
        assert hasattr(qd, 'queue_id')
        assert hasattr(qd, 'maxsize')
        assert qd.queue_id == "custom_queue"
        assert qd.maxsize == 5000
    
    @pytest.mark.unit
    def test_get_qd_different_names(self, remote_env):
        """Test get_qd creates different descriptors for different names"""
        qd1 = remote_env.get_qd("queue1")
        qd2 = remote_env.get_qd("queue2")
        
        assert qd1.queue_id != qd2.queue_id
        assert qd1.queue_id == "queue1"
        assert qd2.queue_id == "queue2"


class TestRemoteEnvironmentInheritance:
    """Test RemoteEnvironment inheritance from BaseEnvironment"""
    
    @pytest.mark.unit
    def test_inherits_from_base_environment(self):
        """Test that RemoteEnvironment properly inherits from BaseEnvironment"""
        from sage.kernel.api.base_environment import BaseEnvironment
        assert issubclass(RemoteEnvironment, BaseEnvironment)
    
    @pytest.mark.unit
    def test_platform_is_remote(self, remote_env):
        """Test that platform is correctly set to 'remote'"""
        assert remote_env.platform == "remote"
    
    @pytest.mark.unit
    def test_inherited_methods_available(self, remote_env):
        """Test that inherited methods from BaseEnvironment are available"""
        # Test some key inherited methods exist
        assert hasattr(remote_env, 'from_source')
        assert hasattr(remote_env, 'from_batch')
        assert hasattr(remote_env, 'from_future')
        assert hasattr(remote_env, 'from_kafka_source')
        assert hasattr(remote_env, 'register_service')
        assert hasattr(remote_env, 'set_console_log_level')


class TestRemoteEnvironmentLogging:
    """Test logging functionality"""
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.logger')
    def test_init_logging(self, mock_module_logger):
        """Test that initialization logs are created"""
        env = RemoteEnvironment("test_env", {}, "example.com", 9000)
        
        mock_module_logger.info.assert_called_once_with(
            "RemoteEnvironment 'test_env' initialized for example.com:9000"
        )
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.logger')
    @patch('sage.kernel.api.remote_environment.JobManagerClient')
    def test_client_creation_logging(self, mock_client_class, mock_module_logger, remote_env):
        """Test that client creation is logged"""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        # Access client property to trigger creation
        client = remote_env.client
        
        mock_module_logger.debug.assert_called_once_with(
            "Creating JobManager client for 127.0.0.1:19001"
        )
    
    @pytest.mark.unit
    @patch('sage.kernel.api.remote_environment.logger')
    @patch('sage.kernel.api.remote_environment.serialize_object')
    @patch('sage.kernel.api.remote_environment.trim_object_for_ray')
    def test_submit_logging(self, mock_trim, mock_serialize, mock_module_logger, remote_env, mock_client):
        """Test that submit process is properly logged"""
        # Setup mocks
        mock_trim.return_value = {}
        mock_serialize.return_value = b"data"
        remote_env._engine_client = mock_client
        
        # Submit job
        result = remote_env.submit()
        
        # Verify logging calls
        expected_calls = [
            ("Submitting environment 'test_remote_env' to remote JobManager",),
            ("Trimming environment for serialization",),
            ("Serializing environment with dill",),
            ("Submitting serialized environment to JobManager",),
            ("Environment submitted successfully with UUID: test_job_uuid",)
        ]
        
        # Check that info/debug logs were called (order may vary)
        info_calls = [call.args[0] for call in mock_module_logger.info.call_args_list]
        debug_calls = [call.args[0] for call in mock_module_logger.debug.call_args_list]
        
        assert "Submitting environment 'test_remote_env' to remote JobManager" in info_calls
        assert "Environment submitted successfully with UUID: test_job_uuid" in info_calls
        assert "Trimming environment for serialization" in debug_calls
        assert "Serializing environment with dill" in debug_calls
        assert "Submitting serialized environment to JobManager" in debug_calls


class TestRemoteEnvironmentIntegration:
    """Integration tests for RemoteEnvironment"""
    
    @pytest.mark.integration
    @patch('sage.kernel.api.remote_environment.serialize_object')
    @patch('sage.kernel.api.remote_environment.trim_object_for_ray')
    @patch('sage.kernel.api.remote_environment.JobManagerClient')
    def test_full_workflow(self, mock_client_class, mock_trim, mock_serialize):
        """Test full workflow: create -> add pipelines -> submit"""
        # Setup mocks
        mock_client_instance = Mock()
        mock_client_instance.submit_job.return_value = {
            "status": "success",
            "job_uuid": "integration_test_uuid"
        }
        mock_client_class.return_value = mock_client_instance
        mock_trim.return_value = {"environment": "data"}
        mock_serialize.return_value = b"serialized_environment"
        
        # Create environment
        env = RemoteEnvironment("integration_test", {}, "test.host.com", 8080)
        
        # Add some pipeline elements
        from sage.kernel.api.datastream import DataStream
        batch_stream = env.from_batch([1, 2, 3])
        assert isinstance(batch_stream, DataStream)
        assert len(env.pipeline) == 1
        
        # Submit job
        result = env.submit()
        
        # Verify client creation
        mock_client_class.assert_called_once_with(host="test.host.com", port=8080)
        
        # Verify submission process
        mock_trim.assert_called_once_with(env)
        mock_serialize.assert_called_once_with({"environment": "data"})
        mock_client_instance.submit_job.assert_called_once_with(b"serialized_environment")
        
        # Verify result
        assert result == "integration_test_uuid"
        assert env.env_uuid == "integration_test_uuid"
    
    @pytest.mark.integration
    def test_multiple_queue_descriptors(self, remote_env):
        """Test creating multiple queue descriptors"""
        queues = []
        for i in range(5):
            qd = remote_env.get_qd(f"queue_{i}", maxsize=1000 * (i + 1))
            queues.append(qd)
        
        # Verify all queues are unique and properly configured
        for i, qd in enumerate(queues):
            assert qd.queue_id == f"queue_{i}"
            assert qd.maxsize == 1000 * (i + 1)
            # Test basic queue descriptor interface
            assert hasattr(qd, 'queue_id')
            assert hasattr(qd, 'maxsize')
        
        # Verify they are all different objects
        for i in range(len(queues)):
            for j in range(i + 1, len(queues)):
                assert queues[i] is not queues[j]
                assert queues[i].queue_id != queues[j].queue_id


class TestRemoteEnvironmentEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_config_merging(self):
        """Test that config is properly merged with connection parameters"""
        initial_config = {"existing_key": "existing_value", "engine_host": "old_host"}
        env = RemoteEnvironment("test", initial_config, "new_host", 9999)
        
        # Verify config merging
        assert env.config["existing_key"] == "existing_value"
        assert env.config["engine_host"] == "new_host"  # Should be overwritten
        assert env.config["engine_port"] == 9999
    
    @pytest.mark.unit
    def test_multiple_submit_calls(self, remote_env, mock_client):
        """Test multiple submit calls behavior"""
        with patch('sage.kernel.api.remote_environment.serialize_object') as mock_serialize, \
             patch('sage.kernel.api.remote_environment.trim_object_for_ray') as mock_trim:
            
            mock_trim.return_value = {}
            mock_serialize.return_value = b"data"
            remote_env._engine_client = mock_client
            
            # First submit
            uuid1 = remote_env.submit()
            assert uuid1 == "test_job_uuid"
            
            # Second submit (should work and potentially overwrite env_uuid)
            uuid2 = remote_env.submit()
            assert uuid2 == "test_job_uuid"
            assert remote_env.env_uuid == "test_job_uuid"
            
            # Verify both calls went through
            assert mock_client.submit_job.call_count == 2
    
    @pytest.mark.unit
    def test_attributes_exist_after_init(self, remote_env):
        """Test that all expected attributes exist after initialization"""
        # Inherited attributes from BaseEnvironment
        assert hasattr(remote_env, 'name')
        assert hasattr(remote_env, 'config')
        assert hasattr(remote_env, 'platform')
        assert hasattr(remote_env, 'pipeline')
        assert hasattr(remote_env, 'service_factories')
        assert hasattr(remote_env, 'service_task_factories')
        
        # RemoteEnvironment specific attributes
        assert hasattr(remote_env, 'daemon_host')
        assert hasattr(remote_env, 'daemon_port')
        assert hasattr(remote_env, '_engine_client')
    
    @pytest.mark.unit
    def test_client_property_thread_safety(self, remote_env):
        """Test that client property is thread-safe (basic check)"""
        with patch('sage.kernel.api.remote_environment.JobManagerClient') as mock_client_class:
            mock_client_instance = Mock()
            mock_client_class.return_value = mock_client_instance
            
            # Multiple accesses should return same instance
            client1 = remote_env.client
            client2 = remote_env.client
            client3 = remote_env.client
            
            assert client1 is client2 is client3
            # Should only create client once
            mock_client_class.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
