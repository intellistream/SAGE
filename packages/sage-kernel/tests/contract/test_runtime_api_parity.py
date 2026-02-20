"""Contract tests for runtime API semantic parity across three entry styles.

Issue coverage: intellistream/SAGE#1447

This suite validates shared semantics across:

- SAGE facade (`create/submit/run/call`) via `sage.kernel.facade`
- `LocalEnvironment`
- `FlownetEnvironment`

Current scope is intentionally focused on high-signal contract points:

1) non-blocking submit behavior
2) autostop behavior at environment tier
3) error propagation (no silent fallback)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _mock_facade_backend(monkeypatch: pytest.MonkeyPatch, *, submit_result=None, submit_error=None):
    """Patch facade backend helpers and return a controllable backend mock."""
    from sage.kernel import facade

    mock_backend = MagicMock()
    if submit_error is not None:
        mock_backend.submit.side_effect = submit_error
    else:
        mock_backend.submit.return_value = submit_result

    monkeypatch.setattr(facade, "_get_runtime_backend", lambda: mock_backend)
    monkeypatch.setattr(facade, "_resolve_flow_for_backend", lambda flow_obj: flow_obj)
    return mock_backend


def _mock_flownet_environment_compile(
    monkeypatch: pytest.MonkeyPatch,
    *,
    submit_result=None,
    submit_error=None,
):
    """Patch FlownetEnvironment compile/adapter dependencies for isolated tests."""
    mock_graph = MagicMock()
    if submit_error is not None:
        mock_graph.submit.side_effect = submit_error
    else:
        mock_graph.submit.return_value = submit_result

    mock_compiler_instance = MagicMock()
    mock_compiler_instance.compile.return_value = mock_graph

    monkeypatch.setattr(
        "sage.kernel.api.runtime_backend.get_flownet_runtime_backend",
        lambda: MagicMock(name="flownet_adapter"),
    )
    monkeypatch.setattr(
        "sage.kernel.flow.pipeline_compiler.PipelineCompiler",
        lambda: mock_compiler_instance,
    )
    return mock_graph


class TestSubmitContractParity:
    """Parity tests for submit lifecycle semantics across API entry styles."""

    def test_nonblocking_submit_returns_handle_or_ref(self, monkeypatch: pytest.MonkeyPatch):
        from sage.kernel.api.flownet_environment import FlownetEnvironment
        from sage.kernel.api.local_environment import LocalEnvironment
        from sage.kernel.facade import submit as facade_submit

        # facade submit -> run handle
        facade_handle = MagicMock(name="facade_run_handle")
        _mock_facade_backend(monkeypatch, submit_result=facade_handle)
        assert facade_submit(object()) is facade_handle

        # local env submit(autostop=False) -> job reference id
        local_env = LocalEnvironment("parity_local")
        local_env._jobmanager = MagicMock()
        local_env._jobmanager.submit_job.return_value = "job-123"

        wait_spy = MagicMock()
        monkeypatch.setattr(local_env, "_wait_for_completion", wait_spy)

        local_ref = local_env.submit(autostop=False)
        assert local_ref == "job-123"
        wait_spy.assert_not_called()

        # flownet env submit(autostop=False) -> streaming handle
        stream_handle = MagicMock(name="stream_handle")
        stream_handle.is_running = True
        _mock_flownet_environment_compile(monkeypatch, submit_result=stream_handle)

        flownet_env = FlownetEnvironment("parity_flownet")
        flownet_ref = flownet_env.submit(autostop=False)
        assert flownet_ref is stream_handle
        assert flownet_env.is_running is True

    def test_autostop_behavior_is_explicit(self, monkeypatch: pytest.MonkeyPatch):
        from sage.kernel.api.flownet_environment import FlownetEnvironment
        from sage.kernel.api.local_environment import LocalEnvironment

        # local: autostop=True must trigger wait path
        local_env = LocalEnvironment("parity_local_autostop")
        local_env._jobmanager = MagicMock()
        local_env._jobmanager.submit_job.return_value = "job-456"
        wait_spy = MagicMock()
        monkeypatch.setattr(local_env, "_wait_for_completion", wait_spy)

        local_result = local_env.submit(autostop=True)
        assert local_result == "job-456"
        wait_spy.assert_called_once()

        # flownet: autostop=True should not retain a streaming handle
        _mock_flownet_environment_compile(monkeypatch, submit_result=None)
        flownet_env = FlownetEnvironment("parity_flownet_autostop")
        result = flownet_env.submit(autostop=True)
        assert result is None
        assert flownet_env.is_running is False


class TestErrorPropagationParity:
    """Parity tests for fail-fast error propagation."""

    def test_submit_errors_propagate_across_all_entry_styles(self, monkeypatch: pytest.MonkeyPatch):
        from sage.kernel.api.flownet_environment import FlownetEnvironment
        from sage.kernel.api.local_environment import LocalEnvironment
        from sage.kernel.facade import submit as facade_submit

        expected_error = RuntimeError("contract-parity-error")

        # facade
        _mock_facade_backend(monkeypatch, submit_error=expected_error)
        with pytest.raises(RuntimeError, match="contract-parity-error"):
            facade_submit(object())

        # local
        local_env = LocalEnvironment("parity_local_error")
        local_env._jobmanager = MagicMock()
        local_env._jobmanager.submit_job.side_effect = expected_error
        with pytest.raises(RuntimeError, match="contract-parity-error"):
            local_env.submit(autostop=False)

        # flownet
        _mock_flownet_environment_compile(monkeypatch, submit_error=expected_error)
        flownet_env = FlownetEnvironment("parity_flownet_error")
        with pytest.raises(RuntimeError, match="contract-parity-error"):
            flownet_env.submit(autostop=False)
