"""
Unit tests for FlownetEnvironment.

Layer 1 of the 3-layer test taxonomy — intellistream/SAGE#1440.

These tests verify the structural contract and constructor behaviour of
``FlownetEnvironment`` **without** requiring sageFlownet to be installed.
All Flownet interaction is replaced by ``unittest.mock``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_env(**kwargs):
    from sage.kernel.api.flownet_environment import FlownetEnvironment

    return FlownetEnvironment(**kwargs)


# ===========================================================================
# Suite 1: Import and instantiation
# ===========================================================================


@pytest.mark.unit
class TestFlownetEnvironmentInit:
    """Basic construction checks."""

    def test_import(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        assert FlownetEnvironment is not None

    def test_top_level_api_export(self):
        from sage.kernel.api import FlownetEnvironment

        assert FlownetEnvironment is not None

    def test_kernel_top_level_export(self):
        import sage.kernel as sk

        assert hasattr(sk, "FlownetEnvironment")

    def test_default_name(self):
        env = _make_env()
        assert env.name == "flownet_environment"

    def test_custom_name(self):
        env = _make_env(name="my_flow")
        assert env.name == "my_flow"

    def test_platform_is_flownet(self):
        env = _make_env()
        assert env.platform == "flownet"

    def test_pipeline_starts_empty(self):
        env = _make_env()
        assert env.pipeline == []

    def test_placement_policy_default_none(self):
        env = _make_env()
        assert env.placement_policy is None

    def test_placement_policy_custom(self):
        env = _make_env(placement_policy="round_robin")
        assert env.placement_policy == "round_robin"

    def test_placement_policy_setter(self):
        env = _make_env()
        env.placement_policy = "affinity"
        assert env.placement_policy == "affinity"

    def test_config_stored(self):
        cfg = {"engine_host": "10.0.0.1", "batch_size": 64}
        env = _make_env(config=cfg)
        assert env.config["engine_host"] == "10.0.0.1"
        assert env.config["batch_size"] == 64

    def test_scheduler_fifo_string(self):
        env = _make_env(scheduler="fifo")
        assert env._scheduler is not None

    def test_scheduler_load_aware_string(self):
        env = _make_env(scheduler="load_aware")
        assert env._scheduler is not None

    def test_is_running_false_initially(self):
        env = _make_env()
        assert env.is_running is False

    def test_repr_contains_name(self):
        env = _make_env(name="test_repr")
        r = repr(env)
        assert "test_repr" in r
        assert "idle" in r

    def test_context_manager(self):
        with _make_env(name="ctx") as env:
            assert env.name == "ctx"


# ===========================================================================
# Suite 2: Structural contract
# ===========================================================================


@pytest.mark.unit
class TestFlownetEnvironmentContract:
    """Verify class hierarchy and abstract method implementation."""

    def test_is_subclass_of_base_environment(self):
        from sage.kernel.api.base_environment import BaseEnvironment
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        assert issubclass(FlownetEnvironment, BaseEnvironment)

    def test_has_submit_method(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        assert callable(getattr(FlownetEnvironment, "submit", None))

    def test_has_stop_method(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        assert callable(getattr(FlownetEnvironment, "stop", None))

    def test_has_close_method(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        assert callable(getattr(FlownetEnvironment, "close", None))

    def test_has_health_check_method(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        assert callable(getattr(FlownetEnvironment, "health_check", None))


# ===========================================================================
# Suite 3: submit() delegates to PipelineCompiler (mocked)
# ===========================================================================


@pytest.mark.unit
class TestFlownetEnvironmentSubmit:
    """Verify submit() calls the compiler and adapter correctly."""

    def _patched_submit(self, autostop=False):
        """Create env, attach a mock pipeline entry, call submit() with mocks."""
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        env = FlownetEnvironment(name="test_submit")

        # Attach a fake pipeline so that compile() has something to work with.
        fake_stage = MagicMock()
        env.pipeline = [fake_stage]

        mock_compiled = MagicMock()
        mock_compiled.submit.return_value = None if autostop else MagicMock()

        mock_compiler_instance = MagicMock()
        mock_compiler_instance.compile.return_value = mock_compiled

        mock_adapter = MagicMock()

        with (
            patch(
                "sage.kernel.flow.pipeline_compiler.PipelineCompiler",
                return_value=mock_compiler_instance,
            ),
            patch(
                "sage.platform.runtime.adapters.flownet_adapter.get_flownet_adapter",
                return_value=mock_adapter,
            ),
        ):
            result = env.submit(autostop=autostop)

        return env, mock_compiler_instance, mock_compiled, mock_adapter, result

    def test_submit_calls_compile(self):
        env, compiler, compiled, adapter, _ = self._patched_submit(autostop=True)
        compiler.compile.assert_called_once_with(env.pipeline, adapter)

    def test_submit_calls_compiled_submit(self):
        _, _, compiled, _, _ = self._patched_submit(autostop=False)
        compiled.submit.assert_called_once_with(autostop=False)

    def test_submit_autostop_true_calls_batch(self):
        _, _, compiled, _, _ = self._patched_submit(autostop=True)
        compiled.submit.assert_called_once_with(autostop=True)

    def test_submit_streaming_stores_handle(self):
        env, _, compiled, _, result = self._patched_submit(autostop=False)
        # The returned handle from compiled.submit() should be stored.
        assert env._streaming_handle is compiled.submit.return_value

    def test_submit_batch_no_handle_stored(self):
        env, _, _, _, _ = self._patched_submit(autostop=True)
        assert env._streaming_handle is None


# ===========================================================================
# Suite 4: stop() / close() / health_check()
# ===========================================================================


@pytest.mark.unit
class TestFlownetEnvironmentLifecycle:
    def test_stop_no_handle_logs_info(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        env = FlownetEnvironment()
        env.logger.info = MagicMock()
        env.logger.warning = MagicMock()
        env.stop()  # should not raise
        env.logger.warning.assert_not_called()
        env.logger.info.assert_called_once()
        assert "nothing to stop" in env.logger.info.call_args[0][0].lower()

    def test_stop_calls_handle_stop(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        env = FlownetEnvironment()
        mock_handle = MagicMock()
        env._streaming_handle = mock_handle
        env.stop()
        mock_handle.stop.assert_called_once()
        assert env._streaming_handle is None

    def test_close_resets_compiled_graph(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        env = FlownetEnvironment()
        env._compiled_graph = MagicMock()
        env.close()
        assert env._compiled_graph is None

    def test_health_check_returns_list_on_failure(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        env = FlownetEnvironment()
        # Adapter not available → should return empty list, not raise.
        with patch(
            "sage.platform.runtime.adapters.flownet_adapter.get_flownet_adapter",
            side_effect=RuntimeError("no flownet"),
        ):
            result = env.health_check()
        assert result == []

    def test_health_check_returns_nodes(self):
        from sage.kernel.api.flownet_environment import FlownetEnvironment

        env = FlownetEnvironment()
        nodes = [{"node_id": "n0", "status": "healthy"}]
        mock_adapter = MagicMock()
        mock_adapter.list_nodes.return_value = nodes
        with patch(
            "sage.platform.runtime.adapters.flownet_adapter.get_flownet_adapter",
            return_value=mock_adapter,
        ):
            result = env.health_check()
        assert result == nodes
