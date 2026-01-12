#!/usr/bin/env python3
"""Example: Using UnifiedInferenceClient from isagellm.

Prerequisites:
    pip install isagellm>=0.1.0
"""

from __future__ import annotations


def main():
    """Demo unified inference client usage."""
    try:
        from sagellm import UnifiedInferenceClient
    except ImportError:
        print("Please install isagellm: pip install isagellm")
        return

    # Create client (mock mode for demo)
    client = UnifiedInferenceClient(
        base_url="http://localhost:8000",
        mock_mode=True,
    )

    # Simple completion
    response = client.complete(
        prompt="Hello, world!",
        max_tokens=100,
    )
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
