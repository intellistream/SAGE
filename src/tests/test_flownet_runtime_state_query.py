from __future__ import annotations

from types import SimpleNamespace

import pytest

from sage.runtime.flownet.client import node_runtime as node_runtime_module
from sage.runtime.flownet.client.node_runtime import V1NodeRuntimeService


class _DummyStateRuntime:
    def __init__(self) -> None:
        self.calls: list[dict[str, int | str]] = []

    def query_namespace_entries(
        self,
        *,
        namespace: str,
        prefix: str,
        limit: int,
        cursor: int,
    ) -> tuple[list[dict[str, object]], int | None]:
        self.calls.append(
            {
                "namespace": namespace,
                "prefix": prefix,
                "limit": int(limit),
                "cursor": int(cursor),
            }
        )
        return (
            [
                {
                    "key": "k1",
                    "value": {"token": "secret"},
                    "updated_at_ms": 123,
                }
            ],
            1,
        )


@pytest.fixture
def runtime_state_service() -> tuple[V1NodeRuntimeService, _DummyStateRuntime]:
    state_runtime = _DummyStateRuntime()
    runtime_host = SimpleNamespace(
        topic_api=None,
        _flow_process_execution=SimpleNamespace(
            _flow_engine=SimpleNamespace(
                _state_runtime=state_runtime,
            )
        ),
    )
    service = V1NodeRuntimeService(
        runtime_host=runtime_host,
        node_id="node-1",
        node_address="127.0.0.1:18080",
    )
    return service, state_runtime


def test_query_runtime_state_masks_value_and_writes_success_audit(
    runtime_state_service: tuple[V1NodeRuntimeService, _DummyStateRuntime],
) -> None:
    service, _ = runtime_state_service

    result = service.query_runtime_state(
        "ns.user",
        prefix="profile",
        principal="alice",
        include_values=True,
        reveal_values=False,
        permissions=[],
        allowed_namespaces=["ns.*"],
    )

    assert result["masked_values"] is True
    assert result["items"][0]["value"] == "<redacted>"
    assert result["next_cursor"] == 1

    last_audit = service._runtime_state_query_audit[-1]
    assert last_audit["allowed"] is True
    assert last_audit["reason"] == "ok"
    assert last_audit["result_count"] == 1


def test_query_runtime_state_reveal_permission_denied_downgrades_to_redacted(
    runtime_state_service: tuple[V1NodeRuntimeService, _DummyStateRuntime],
) -> None:
    """Issue 1493: reveal_values=True without permission must NOT raise PermissionError.
    Instead the response must succeed with <redacted> values so the caller can
    still observe which keys exist ('使调用方能判断状态存在但无法读取内容')."""
    service, _ = runtime_state_service

    # Should NOT raise - must return a masked response
    result = service.query_runtime_state(
        "ns.user",
        prefix="profile",
        principal="alice",
        include_values=True,
        reveal_values=True,
        permissions=[],  # no runtime_state.reveal_values permission
        allowed_namespaces=["*"],
    )

    # Query succeeds; values are masked
    assert result["masked_values"] is True
    assert len(result["items"]) == 1
    assert result["items"][0]["value"] == "<redacted>"
    # Effective reveal_values is downgraded to False
    assert result["reveal_values"] is False
    # Keys and timestamps are preserved so caller can see state exists
    assert result["items"][0]["key"] == "k1"
    assert result["items"][0]["updated_at_ms"] == 123

    # Audit records: one for permission demotion, one for successful query
    audits = list(service._runtime_state_query_audit)
    reveal_audit = next(
        (a for a in audits if a["reason"] == "reveal_values_permission_required"), None
    )
    assert reveal_audit is not None
    assert reveal_audit["allowed"] is False
    assert reveal_audit["reveal_values"] is True

    ok_audit = next((a for a in audits if a["reason"] == "ok"), None)
    assert ok_audit is not None
    assert ok_audit["result_count"] == 1

    # NOT counted as a hard denial because the query itself succeeded
    assert int(service._stats.get("runtime_state_query_denied_total", 0)) == 0


def test_query_runtime_state_namespace_forbidden_is_audited(
    runtime_state_service: tuple[V1NodeRuntimeService, _DummyStateRuntime],
) -> None:
    service, _ = runtime_state_service

    with pytest.raises(PermissionError, match="runtime_state_query_namespace_forbidden"):
        service.query_runtime_state(
            "ns.user",
            prefix="profile",
            principal="alice",
            include_values=True,
            reveal_values=False,
            permissions=[],
            allowed_namespaces=["admin.*"],
        )

    last_audit = service._runtime_state_query_audit[-1]
    assert last_audit["allowed"] is False
    assert last_audit["reason"] == "namespace_forbidden"


def test_query_runtime_state_rate_limited_is_audited(
    monkeypatch: pytest.MonkeyPatch,
    runtime_state_service: tuple[V1NodeRuntimeService, _DummyStateRuntime],
) -> None:
    service, _ = runtime_state_service

    monkeypatch.setattr(node_runtime_module, "_RUNTIME_STATE_QUERY_MAX_PER_WINDOW", 2)
    monkeypatch.setattr(node_runtime_module, "_RUNTIME_STATE_QUERY_WINDOW_MS", 60_000)

    for _ in range(2):
        service.query_runtime_state(
            "ns.user",
            prefix="profile",
            principal="alice",
            include_values=False,
            reveal_values=False,
            permissions=[],
            allowed_namespaces=["*"],
        )

    with pytest.raises(RuntimeError, match="runtime_state_query_rate_limited"):
        service.query_runtime_state(
            "ns.user",
            prefix="profile",
            principal="alice",
            include_values=False,
            reveal_values=False,
            permissions=[],
            allowed_namespaces=["*"],
        )

    last_audit = service._runtime_state_query_audit[-1]
    assert last_audit["allowed"] is False
    assert last_audit["reason"] == "rate_limited"
    assert int(service._stats["runtime_state_query_rate_limited_total"]) == 1


def test_query_runtime_state_include_values_false_hides_value_field(
    runtime_state_service: tuple[V1NodeRuntimeService, _DummyStateRuntime],
) -> None:
    service, _ = runtime_state_service

    result = service.query_runtime_state(
        "ns.user",
        prefix="profile",
        principal="alice",
        include_values=False,
        reveal_values=False,
        permissions=[],
        allowed_namespaces=["*"],
    )

    assert result["masked_values"] is False
    assert "value" not in result["items"][0]


def test_query_runtime_state_limit_and_cursor_are_normalized(
    runtime_state_service: tuple[V1NodeRuntimeService, _DummyStateRuntime],
) -> None:
    service, state_runtime = runtime_state_service

    result = service.query_runtime_state(
        "ns.user",
        prefix="profile",
        principal="alice",
        include_values=False,
        reveal_values=False,
        permissions=[],
        allowed_namespaces=["*"],
        limit=10_000,
        cursor="3",
    )

    assert result["limit"] == 1000
    assert result["cursor"] == 3
    assert state_runtime.calls[-1]["limit"] == 1000
    assert state_runtime.calls[-1]["cursor"] == 3
