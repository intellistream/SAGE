"""Centralized port configuration for the stream-first SAGE core.

This in-tree version intentionally focuses on the current product center:
runtime + serving + optional scale-out execution.
Legacy UI-specific ports are not part of this foundation baseline.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import ClassVar


def is_wsl() -> bool:
    """Return ``True`` when running inside WSL."""
    try:
        with open("/proc/version", encoding="utf-8") as handle:
            return "microsoft" in handle.read().lower()
    except OSError:
        return False


@dataclass(frozen=True)
class SagePorts:
    """Centralized port assignments for serving and runtime surfaces."""

    # Service entrypoints
    SAGELLM_GATEWAY: ClassVar[int] = 8889
    EDGE_DEFAULT: ClassVar[int] = 8899

    # Primary/secondary sageLLM serve + engine pairs
    SAGELLM_SERVE_PORT: ClassVar[int] = 8901
    SAGELLM_ENGINE_PORT: ClassVar[int] = 8902
    SAGELLM_SERVE_PORT_2: ClassVar[int] = 8903
    SAGELLM_ENGINE_PORT_2: ClassVar[int] = 8904

    # Legacy direct engine access
    LLM_DEFAULT: ClassVar[int] = 8001
    LLM_SECONDARY: ClassVar[int] = 8002

    # Embedding services
    EMBEDDING_DEFAULT: ClassVar[int] = 8090
    EMBEDDING_SECONDARY: ClassVar[int] = 8091

    # Benchmark/testing
    BENCHMARK_EMBEDDING: ClassVar[int] = 8950
    BENCHMARK_API: ClassVar[int] = 8951

    # Compatibility aliases
    SAGELLM_DEFAULT: ClassVar[int] = 8001
    GATEWAY_DEFAULT: ClassVar[int] = 8889
    LLM_WSL_FALLBACK: ClassVar[int] = 8901
    BENCHMARK_LLM: ClassVar[int] = 8901

    @classmethod
    def get_recommended_llm_port(cls) -> int:
        """Return the preferred shell port for sageLLM."""
        if is_wsl():
            return cls.SAGELLM_SERVE_PORT
        return cls.LLM_DEFAULT

    @classmethod
    def get_llm_ports(cls) -> list[int]:
        """Return serve/gateway ports in priority order."""
        return [
            cls.SAGELLM_SERVE_PORT,
            cls.SAGELLM_SERVE_PORT_2,
            cls.LLM_DEFAULT,
            cls.SAGELLM_GATEWAY,
        ]

    @classmethod
    def get_embedding_ports(cls) -> list[int]:
        """Return embedding-related ports in priority order."""
        return [cls.EMBEDDING_DEFAULT, cls.EMBEDDING_SECONDARY]

    @classmethod
    def get_benchmark_ports(cls) -> list[int]:
        """Return benchmark ports."""
        return [cls.BENCHMARK_LLM, cls.BENCHMARK_EMBEDDING, cls.BENCHMARK_API]

    @classmethod
    def is_available(cls, port: int, host: str = "localhost") -> bool:
        """Return whether a port can be bound."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                return sock.connect_ex((host, port)) != 0
        except OSError:
            return True

    @classmethod
    def find_available_port(cls, start: int = 8900, end: int = 8999) -> int | None:
        """Find the first available port in ``[start, end]``."""
        for port in range(start, end + 1):
            if cls.is_available(port):
                return port
        return None

    @classmethod
    def get_from_env(cls, env_var: str, default: int) -> int:
        """Read a port from the environment with integer fallback."""
        value = os.environ.get(env_var)
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return default

    @classmethod
    def check_port_status(cls, port: int, host: str = "localhost") -> dict[str, object]:
        """Return listening/availability status for one port."""
        is_listening = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                is_listening = sock.connect_ex((host, port)) == 0
        except OSError:
            pass

        return {
            "port": port,
            "is_available": not is_listening,
            "is_listening": is_listening,
        }

    @classmethod
    def diagnose(cls) -> None:
        """Print a small diagnostic report for core SAGE ports."""
        print("=" * 65)
        print("🔍 SAGE Port Diagnostic Tool")
        print("=" * 70)

        if is_wsl():
            print("⚠️  Environment: WSL2 detected (prefer 8901 over legacy 8001)")
        else:
            print("✅ Environment: Standard Linux/Unix")

        print()

        groups: list[tuple[str, list[tuple[str, int]]]] = [
            (
                "Serving Entry Points",
                [
                    ("sageLLM Gateway", cls.SAGELLM_GATEWAY),
                    ("Edge Aggregator", cls.EDGE_DEFAULT),
                ],
            ),
            (
                "sageLLM Inference Engine",
                [
                    ("Serve shell #1 (--port)", cls.SAGELLM_SERVE_PORT),
                    ("Real engine #1 (--engine-port)", cls.SAGELLM_ENGINE_PORT),
                    ("Serve shell #2 (--port)", cls.SAGELLM_SERVE_PORT_2),
                    ("Real engine #2 (--engine-port)", cls.SAGELLM_ENGINE_PORT_2),
                    ("Legacy direct", cls.LLM_DEFAULT),
                ],
            ),
            (
                "Embedding Services",
                [
                    ("Embedding primary", cls.EMBEDDING_DEFAULT),
                    ("Embedding secondary", cls.EMBEDDING_SECONDARY),
                ],
            ),
            (
                "Benchmark & Testing",
                [
                    ("Benchmark LLM", cls.BENCHMARK_LLM),
                    ("Benchmark Embedding", cls.BENCHMARK_EMBEDDING),
                    ("Benchmark API", cls.BENCHMARK_API),
                ],
            ),
        ]

        for group_name, services in groups:
            print(f"── {group_name} {'─' * (50 - len(group_name))}")
            print(f"  {'Service':<32} {'Port':<6}  Status")
            for name, port in services:
                status = cls.check_port_status(port)
                state = "🔴 listening" if status["is_listening"] else "○  available"
                print(f"  {name:<32} {port:<6}  {state}")
            print()

        print("=" * 70)


DEFAULT_SAGELLM_PORT = SagePorts.SAGELLM_SERVE_PORT
DEFAULT_LLM_PORT = SagePorts.LLM_DEFAULT
DEFAULT_EMBEDDING_PORT = SagePorts.EMBEDDING_DEFAULT
DEFAULT_BENCHMARK_LLM_PORT = SagePorts.BENCHMARK_LLM


if __name__ == "__main__":
    SagePorts.diagnose()
