"""
Unit tests for BaseEnvironment and LocalEnvironment classes.

Tests cover:
- BaseEnvironment initialization and configuration
- LocalEnvironment initialization
- Service registration
- Scheduler initialization (FIFO, LoadAware, custom)
- from_source/from_batch/from_future methods
- Console log level configuration
- Pipeline management
- JobManager integration
"""

from unittest.mock import MagicMock, patch

import pytest

from sage.common.core import BaseFunction
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_jobmanager():
    """Mock JobManager for environment testing"""
    jobmanager = MagicMock()
    jobmanager.submit_job = MagicMock(return_value="test-uuid-123")
    jobmanager.jobs = {}
    return jobmanager


@pytest.fixture
def local_env(mock_jobmanager):
    """Create LocalEnvironment instance with mocked JobManager"""
    env = LocalEnvironment(name="test_env", config={"test_key": "test_value"})
    env._jobmanager = mock_jobmanager
    return env


@pytest.fixture
def base_env_config():
    """Standard configuration for environment testing"""
    return {
        "engine_host": "localhost",
        "engine_port": 19000,
        "buffer_size": 1000,
    }


@pytest.fixture
def mock_transformation():
    """Mock transformation for testing"""
    transformation = MagicMock()
    transformation.basename = "mock_transformation"
    transformation.function_class = MagicMock(__name__="MockFunction")
    return transformation


@pytest.fixture
def mock_datastream_class():
    """Mock DataStream class for testing"""
    with patch("sage.kernel.api.base_environment.DataStream") as mock_ds:
        yield mock_ds


class MockService:
    """Mock service class for testing service registration"""

    def __init__(self, config=None, **kwargs):
        self.config = config
        self.kwargs = kwargs
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False


class CustomScheduler(BaseScheduler):
    """Custom scheduler for testing"""

    def __init__(self):
        super().__init__()
        self.custom_initialized = True

    def make_decision(self, graph):
        """Implement abstract method"""
        return {}

    def schedule_task(self, task):
        return "custom_worker"


# ============================================================================
# BaseEnvironment Tests
# ============================================================================


@pytest.mark.unit
class TestBaseEnvironmentInitialization:
    """Test BaseEnvironment initialization and configuration"""

    def test_init_with_minimal_config(self):
        """Test initialization with minimal configuration"""
        env = LocalEnvironment(name="minimal_env")

        assert env.name == "minimal_env"
        assert env.config == {}
        assert env.platform == "local"
        assert env.pipeline == []
        assert env.service_factories == {}
        assert env.enable_monitoring is False
        assert env.console_log_level == "INFO"

    def test_init_with_full_config(self, base_env_config):
        """Test initialization with full configuration"""
        env = LocalEnvironment(
            name="full_env",
            config=base_env_config,
            scheduler="fifo",
            enable_monitoring=True,
        )

        assert env.name == "full_env"
        assert env.config == base_env_config
        assert env.config["engine_host"] == "localhost"
        assert env.config["engine_port"] == 19000
        assert env.enable_monitoring is True

    def test_init_preserves_config_dict(self, base_env_config):
        """Test that initialization creates independent config copy"""
        env = LocalEnvironment(name="test_env", config=base_env_config)

        # Modify environment config
        env.config["new_key"] = "new_value"

        # Original config should be unchanged
        assert "new_key" not in base_env_config

    def test_init_with_none_config(self):
        """Test initialization with None config creates empty dict"""
        env = LocalEnvironment(name="test_env", config=None)

        assert env.config == {}
        assert isinstance(env.config, dict)


@pytest.mark.unit
class TestSchedulerInitialization:
    """Test scheduler initialization and configuration"""

    def test_default_fifo_scheduler(self):
        """Test default FIFO scheduler initialization"""
        env = LocalEnvironment(name="test_env", scheduler=None)

        assert env.scheduler is not None
        assert isinstance(env.scheduler, FIFOScheduler)
        assert env.scheduler.platform == "local"

    def test_fifo_scheduler_by_name(self):
        """Test FIFO scheduler initialization by string name"""
        env = LocalEnvironment(name="test_env", scheduler="fifo")

        assert isinstance(env.scheduler, FIFOScheduler)
        assert env.scheduler.platform == "local"

    def test_load_aware_scheduler_by_name(self):
        """Test LoadAware scheduler initialization"""
        for scheduler_name in ["load_aware", "loadaware"]:
            env = LocalEnvironment(name="test_env", scheduler=scheduler_name)

            assert isinstance(env.scheduler, LoadAwareScheduler)
            assert env.scheduler.platform == "local"

    def test_custom_scheduler_instance(self):
        """Test custom scheduler instance initialization"""
        custom = CustomScheduler()
        env = LocalEnvironment(name="test_env", scheduler=custom)

        assert env.scheduler is custom
        assert env.scheduler.custom_initialized is True

    def test_invalid_scheduler_name_raises_error(self):
        """Test that invalid scheduler name raises ValueError"""
        with pytest.raises(ValueError, match="Unknown scheduler type"):
            LocalEnvironment(name="test_env", scheduler="invalid_scheduler")

    def test_invalid_scheduler_type_raises_error(self):
        """Test that invalid scheduler type raises TypeError"""
        with pytest.raises(TypeError, match="scheduler must be None, str, or BaseScheduler"):
            LocalEnvironment(name="test_env", scheduler=123)


@pytest.mark.unit
class TestConsoleLogLevel:
    """Test console log level configuration"""

    def test_default_log_level(self):
        """Test default console log level"""
        env = LocalEnvironment(name="test_env")
        assert env.console_log_level == "INFO"

    def test_set_valid_log_levels(self):
        """Test setting valid log levels"""
        env = LocalEnvironment(name="test_env")

        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            env.set_console_log_level(level)
            assert env.console_log_level == level

            # Test case-insensitive
            env.set_console_log_level(level.lower())
            assert env.console_log_level == level

    def test_set_invalid_log_level_raises_error(self):
        """Test that invalid log level raises ValueError"""
        env = LocalEnvironment(name="test_env")

        with pytest.raises(ValueError, match="Invalid log level"):
            env.set_console_log_level("INVALID")

    def test_log_level_updates_existing_logger(self):
        """Test that changing log level updates existing logger"""
        env = LocalEnvironment(name="test_env")

        # Access logger to initialize it
        _ = env.logger

        # Mock the logger's update method
        with patch.object(env.logger, "update_output_level") as mock_update:
            env.set_console_log_level("DEBUG")

            mock_update.assert_called_once_with("console", "DEBUG")


@pytest.mark.unit
class TestServiceRegistration:
    """Test service registration functionality"""

    def test_register_service_basic(self, local_env):
        """Test basic service registration"""
        service_name = "test_service"
        service = local_env.register_service(service_name, MockService, config={"key": "value"})

        assert service_name in local_env.service_factories
        assert isinstance(service, ServiceFactory)
        assert local_env.service_factories[service_name].service_name == service_name
        assert local_env.service_factories[service_name].service_class == MockService

    def test_register_service_with_args(self, local_env):
        """Test service registration with positional arguments"""
        service_name = "arg_service"
        local_env.register_service(service_name, MockService, "arg1", "arg2", key="value")

        factory = local_env.service_factories[service_name]
        assert factory.service_args == ("arg1", "arg2")
        assert factory.service_kwargs == {"key": "value"}

    def test_register_service_overwrites_existing(self, local_env):
        """Test that re-registering service overwrites previous"""
        service_name = "overwrite_service"

        # Register first service
        local_env.register_service(service_name, MockService, config="v1")
        first_factory = local_env.service_factories[service_name]

        # Register second service with same name
        local_env.register_service(service_name, MockService, config="v2")
        second_factory = local_env.service_factories[service_name]

        assert first_factory is not second_factory
        assert second_factory.service_kwargs == {"config": "v2"}

    def test_register_service_factory_directly(self, local_env):
        """Test registering ServiceFactory instance directly"""
        service_name = "factory_service"
        factory = ServiceFactory(
            service_name=service_name,
            service_class=MockService,
            service_args=(),
            service_kwargs={"test": "value"},
        )

        local_env.register_service_factory(service_name, factory)

        assert local_env.service_factories[service_name] is factory


@pytest.mark.unit
class TestDataSourceCreation:
    """Test data source creation methods"""

    @patch("sage.kernel.api.datastream.DataStream")
    def test_from_source_with_function_class(self, mock_datastream, local_env):
        """Test from_source with BaseFunction class"""

        class MockSourceFunction(BaseFunction):
            def __call__(self, ctx):
                return [1, 2, 3]

        local_env.from_source(MockSourceFunction)

        # Verify transformation was added to pipeline
        assert len(local_env.pipeline) == 1
        transformation = local_env.pipeline[0]
        assert transformation.__class__.__name__ == "SourceTransformation"

        # Verify DataStream was created
        mock_datastream.assert_called_once()

    @patch("sage.kernel.api.datastream.DataStream")
    def test_from_source_with_lambda(self, mock_datastream, local_env):
        """Test from_source with lambda function"""
        source_func = lambda ctx: [1, 2, 3]  # noqa: E731

        local_env.from_source(source_func)

        # Verify transformation was added
        assert len(local_env.pipeline) == 1
        transformation = local_env.pipeline[0]
        assert transformation.__class__.__name__ == "SourceTransformation"

    @patch("sage.kernel.api.datastream.DataStream")
    def test_from_batch_with_list(self, mock_datastream, local_env):
        """Test from_batch with list data"""
        data = [1, 2, 3, 4, 5]
        local_env.from_batch(data)

        # Verify BatchTransformation was created
        assert len(local_env.pipeline) == 1
        transformation = local_env.pipeline[0]
        assert transformation.__class__.__name__ == "BatchTransformation"

    @patch("sage.kernel.api.datastream.DataStream")
    def test_from_batch_with_tuple(self, mock_datastream, local_env):
        """Test from_batch with tuple data"""
        data = (10, 20, 30)
        local_env.from_batch(data)

        assert len(local_env.pipeline) == 1
        assert local_env.pipeline[0].__class__.__name__ == "BatchTransformation"

    @patch("sage.kernel.api.datastream.DataStream")
    def test_from_batch_with_function_class(self, mock_datastream, local_env):
        """Test from_batch with custom function class"""

        class CustomBatchFunction(BaseFunction):
            def get_data_iterator(self):
                return iter(range(10))

            def get_total_count(self):
                return 10

        local_env.from_batch(CustomBatchFunction, custom_arg="value")

        assert len(local_env.pipeline) == 1
        transformation = local_env.pipeline[0]
        assert transformation.__class__.__name__ == "BatchTransformation"

    @patch("sage.kernel.api.datastream.DataStream")
    def test_from_batch_with_iterable(self, mock_datastream, local_env):
        """Test from_batch with various iterable types"""
        # Test with range
        local_env.from_batch(range(100))
        assert len(local_env.pipeline) == 1

        # Test with set
        local_env.from_batch({1, 2, 3})
        assert len(local_env.pipeline) == 2

        # Test with generator
        local_env.from_batch(x for x in range(5))
        assert len(local_env.pipeline) == 3

    @patch("sage.kernel.api.datastream.DataStream")
    def test_from_batch_with_string(self, mock_datastream, local_env):
        """Test from_batch with string (character iteration)"""
        local_env.from_batch("hello")

        assert len(local_env.pipeline) == 1
        assert local_env.pipeline[0].__class__.__name__ == "BatchTransformation"

    def test_from_batch_with_non_iterable_raises_error(self, local_env):
        """Test from_batch with non-iterable raises TypeError"""
        with pytest.raises(TypeError, match="Unsupported source type"):
            local_env.from_batch(12345)

    @patch("sage.kernel.api.datastream.DataStream")
    def test_from_future(self, mock_datastream, local_env):
        """Test from_future creates FutureTransformation"""
        future_name = "feedback_loop"
        local_env.from_future(future_name)

        # Verify FutureTransformation was created
        assert len(local_env.pipeline) == 1
        transformation = local_env.pipeline[0]
        assert transformation.__class__.__name__ == "FutureTransformation"


@pytest.mark.unit
class TestLocalEnvironmentSubmit:
    """Test LocalEnvironment submit functionality"""

    def test_submit_without_autostop(self, local_env, mock_jobmanager):
        """Test submit without autostop returns immediately"""
        local_env._jobmanager = mock_jobmanager

        env_uuid = local_env.submit(autostop=False)

        # Verify submit_job was called
        mock_jobmanager.submit_job.assert_called_once_with(local_env, autostop=False)
        assert env_uuid == "test-uuid-123"

    def test_submit_with_autostop(self, local_env, mock_jobmanager):
        """Test submit with autostop waits for completion"""
        local_env._jobmanager = mock_jobmanager

        # Mock _wait_for_completion to avoid blocking
        with patch.object(local_env, "_wait_for_completion") as mock_wait:
            env_uuid = local_env.submit(autostop=True)

            mock_jobmanager.submit_job.assert_called_once_with(local_env, autostop=True)
            mock_wait.assert_called_once()
            assert env_uuid == "test-uuid-123"

    def test_wait_for_completion_job_deleted(self, local_env, mock_jobmanager):
        """Test _wait_for_completion when job is deleted"""
        local_env._jobmanager = mock_jobmanager
        local_env.env_uuid = "test-uuid"

        # Job not found (deleted) - modify the jobs dict directly
        mock_jobmanager.jobs = {"other-uuid": MagicMock()}

        # Should return immediately
        local_env._wait_for_completion()

    def test_wait_for_completion_job_stopped(self, local_env, mock_jobmanager):
        """Test _wait_for_completion when job status is stopped"""
        local_env._jobmanager = mock_jobmanager
        local_env.env_uuid = "test-uuid"

        # Mock job info
        job_info = MagicMock()
        job_info.status = "stopped"
        mock_jobmanager.jobs = {"test-uuid": job_info}

        local_env._wait_for_completion()

    def test_wait_for_completion_no_env_uuid(self, local_env):
        """Test _wait_for_completion with no environment UUID"""
        local_env.env_uuid = None

        # Should log warning and return
        local_env._wait_for_completion()


@pytest.mark.unit
class TestEnvironmentProperties:
    """Test environment properties and lazy initialization"""

    def test_logger_property_lazy_initialization(self, local_env):
        """Test logger is lazily initialized"""
        assert not hasattr(local_env, "_logger")

        logger = local_env.logger

        assert hasattr(local_env, "_logger")
        assert logger is not None

    def test_logger_property_reuses_instance(self, local_env):
        """Test logger property returns same instance"""
        logger1 = local_env.logger
        logger2 = local_env.logger

        assert logger1 is logger2

    def test_client_property_creates_jobmanager_client(self, local_env):
        """Test client property creates JobManagerClient"""
        assert local_env._engine_client is None

        with patch("sage.kernel.api.base_environment.JobManagerClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            client = local_env.client

            # Verify client was created with default host/port
            mock_client_class.assert_called_once_with(host="127.0.0.1", port=19000)
            assert client is mock_instance

    def test_client_property_uses_config_host_port(self, base_env_config):
        """Test client property uses config host and port"""
        env = LocalEnvironment(name="test_env", config=base_env_config)

        with patch("sage.kernel.api.base_environment.JobManagerClient") as mock_client_class:
            _ = env.client

            mock_client_class.assert_called_once_with(host="localhost", port=19000)

    def test_scheduler_property(self, local_env):
        """Test scheduler property returns scheduler instance"""
        assert local_env.scheduler is not None
        assert isinstance(local_env.scheduler, FIFOScheduler)


@pytest.mark.unit
class TestPipelineManagement:
    """Test pipeline management methods"""

    def test_append_transformation(self, local_env, mock_transformation):
        """Test _append adds transformation to pipeline"""
        assert len(local_env.pipeline) == 0

        with patch("sage.kernel.api.datastream.DataStream") as mock_ds:
            local_env._append(mock_transformation)

            assert len(local_env.pipeline) == 1
            assert local_env.pipeline[0] is mock_transformation
            mock_ds.assert_called_once()

    def test_multiple_transformations_in_pipeline(self, local_env):
        """Test multiple transformations can be added to pipeline"""
        transformations = [MagicMock() for _ in range(5)]

        with patch("sage.kernel.api.datastream.DataStream"):
            for t in transformations:
                local_env._append(t)

        assert len(local_env.pipeline) == 5
        assert local_env.pipeline == transformations


@pytest.mark.unit
class TestEnvironmentInheritance:
    """Test LocalEnvironment inheritance from BaseEnvironment"""

    def test_local_environment_sets_platform(self):
        """Test LocalEnvironment sets platform to 'local'"""
        env = LocalEnvironment(name="test_env")
        assert env.platform == "local"

    def test_local_environment_no_engine_client(self):
        """Test LocalEnvironment sets _engine_client to None"""
        env = LocalEnvironment(name="test_env")
        assert env._engine_client is None

    def test_local_environment_inherits_methods(self, local_env):
        """Test LocalEnvironment inherits BaseEnvironment methods"""
        # Test inherited methods exist
        assert hasattr(local_env, "from_source")
        assert hasattr(local_env, "from_batch")
        assert hasattr(local_env, "from_future")
        assert hasattr(local_env, "register_service")
        assert hasattr(local_env, "set_console_log_level")


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_pipeline_submission(self, local_env, mock_jobmanager):
        """Test submitting environment with empty pipeline"""
        local_env._jobmanager = mock_jobmanager
        assert len(local_env.pipeline) == 0

        env_uuid = local_env.submit(autostop=False)

        # Should still submit successfully
        mock_jobmanager.submit_job.assert_called_once()
        assert env_uuid == "test-uuid-123"

    def test_service_registration_with_no_args(self, local_env):
        """Test service registration with no arguments"""
        service_name = "minimal_service"
        local_env.register_service(service_name, MockService)

        factory = local_env.service_factories[service_name]
        assert factory.service_args == ()
        assert factory.service_kwargs == {}

    def test_multiple_from_source_creates_multiple_transformations(self, local_env):
        """Test multiple from_source calls create independent transformations"""

        class Source1(BaseFunction):
            pass

        class Source2(BaseFunction):
            pass

        with patch("sage.kernel.api.datastream.DataStream"):
            local_env.from_source(Source1)
            local_env.from_source(Source2)

        assert len(local_env.pipeline) == 2
        assert local_env.pipeline[0].function_class != local_env.pipeline[1].function_class

    def test_config_modification_after_init(self, local_env):
        """Test config can be modified after initialization"""
        local_env.config["new_setting"] = "new_value"

        assert local_env.config["new_setting"] == "new_value"

    def test_enable_monitoring_flag(self):
        """Test enable_monitoring flag is properly set"""
        env_disabled = LocalEnvironment(name="env1", enable_monitoring=False)
        env_enabled = LocalEnvironment(name="env2", enable_monitoring=True)

        assert env_disabled.enable_monitoring is False
        assert env_enabled.enable_monitoring is True
