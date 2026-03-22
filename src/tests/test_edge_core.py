from __future__ import annotations

import pytest

from sage.edge.core import normalize_mount_path, probe_payload


def test_normalize_mount_path() -> None:
    assert normalize_mount_path(None) == "/"
    assert normalize_mount_path("") == "/"
    assert normalize_mount_path("/") == "/"
    assert normalize_mount_path("/llm") == "/llm"
    assert normalize_mount_path("/llm/") == "/llm"

    with pytest.raises(ValueError, match="must start with"):
        normalize_mount_path("llm")


def test_probe_payload() -> None:
    payload = probe_payload("ok", llm_mounted=True, llm_prefix="/llm")
    assert payload == {
        "status": "ok",
        "service": "SAGE Edge",
        "llm_mounted": True,
        "llm_prefix": "/llm",
    }
