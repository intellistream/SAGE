from __future__ import annotations

import pytest

from sage.runtime.flownet_backend import _DEFAULT_LOCAL_ADDRESS, FlowNetRuntimeAdapter


class _FakeSession:
    def __init__(self) -> None:
        self.shutdown_calls: list[bool] = []

    def shutdown(self, wait: bool = True) -> None:
        self.shutdown_calls.append(bool(wait))


def test_flownet_runtime_adapter_connect_mode_uses_remote_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sage.runtime.flownet as flownet

    calls: list[tuple[str, dict[str, object]]] = []
    session = _FakeSession()

    def _fake_connect(**kwargs):
        calls.append(("connect", kwargs))
        return session

    def _fake_init_local(**kwargs):
        calls.append(("init_local", kwargs))
        raise AssertionError("connect mode should not fall back to init_local")

    monkeypatch.setattr(flownet, "connect", _fake_connect)
    monkeypatch.setattr(flownet, "init_local", _fake_init_local)

    adapter = FlowNetRuntimeAdapter()
    adapter.start(
        {
            "mode": "connect",
            "owner": "benchmark-owner",
            "entry_node": "sage-node-1:18787",
            "cluster": "cluster8",
            "connect_timeout": 5.0,
        }
    )

    try:
        assert calls == [
            (
                "connect",
                {
                    "owner": "benchmark-owner",
                    "local_address": _DEFAULT_LOCAL_ADDRESS,
                    "entry_node": "sage-node-1:18787",
                    "cluster": "cluster8",
                    "config_path": None,
                    "clusters_dir": None,
                    "connect_timeout": 5.0,
                    "mode": "connect",
                },
            )
        ]
    finally:
        adapter.stop()

    assert session.shutdown_calls == [True]


def test_flownet_runtime_adapter_cluster_mode_keeps_local_session_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sage.runtime.flownet as flownet

    calls: list[tuple[str, dict[str, object]]] = []
    session = _FakeSession()

    def _fake_init_local(**kwargs):
        calls.append(("init_local", kwargs))
        return session

    def _fake_connect(**kwargs):
        calls.append(("connect", kwargs))
        raise AssertionError("cluster mode should keep using init_local")

    monkeypatch.setattr(flownet, "init_local", _fake_init_local)
    monkeypatch.setattr(flownet, "connect", _fake_connect)

    adapter = FlowNetRuntimeAdapter()
    adapter.start({"mode": "cluster", "owner": "benchmark-owner"})

    try:
        assert calls == [
            (
                "init_local",
                {
                    "owner": "benchmark-owner",
                    "local_address": _DEFAULT_LOCAL_ADDRESS,
                    "entry_node": None,
                    "connect_timeout": None,
                },
            )
        ]
    finally:
        adapter.stop()

    assert session.shutdown_calls == [True]
