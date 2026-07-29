from __future__ import annotations

from unittest.mock import MagicMock


def test_submit_routes_through_shared_runtime_backend_helper(monkeypatch):
    from sage.kernel.api.flownet_environment import FlownetEnvironment

    adapter = MagicMock(name="runtime_backend_adapter")
    stream_handle = MagicMock(name="stream_handle")
    stream_handle.is_running = True

    compiled_graph = MagicMock(name="compiled_graph")
    compiled_graph.submit.return_value = stream_handle

    compiler_instance = MagicMock(name="compiler_instance")
    compiler_instance.compile.return_value = compiled_graph

    monkeypatch.setattr(
        "sage.kernel.api.runtime_backend.get_flownet_runtime_backend",
        lambda: adapter,
    )
    monkeypatch.setattr(
        "sage.kernel.flow.pipeline_compiler.PipelineCompiler",
        lambda: compiler_instance,
    )

    env = FlownetEnvironment("routing_test")
    ref = env.submit(autostop=False)

    compiler_instance.compile.assert_called_once_with(env.pipeline, adapter)
    assert ref is stream_handle
