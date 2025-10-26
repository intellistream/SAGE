"""
Test suite for sage.kernels.runtime.factory.task_factory module

Tests the TaskFactory class which creates task instances
for both local and remote execution environments.
"""

from unittest.mock import Mock, patch

import pytest

from sage.kernel.runtime.factory.task_factory import TaskFactory
from sage.kernel.runtime.task.local_task import LocalTask
from sage.kernel.utils.ray.actor import ActorWrapper


class MockTransformation:
    """Mock transformation for testing"""

    def __init__(self, basename="test_transform", remote=False, is_spout=True):
        self.basename = basename
        # 使用统一的测试环境名称，实际路径通过其他方式控制
        self.env_name = "test_env"
        self.operator_factory = Mock()
        self.delay = 0.01
        self.remote = remote
        self.is_spout = is_spout


class MockTaskContext:
    """Mock task context for testing"""

    def __init__(self):
        self.name = "test_context"
        self.parallel_index = 0
        self.parallelism = 1
        # Add missing attributes that TaskContext should have
        self.input_qd = Mock()
        self.response_qd = Mock()
        self.service_qds = {}
        self.downstream_groups = {}
        self.env_name = "test_env"

        # 使用统一的SAGE路径管理
        from sage.common.config.output_paths import get_test_context_dir

        self.env_base_dir = str(get_test_context_dir("test_context"))

        self.env_uuid = "test-uuid"
        self.env_console_log_level = "INFO"
        self.is_spout = True
        self.delay = 0.01
        self.stop_signal_num = 1
        self.jobmanager_host = "127.0.0.1"
        self.jobmanager_port = 19001
        self.stop_signal_count = 0
        # Add logger property
        self._logger = Mock()

    @property
    def logger(self):
        """Mock logger property"""
        return self._logger


class TestTaskFactory:
    """Test class for TaskFactory functionality"""

    @pytest.fixture
    def local_transformation(self):
        """Create a mock local transformation"""
        return MockTransformation(remote=False)

    @pytest.fixture
    def remote_transformation(self):
        """Create a mock remote transformation"""
        return MockTransformation(remote=True)

    @pytest.fixture
    def local_factory(self, local_transformation):
        """Create a TaskFactory for local execution"""
        return TaskFactory(local_transformation)

    @pytest.fixture
    def remote_factory(self, remote_transformation):
        """Create a TaskFactory for remote execution"""
        return TaskFactory(remote_transformation)

    @pytest.mark.unit
    def test_factory_initialization_local(self, local_transformation):
        """Test TaskFactory initialization for local transformation"""
        factory = TaskFactory(local_transformation)

        assert factory.basename == "test_transform"
        assert factory.env_name == "test_env"
        assert factory.operator_factory is local_transformation.operator_factory
        assert factory.delay == 0.01
        assert factory.remote is False
        assert factory.is_spout is True

    @pytest.mark.unit
    def test_factory_initialization_remote(self, remote_transformation):
        """Test TaskFactory initialization for remote transformation"""
        factory = TaskFactory(remote_transformation)

        assert factory.basename == "test_transform"
        assert factory.env_name == "test_env"
        assert factory.operator_factory is remote_transformation.operator_factory
        assert factory.delay == 0.01
        assert factory.remote is True
        assert factory.is_spout is True

    @pytest.mark.unit
    def test_create_local_task(self, local_factory, mock_context):
        """Test creating a local task"""
        task = local_factory.create_task("test_task", mock_context)

        # Should return a LocalTask instance
        assert isinstance(task, LocalTask)
        assert not isinstance(task, ActorWrapper)

    @pytest.mark.unit
    @patch("sage.kernel.runtime.factory.task_factory.RayTask")
    def test_create_remote_task(
        self, mock_ray_task_class, remote_factory, mock_context
    ):
        """Test creating a remote task"""
        # Mock the Ray task class and its options method
        mock_ray_task_instance = Mock()
        mock_ray_task_class.options.return_value.remote.return_value = (
            mock_ray_task_instance
        )

        with patch(
            "sage.kernel.runtime.factory.task_factory.ActorWrapper"
        ) as mock_wrapper:
            mock_wrapper_instance = Mock()
            mock_wrapper.return_value = mock_wrapper_instance

            task = remote_factory.create_task("test_task", mock_context)

            # Should create RayTask with options and wrap it
            mock_ray_task_class.options.assert_called_once_with(lifetime="detached")
            mock_ray_task_class.options.return_value.remote.assert_called_once_with(
                mock_context, remote_factory.operator_factory
            )
            mock_wrapper.assert_called_once_with(mock_ray_task_instance)
            assert task is mock_wrapper_instance

    @pytest.mark.unit
    def test_factory_attributes_inheritance(self):
        """Test that factory inherits all necessary attributes from transformation"""
        transformation = MockTransformation(
            basename="custom_transform", remote=True, is_spout=False
        )
        transformation.env_name = "custom_env"
        transformation.delay = 0.05

        factory = TaskFactory(transformation)

        assert factory.basename == "custom_transform"
        assert factory.env_name == "custom_env"
        assert factory.delay == 0.05
        assert factory.remote is True
        assert factory.is_spout is False

    @pytest.mark.unit
    def test_factory_repr(self, local_factory):
        """Test string representation of TaskFactory"""
        repr_str = repr(local_factory)
        assert "TaskFactory" in repr_str
        assert "test_transform" in repr_str

    @pytest.mark.unit
    def test_multiple_task_creation(self, local_factory, mock_context):
        """Test creating multiple tasks from same factory"""
        task1 = local_factory.create_task("task1", mock_context)
        task2 = local_factory.create_task("task2", mock_context)

        # Should create separate instances
        assert task1 is not task2
        assert isinstance(task1, LocalTask)
        assert isinstance(task2, LocalTask)

    @pytest.mark.unit
    def test_factory_with_different_transformations(self):
        """Test factory behavior with different transformation types"""
        # Spout transformation
        spout_transform = MockTransformation(is_spout=True)
        spout_factory = TaskFactory(spout_transform)
        assert spout_factory.is_spout is True

        # Non-spout transformation
        non_spout_transform = MockTransformation(is_spout=False)
        non_spout_factory = TaskFactory(non_spout_transform)
        assert non_spout_factory.is_spout is False

    @pytest.mark.integration
    @patch("sage.kernel.runtime.factory.task_factory.RayTask")
    @patch("sage.kernel.runtime.factory.task_factory.ActorWrapper")
    def test_factory_integration_local_and_remote(
        self, mock_wrapper, mock_ray_task, mock_context
    ):
        """Integration test creating both local and remote tasks"""
        # Create factories
        local_transform = MockTransformation(remote=False)
        remote_transform = MockTransformation(remote=True)

        local_factory = TaskFactory(local_transform)
        remote_factory = TaskFactory(remote_transform)

        # Create tasks
        local_task = local_factory.create_task("local_task", mock_context)

        # Mock remote task creation
        mock_ray_instance = Mock()
        mock_ray_task.options.return_value.remote.return_value = mock_ray_instance
        mock_wrapper.return_value = Mock()

        remote_factory.create_task("remote_task", mock_context)

        # Verify correct types
        assert isinstance(local_task, LocalTask)
        mock_wrapper.assert_called_once()

    @pytest.mark.unit
    def test_factory_with_none_context(self, local_factory):
        """Test creating task with None context"""
        # Should raise an exception when context is None
        with pytest.raises(AttributeError):
            local_factory.create_task("test_task", None)

    @pytest.mark.unit
    def test_factory_operator_factory_propagation(self, mock_context):
        """Test that operator factory is properly propagated to tasks"""
        mock_operator_factory = Mock()
        transformation = MockTransformation()
        transformation.operator_factory = mock_operator_factory

        factory = TaskFactory(transformation)

        # Verify operator factory is stored
        assert factory.operator_factory is mock_operator_factory

        # Create task and verify operator factory is passed
        task = factory.create_task("test_task", mock_context)
        # Note: The actual verification depends on LocalTask implementation
        assert isinstance(task, LocalTask)


class TestTaskFactoryEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.unit
    def test_factory_with_missing_transformation_attributes(self):
        """Test factory creation when transformation is missing attributes"""
        incomplete_transform = Mock()
        incomplete_transform.basename = "incomplete"
        # Missing other required attributes

        try:
            TaskFactory(incomplete_transform)
            # Behavior depends on implementation
        except AttributeError:
            # Expected if implementation requires all attributes
            pass

    @pytest.mark.unit
    def test_factory_with_none_transformation(self):
        """Test factory creation with None transformation"""
        with pytest.raises((AttributeError, TypeError)):
            TaskFactory(None)

    @pytest.mark.unit
    @patch("sage.kernel.runtime.factory.task_factory.RayTask")
    def test_remote_task_creation_ray_failure(self, mock_ray_task_class, mock_context):
        """Test remote task creation when Ray operations fail"""
        # Mock Ray task creation failure
        mock_ray_task_class.options.side_effect = Exception("Ray not available")

        remote_transform = MockTransformation(remote=True)
        factory = TaskFactory(remote_transform)

        # Should propagate the exception
        with pytest.raises(Exception, match="Ray not available"):
            factory.create_task("test_task", mock_context)

    @pytest.mark.unit
    def test_factory_with_extreme_values(self):
        """Test factory with extreme attribute values"""
        extreme_transform = MockTransformation()
        extreme_transform.delay = 999999.999
        extreme_transform.basename = "a" * 1000  # Very long name

        factory = TaskFactory(extreme_transform)

        assert factory.delay == 999999.999
        assert len(factory.basename) == 1000

    @pytest.mark.unit
    def test_factory_with_special_characters(self):
        """Test factory with special characters in names"""
        special_transform = MockTransformation()
        special_transform.basename = "test-task_with.special@chars#123"
        special_transform.env_name = "env/with\\special:chars"

        factory = TaskFactory(special_transform)

        assert factory.basename == "test-task_with.special@chars#123"
        assert factory.env_name == "env/with\\special:chars"

    @pytest.mark.unit
    def test_factory_thread_safety(self, mock_context):
        """Test factory in multi-threaded environment"""
        import threading

        transformation = MockTransformation()
        factory = TaskFactory(transformation)

        tasks = []

        def create_task_worker(task_id):
            try:
                task = factory.create_task(f"task_{task_id}", mock_context)
                tasks.append(task)
            except Exception as e:
                tasks.append(e)

        # Create multiple threads
        threads = [
            threading.Thread(target=create_task_worker, args=(i,)) for i in range(10)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All tasks should be created successfully
        assert len(tasks) == 10
        for task in tasks:
            assert isinstance(task, LocalTask)


class TestTaskFactoryPerformance:
    """Performance tests for TaskFactory"""

    @pytest.mark.slow
    def test_factory_creation_performance(self):
        """Test performance of factory creation"""
        import time

        transformation = MockTransformation()

        start_time = time.time()

        # Create many factories
        factories = [TaskFactory(transformation) for _ in range(1000)]

        elapsed = time.time() - start_time

        # Should be fast
        assert elapsed < 1.0  # Less than 1 second for 1000 factories
        assert len(factories) == 1000

    @pytest.mark.slow
    def test_task_creation_performance(self, mock_context):
        """Test performance of task creation"""
        import time

        transformation = MockTransformation()
        factory = TaskFactory(transformation)

        start_time = time.time()

        # Create many tasks
        tasks = [factory.create_task(f"task_{i}", mock_context) for i in range(100)]

        elapsed = time.time() - start_time

        # Should be reasonably fast
        assert elapsed < 1.0  # Less than 1 second for 100 tasks
        assert len(tasks) == 100


# Additional fixtures and utilities
@pytest.fixture
def mock_context():
    """Create a mock task context"""
    return MockTaskContext()


@pytest.fixture
def factory_with_complex_transformation():
    """Create a factory with a more complex transformation"""

    class ComplexTransformation:
        def __init__(self):
            self.basename = "complex_transform"
            self.env_name = "complex_env"
            self.operator_factory = Mock()
            self.delay = 0.001
            self.remote = False
            self.is_spout = True
            self.custom_attribute = "custom_value"

    return TaskFactory(ComplexTransformation())


@pytest.fixture
def transformation_factory():
    """Factory for creating different types of transformations"""

    def _create_transformation(remote=False, is_spout=True, basename="test"):
        transform = MockTransformation(
            basename=basename, remote=remote, is_spout=is_spout
        )
        return transform

    return _create_transformation
