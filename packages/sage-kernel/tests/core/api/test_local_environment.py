#!/usr/bin/env python3
"""
Tests for sage.core.api.local_environment module

This module provides comprehensive unit tests for the LocalEnvironment class,
following the testing organization structure outlined in the issue.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.datastream import DataStream


@pytest.fixture
def local_env():
    """Fixture providing a LocalEnvironment instance"""
    return LocalEnvironment("test_local_env", {"test_key": "test_value"})


@pytest.fixture
def mock_jobmanager():
    """Fixture providing a mock JobManager"""
    mock_jm = Mock()
    mock_jm.submit_job.return_value = "test_job_uuid"
    mock_jm.pause_job.return_value = {"status": "success", "message": "Job paused"}
    return mock_jm


class TestLocalEnvironmentInit:
    """Test LocalEnvironment initialization"""
    
    @pytest.mark.unit
    def test_init_with_defaults(self):
        """Test LocalEnvironment initialization with default values"""
        env = LocalEnvironment()
        
        assert "localenvironment" in env.name
        assert env.config == {}
        assert env.platform == "local"
        assert env._engine_client is None
    
    @pytest.mark.unit
    def test_init_with_custom_name_and_config(self):
        """Test LocalEnvironment initialization with custom parameters"""
        config = {"key": "value", "timeout": 30}
        env = LocalEnvironment("my_local_env", config)
        
        assert "my_local_env" in env.name
        assert env.config == config
        assert env.platform == "local"
    
    @pytest.mark.unit
    def test_init_with_none_config(self):
        """Test LocalEnvironment initialization with None config"""
        env = LocalEnvironment("test_env", None)
        assert env.config == {}


class TestLocalEnvironmentJobManager:
    """Test JobManager integration"""
    
    @pytest.mark.unit
    @patch('sage.core.api.local_environment.JobManager')
    def test_jobmanager_property_lazy_creation(self, mock_jobmanager_class, local_env):
        """Test jobmanager property creates JobManager lazily"""
        mock_jobmanager_instance = Mock()
        mock_jobmanager_class.return_value = mock_jobmanager_instance
        
        # First access should create JobManager
        jobmanager = local_env.jobmanager
        assert jobmanager == mock_jobmanager_instance
        mock_jobmanager_class.assert_called_once()
        
        # Second access should return same JobManager
        jobmanager2 = local_env.jobmanager
        assert jobmanager2 == mock_jobmanager_instance
        # Should not create another JobManager
        assert mock_jobmanager_class.call_count == 1
    
    @pytest.mark.unit
    @patch('sage.core.api.local_environment.JobManager')
    def test_jobmanager_property_singleton(self, mock_jobmanager_class, local_env):
        """Test jobmanager property gets singleton instance"""
        mock_jobmanager_instance = Mock()
        mock_jobmanager_class.return_value = mock_jobmanager_instance
        
        jobmanager = local_env.jobmanager
        
        # Verify JobManager() was called (singleton pattern)
        mock_jobmanager_class.assert_called_once_with()
        assert local_env._jobmanager == mock_jobmanager_instance


class TestLocalEnvironmentSubmit:
    """Test job submission functionality"""
    
    @pytest.mark.unit
    @patch('sage.core.api.local_environment.JobManager')
    def test_submit_job(self, mock_jobmanager_class, local_env):
        """Test submitting job to local JobManager"""
        mock_jobmanager_instance = Mock()
        mock_jobmanager_instance.submit_job.return_value = "test_job_uuid"
        mock_jobmanager_class.return_value = mock_jobmanager_instance
        
        # Submit job
        local_env.submit()
        
        # Verify JobManager.submit_job was called with environment
        mock_jobmanager_instance.submit_job.assert_called_once_with(local_env)
    
    @pytest.mark.unit
    def test_submit_returns_none(self, local_env):
        """Test that submit method returns None (fire-and-forget)"""
        with patch.object(local_env, 'jobmanager') as mock_jm:
            mock_jm.submit_job.return_value = "test_uuid"
            
            result = local_env.submit()
            assert result is None


class TestLocalEnvironmentStop:
    """Test pipeline stopping functionality"""
    
    @pytest.mark.unit
    def test_stop_without_env_uuid(self, local_env):
        """Test stopping when environment not submitted"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = None
        
        local_env.stop()
        
        mock_logger.warning.assert_called_once_with(
            "Environment not submitted, nothing to stop"
        )
    
    @pytest.mark.unit
    def test_stop_successful(self, local_env, mock_jobmanager):
        """Test successful pipeline stop"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = "test_uuid"
        local_env._jobmanager = mock_jobmanager
        local_env.is_running = True
        
        local_env.stop()
        
        mock_jobmanager.pause_job.assert_called_once_with("test_uuid")
        mock_logger.info.assert_any_call("Stopping pipeline...")
        mock_logger.info.assert_any_call("Pipeline stopped successfully")
        assert local_env.is_running is False
    
    @pytest.mark.unit
    def test_stop_failure_response(self, local_env, mock_jobmanager):
        """Test stop with failure response from JobManager"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = "test_uuid"
        local_env._jobmanager = mock_jobmanager
        
        # Mock failure response
        mock_jobmanager.pause_job.return_value = {
            "status": "error",
            "message": "Job not found"
        }
        
        local_env.stop()
        
        mock_logger.warning.assert_called_once_with(
            "Failed to stop pipeline: Job not found"
        )
    
    @pytest.mark.unit
    def test_stop_exception_handling(self, local_env):
        """Test stop with exception from JobManager"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = "test_uuid"
        
        # Mock JobManager that raises exception
        mock_jobmanager = Mock()
        mock_jobmanager.pause_job.side_effect = Exception("Connection error")
        local_env._jobmanager = mock_jobmanager
        
        local_env.stop()
        
        mock_logger.error.assert_called_once_with(
            "Error stopping pipeline: Connection error"
        )


class TestLocalEnvironmentClose:
    """Test environment closing functionality"""
    
    @pytest.mark.unit
    def test_close_without_env_uuid(self, local_env):
        """Test closing when environment not submitted"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = None
        
        local_env.close()
        
        mock_logger.warning.assert_called_once_with(
            "Environment not submitted, nothing to close"
        )
    
    @pytest.mark.unit
    def test_close_successful(self, local_env, mock_jobmanager):
        """Test successful environment close"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = "test_uuid"
        local_env._jobmanager = mock_jobmanager
        local_env.is_running = True
        local_env.pipeline = [Mock(), Mock()]  # Add some transformations
        
        local_env.close()
        
        mock_jobmanager.pause_job.assert_called_once_with("test_uuid")
        mock_logger.info.assert_any_call("Closing environment...")
        mock_logger.info.assert_any_call("Environment closed successfully")
        
        # Verify cleanup
        assert local_env.is_running is False
        assert local_env.env_uuid is None
        assert len(local_env.pipeline) == 0
    
    @pytest.mark.unit
    def test_close_failure_response(self, local_env, mock_jobmanager):
        """Test close with failure response from JobManager"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = "test_uuid"
        local_env._jobmanager = mock_jobmanager
        local_env.is_running = True
        
        # Mock failure response
        mock_jobmanager.pause_job.return_value = {
            "status": "error",
            "message": "Failed to pause"
        }
        
        local_env.close()
        
        mock_logger.warning.assert_called_once_with(
            "Failed to close environment: Failed to pause"
        )
        
        # Verify cleanup still happens
        assert local_env.is_running is False
        assert local_env.env_uuid is None
    
    @pytest.mark.unit
    def test_close_exception_handling(self, local_env):
        """Test close with exception from JobManager"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = "test_uuid"
        local_env.is_running = True
        local_env.pipeline = [Mock()]
        
        # Mock JobManager that raises exception
        mock_jobmanager = Mock()
        mock_jobmanager.pause_job.side_effect = Exception("Network error")
        local_env._jobmanager = mock_jobmanager
        
        local_env.close()
        
        mock_logger.error.assert_called_once_with(
            "Error closing environment: Network error"
        )
        
        # Verify cleanup still happens in finally block
        assert local_env.is_running is False
        assert local_env.env_uuid is None
        assert len(local_env.pipeline) == 0


class TestLocalEnvironmentGetQd:
    """Test queue descriptor functionality"""
    
    @pytest.mark.unit
    def test_get_qd_default_params(self, local_env):
        """Test get_qd with default parameters"""
        qd = local_env.get_qd("test_queue")
        
        # Test the basic properties instead of specific type
        assert hasattr(qd, 'queue_id')
        assert hasattr(qd, 'maxsize')
        assert qd.queue_id == "test_queue"
        assert qd.maxsize == 10000
    
    @pytest.mark.unit
    def test_get_qd_custom_params(self, local_env):
        """Test get_qd with custom parameters"""
        qd = local_env.get_qd("custom_queue", maxsize=5000)
        
        assert hasattr(qd, 'queue_id')
        assert hasattr(qd, 'maxsize')
        assert qd.queue_id == "custom_queue"
        assert qd.maxsize == 5000
    
    @pytest.mark.unit
    def test_get_qd_different_names(self, local_env):
        """Test get_qd creates different descriptors for different names"""
        qd1 = local_env.get_qd("queue1")
        qd2 = local_env.get_qd("queue2")
        
        assert qd1.queue_id != qd2.queue_id
        assert qd1.queue_id == "queue1"
        assert qd2.queue_id == "queue2"


class TestLocalEnvironmentInheritance:
    """Test LocalEnvironment inheritance from BaseEnvironment"""
    
    @pytest.mark.unit
    def test_inherits_from_base_environment(self):
        """Test that LocalEnvironment properly inherits from BaseEnvironment"""
        from sage.core.api.base_environment import BaseEnvironment
        assert issubclass(LocalEnvironment, BaseEnvironment)
    
    @pytest.mark.unit
    def test_platform_is_local(self, local_env):
        """Test that platform is correctly set to 'local'"""
        assert local_env.platform == "local"
    
    @pytest.mark.unit
    def test_inherited_methods_available(self, local_env):
        """Test that inherited methods from BaseEnvironment are available"""
        # Test some key inherited methods exist
        assert hasattr(local_env, 'from_source')
        assert hasattr(local_env, 'from_batch')
        assert hasattr(local_env, 'from_future')
        assert hasattr(local_env, 'from_kafka_source')
        assert hasattr(local_env, 'register_service')
        assert hasattr(local_env, 'set_console_log_level')
    
    @pytest.mark.unit
    def test_no_engine_client_in_local(self, local_env):
        """Test that LocalEnvironment doesn't use engine client"""
        assert local_env._engine_client is None


class TestLocalEnvironmentIntegration:
    """Integration tests for LocalEnvironment"""
    
    @pytest.mark.integration
    @patch('sage.core.api.local_environment.JobManager')
    def test_full_workflow(self, mock_jobmanager_class):
        """Test full workflow: create -> add pipelines -> submit -> stop -> close"""
        mock_jobmanager_instance = Mock()
        mock_jobmanager_instance.submit_job.return_value = "test_uuid"
        mock_jobmanager_instance.pause_job.return_value = {"status": "success"}
        mock_jobmanager_class.return_value = mock_jobmanager_instance
        
        # Create environment
        env = LocalEnvironment("integration_test")
        
        # Add some pipeline elements
        batch_stream = env.from_batch([1, 2, 3])
        assert isinstance(batch_stream, DataStream)
        assert len(env.pipeline) == 1
        
        # Submit job
        env.submit()
        mock_jobmanager_instance.submit_job.assert_called_once_with(env)
        
        # Set env_uuid (normally done by JobManager)
        env.env_uuid = "test_uuid"
        env.is_running = True
        
        # Stop pipeline
        env.stop()
        mock_jobmanager_instance.pause_job.assert_called_with("test_uuid")
        
        # Close environment
        env.close()
        assert env.env_uuid is None
        assert env.is_running is False
        assert len(env.pipeline) == 0
    
    @pytest.mark.integration
    def test_multiple_queue_descriptors(self, local_env):
        """Test creating multiple queue descriptors"""
        queues = []
        for i in range(5):
            qd = local_env.get_qd(f"queue_{i}", maxsize=1000 * (i + 1))
            queues.append(qd)
        
        # Verify all queues are unique and properly configured
        for i, qd in enumerate(queues):
            assert qd.queue_id == f"queue_{i}"
            assert qd.maxsize == 1000 * (i + 1)
        
        # Verify they are all different objects
        for i in range(len(queues)):
            for j in range(i + 1, len(queues)):
                assert queues[i] is not queues[j]
                assert queues[i].queue_id != queues[j].queue_id


class TestLocalEnvironmentEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_stop_close_without_logger(self, local_env):
        """Test stop/close methods work even without logger initialized"""
        local_env.env_uuid = None
        
        # Should not raise exception even without logger
        local_env.stop()
        local_env.close()
    
    @pytest.mark.unit
    def test_multiple_close_calls(self, local_env):
        """Test that multiple close calls are handled gracefully"""
        mock_logger = Mock()
        local_env._logger = mock_logger
        local_env.env_uuid = None
        
        # Multiple close calls should not cause issues
        local_env.close()
        local_env.close()
        local_env.close()
        
        # Should log warning for each call
        assert mock_logger.warning.call_count == 3
    
    @pytest.mark.unit
    def test_attributes_exist_after_init(self, local_env):
        """Test that all expected attributes exist after initialization"""
        # Inherited attributes from BaseEnvironment
        assert hasattr(local_env, 'name')
        assert hasattr(local_env, 'config')
        assert hasattr(local_env, 'platform')
        assert hasattr(local_env, 'pipeline')
        assert hasattr(local_env, 'service_factories')
        assert hasattr(local_env, 'service_task_factories')
        
        # LocalEnvironment specific attributes
        assert hasattr(local_env, '_jobmanager')
        assert hasattr(local_env, '_engine_client')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
