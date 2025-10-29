"""Minimal usage example for the SageFlow Python bindings.

This script shows how to push vector data into the streaming engine and
observe outputs via a Python sink callback. It is safe to run directly or
via ``python -m sage.middleware.components.sage_flow.examples.basic_service``
once the SageFlow C++ extension has been built.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import numpy as np

try:
    from sage.middleware.components.sage_flow.python import sage_flow as _sf
    from sage.middleware.components.sage_flow.service import SageFlowService
except ImportError as exc:  # pragma: no cover - environment misconfigured
    raise SystemExit(
        "Unable to import SageFlow bindings. Ensure 'sage-middleware' is installed "
        "and the SageFlow extension has been built."
    ) from exc


def _assert_extension_available() -> None:
    """Fail fast with a clear message when the C++ extension is missing."""
    if _sf.Stream is None:
        hint = (
            "SageFlow extension not detected. Build it via 'sage extensions install "
            "sage_flow' or configure the packages/sage-middleware superbuild."
        )
        raise SystemExit(hint)


def _print_sink(name: str) -> Callable[[int, int], None]:
    def _inner(uid: int, timestamp_ms: int) -> None:
        print(f"[{name}] uid={uid}, ts={timestamp_ms}")

    return _inner


def main(seed: int | None = None) -> None:
    _assert_extension_available()

    if seed is not None:
        np.random.seed(seed)

    service = SageFlowService(dim=4)
    service.set_sink(_print_sink("py_sink"))

    for uid in range(5):
        vector = np.random.rand(service.dim).astype(np.float32)
        service.push(uid, vector)

    service.run()

    snapshot = {
        "queued_vectors": 5,
        "sink_name": "py_sink",
        "pid": os.getpid(),
    }
    print("Snapshot:", snapshot)


if __name__ == "__main__":
    main()
