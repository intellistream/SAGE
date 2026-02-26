#!/usr/bin/env python3
"""Example: Using UnifiedInferenceClient from sagellm / isagellm.

Prerequisites:
    pip install --upgrade isagellm

Note:
    UnifiedInferenceClient was added to sagellm in version 0.5.3.x (dev).
    If ``from sagellm import UnifiedInferenceClient`` fails on your installed
    version, the example automatically falls back to the direct submodule
    import ``from sagellm.client import UnifiedInferenceClient``.
"""

from __future__ import annotations


def _import_client():
    """Try multiple import paths for backwards compatibility.

    Returns the class, or None if sagellm is not installed / too old.
    """
    # Preferred: public API via sagellm umbrella __init__
    try:
        from sagellm import UnifiedInferenceClient

        return UnifiedInferenceClient
    except (ImportError, AttributeError):
        pass

    # Fallback: direct submodule import (works even when the installed
    # sagellm __init__.py predates the lazy-import registration).
    try:
        from sagellm.client import UnifiedInferenceClient

        return UnifiedInferenceClient
    except (ImportError, AttributeError):
        pass

    return None


def main():
    """Demo unified inference client usage."""
    UnifiedInferenceClient = _import_client()
    if UnifiedInferenceClient is None:
        print(
            "UnifiedInferenceClient not found.\n"
            "Please install or upgrade sagellm:\n"
            "    pip install --upgrade isagellm\n"
            "Or install from source:\n"
            "    pip install -e /path/to/sagellm"
        )
        return

    # Create client (offline_mode=True — no running server required for demo)
    client = UnifiedInferenceClient(
        base_url="http://localhost:8000",
        offline_mode=True,
    )

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
