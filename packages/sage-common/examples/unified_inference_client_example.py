#!/usr/bin/env python3
"""Example: Using UnifiedInferenceClient from sagellm / isagellm.

Prerequisites:
    pip install --upgrade isagellm

Note:
    UnifiedInferenceClient requires sagellm >= 0.5.3 and Python >= 3.10.
    Run ``pip install --upgrade isagellm`` if any pre-flight check fails.
"""

from __future__ import annotations

import sys

# ── Minimum requirements ──────────────────────────────────────────────────────
_MIN_PYTHON = (3, 10)
_MIN_SAGELLM = (0, 5, 3)
_REQUIRED_METHODS = ("complete", "chat", "health")


def _version_tuple(version_str: str) -> tuple[int, ...]:
    """Parse 'X.Y.Z[.W]' into a comparable int tuple, ignoring trailing parts."""
    try:
        return tuple(int(x) for x in version_str.split(".")[:3])
    except ValueError:
        return (0,)


def _preflight_checks() -> type:
    """Run all pre-flight checks and return UnifiedInferenceClient, or abort."""

    # 1. Python version
    if sys.version_info < _MIN_PYTHON:
        raise SystemExit(
            f"ERROR: Python {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}+ is required "
            f"(you have {sys.version.split()[0]}).\n"
            "Please upgrade your Python environment."
        )

    # 2. sagellm installed
    try:
        import sagellm  # noqa: PLC0415
    except ImportError:
        raise SystemExit(
            "ERROR: sagellm (isagellm) is not installed.\n"
            "Install it with:\n"
            "    pip install isagellm"
        )

    # 3. sagellm version
    installed_ver = getattr(sagellm, "__version__", "0.0.0")
    if _version_tuple(installed_ver) < _MIN_SAGELLM:
        raise SystemExit(
            f"ERROR: sagellm {installed_ver} is too old "
            f"(need >= {'.'.join(str(x) for x in _MIN_SAGELLM)}).\n"
            "Upgrade with:\n"
            "    pip install --upgrade isagellm"
        )

    # 4. UnifiedInferenceClient exported from the public API
    try:
        from sagellm import UnifiedInferenceClient  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(
            f"ERROR: UnifiedInferenceClient is not available in sagellm {installed_ver}.\n"
            f"Detail: {exc}\n"
            "Upgrade with:\n"
            "    pip install --upgrade isagellm"
        )

    # 5. Required methods present on the class
    missing = [
        m for m in _REQUIRED_METHODS if not callable(getattr(UnifiedInferenceClient, m, None))
    ]
    if missing:
        raise SystemExit(
            f"ERROR: UnifiedInferenceClient in sagellm {installed_ver} is missing "
            f"required method(s): {', '.join(missing)}.\n"
            "Upgrade with:\n"
            "    pip install --upgrade isagellm"
        )

    return UnifiedInferenceClient


def main():
    """Demo unified inference client usage."""
    UnifiedInferenceClient = _preflight_checks()

    # 6. Instantiation check (offline_mode=True — no server required for demo)
    try:
        client = UnifiedInferenceClient(
            base_url="http://localhost:8000",
            offline_mode=True,
        )
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"ERROR: Failed to instantiate UnifiedInferenceClient: {exc}")

    # Simple completion (wraps /v1/chat/completions)
    response = client.complete(
        prompt="Hello, world!",
        max_tokens=100,
    )
    print(f"complete() response: {response}")

    # Multi-turn chat
    chat_response = client.chat(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is SAGE?"},
        ],
        max_tokens=100,
    )
    print(f"chat() response: {chat_response}")

    # Health check (offline mode returns True — no real server needed for demo)
    healthy = client.health()
    print(f"health(): {healthy}")


if __name__ == "__main__":
    main()
