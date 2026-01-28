"""
Unit tests for RemoteEnvironment
"""

import pytest


@pytest.mark.unit
class TestRemoteEnvironment:
    """Tests for RemoteEnvironment class"""

    def test_remote_environment_import(self):
        """Test RemoteEnvironment can be imported"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        assert RemoteEnvironment is not None

    def test_remote_environment_initialization(self):
        """Test RemoteEnvironment can be initialized"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        env = RemoteEnvironment(
            name="test_remote",
            host="127.0.0.1",
            port=19001,
        )

        assert env.name == "test_remote"
        assert env.platform == "remote"

    def test_remote_environment_default_params(self):
        """Test RemoteEnvironment with default parameters"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        env = RemoteEnvironment()

        assert env.name == "remote_environment"
        assert env.platform == "remote"

    def test_remote_environment_with_config(self):
        """Test RemoteEnvironment with custom config"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        config = {"batch_size": 100, "timeout": 30}
        env = RemoteEnvironment(name="test", config=config)

        assert env.name == "test"
        # Config gets engine_host and engine_port added automatically
        assert "batch_size" in env.config
        assert "timeout" in env.config
        assert env.config["batch_size"] == 100
        assert env.config["timeout"] == 30

    def test_remote_environment_with_scheduler(self):
        """Test RemoteEnvironment with scheduler parameter"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        # Test with string scheduler
        env = RemoteEnvironment(name="test", scheduler="fifo")
        assert env.name == "test"

        # Test with load_aware scheduler
        env2 = RemoteEnvironment(name="test2", scheduler="load_aware")
        assert env2.name == "test2"

    def test_remote_environment_with_extra_python_paths(self):
        """Test RemoteEnvironment with extra Python paths"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        extra_paths = ["/path/to/module1", "/path/to/module2"]
        env = RemoteEnvironment(
            name="test",
            extra_python_paths=extra_paths,
        )

        assert env.name == "test"

    def test_remote_environment_state_exclude(self):
        """Test __state_exclude__ attribute exists"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        assert hasattr(RemoteEnvironment, "__state_exclude__")
        assert isinstance(RemoteEnvironment.__state_exclude__, list)

        # Verify expected exclusions
        expected_excludes = ["logger", "_logger", "_engine_client", "_jobmanager"]
        for exclude in expected_excludes:
            assert exclude in RemoteEnvironment.__state_exclude__, (
                f"{exclude} should be in __state_exclude__"
            )

    def test_remote_environment_inherits_from_base(self):
        """Test RemoteEnvironment inherits from BaseEnvironment"""
        from sage.kernel.api.base_environment import BaseEnvironment
        from sage.kernel.api.remote_environment import RemoteEnvironment

        assert issubclass(RemoteEnvironment, BaseEnvironment)

    def test_remote_environment_custom_host_port(self):
        """Test RemoteEnvironment with custom host and port"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        env = RemoteEnvironment(
            name="test",
            host="192.168.1.100",
            port=29001,
        )

        assert env.name == "test"
        assert env.platform == "remote"


@pytest.mark.unit
class TestRemoteEnvironmentIntegration:
    """Integration tests for RemoteEnvironment"""

    def test_remote_environment_multiple_instances(self):
        """Test creating multiple RemoteEnvironment instances"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        env1 = RemoteEnvironment(name="env1")
        env2 = RemoteEnvironment(name="env2")

        assert env1.name == "env1"
        assert env2.name == "env2"
        assert env1 is not env2

    def test_remote_environment_with_none_config(self):
        """Test RemoteEnvironment with None config"""
        from sage.kernel.api.remote_environment import RemoteEnvironment

        env = RemoteEnvironment(name="test", config=None)

        assert env.name == "test"
        # Config gets engine_host and engine_port added automatically even when starting with None
        assert isinstance(env.config, dict)
        assert "engine_host" in env.config
        assert "engine_port" in env.config
