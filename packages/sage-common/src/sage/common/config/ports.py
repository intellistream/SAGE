"""
SAGE Port Configuration

Centralized port configuration for all SAGE services to avoid conflicts.

Port Allocation Map
───────────────────────────────────────────────────────────────────────
Group 1 · Platform Services
  5173   STUDIO_FRONTEND   Vite dev server (sage-studio)
  8765   STUDIO_BACKEND    Studio FastAPI backend (auth, flows, pipeline builder)
  8889   SAGELLM_GATEWAY   sageLLM Gateway — OpenAI-compatible API entry point
  8899   EDGE_DEFAULT      sage-edge aggregator shell

Group 2 · sageLLM Inference Engine  (sage-llm serve --port SHELL --engine-port ENGINE)
  Each `sage-llm serve` spawns a SHELL process (gateway+control-plane proxy)
  and a REAL ENGINE process (actual vLLM/HF inference). Default: ENGINE = SHELL + 1.

  Instance 1 (primary)
    8901   SAGELLM_SERVE_PORT    sage-llm serve --port  (shell / proxy process)
    8902   SAGELLM_ENGINE_PORT   sage-llm serve --engine-port  (real vLLM engine)

  Instance 2 (secondary / second model)
    8903   SAGELLM_SERVE_PORT_2  second shell process
    8904   SAGELLM_ENGINE_PORT_2 second real vLLM engine

  Legacy / non-WSL2 default
    8001   LLM_DEFAULT / SAGELLM_DEFAULT  (may be unreliable on WSL2)

Group 3 · Embedding Services
  8090   EMBEDDING_DEFAULT   Primary embedding server (CPU, e.g. BAAI/bge-*)
  8091   EMBEDDING_SECONDARY Secondary embedding instance

Group 4 · Benchmark & Testing (8950-8959, clearly separate from inference)
  8950   BENCHMARK_EMBEDDING Benchmark-dedicated embedding server
  8951   BENCHMARK_API       Benchmark API server

─── Backward-Compat Aliases ─────────────────────────────────────────
  BENCHMARK_LLM   = SAGELLM_SERVE_PORT (8901) — deprecated name, same port
  LLM_WSL_FALLBACK = SAGELLM_SERVE_PORT (8901) — deprecated, same port
  GATEWAY_DEFAULT  = SAGELLM_GATEWAY   (8889) — deprecated, same port
───────────────────────────────────────────────────────────────────────

Known Issues:
- WSL2: Port 8001 (LLM_DEFAULT) may show as listening but refuse connections.
  Use SAGELLM_SERVE_PORT (8901) instead.

Usage:
    from sage.common.config.ports import SagePorts

    port = SagePorts.SAGELLM_SERVE_PORT   # primary sageLLM shell port
    port = SagePorts.SAGELLM_ENGINE_PORT  # corresponding real vLLM engine port

    if SagePorts.is_available(SagePorts.SAGELLM_GATEWAY):
        ...

    llm_ports = SagePorts.get_llm_ports()
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import ClassVar


def is_wsl() -> bool:
    """Check if running in WSL (Windows Subsystem for Linux)."""
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


@dataclass(frozen=True)
class SagePorts:
    """
    Centralized port configuration for SAGE services.

    All port numbers are defined here to prevent conflicts between services.

    Architecture overview:
        Browser/Client
          → Studio Frontend  :5173  (Vite dev)
          → SAGELLM Gateway  :8889  ←─── primary API entry point
               ↓ routes to sageLLM engine shell
             sageLLM shell   :8901  (sage-llm serve --port)
               ↓ forwards inference requests
             real vLLM       :8902  (sage-llm serve --engine-port)
    """

    # =========================================================================
    # Group 1: Platform Services
    # =========================================================================
    STUDIO_FRONTEND: ClassVar[int] = 5173  # Vite dev server (sage-studio)
    STUDIO_BACKEND: ClassVar[int] = 8765  # Studio FastAPI backend (auth, flows, pipeline builder)
    SAGELLM_GATEWAY: ClassVar[int] = 8889  # sageLLM Gateway — OpenAI-compatible API entry point
    EDGE_DEFAULT: ClassVar[int] = 8899  # sage-edge aggregator shell

    # =========================================================================
    # Group 2: sageLLM Inference Engine
    #
    # `sage-llm serve` spawns two processes per model:
    #   SHELL   — gateway + control-plane proxy  (--port SHELL)
    #   ENGINE  — real vLLM / HF inference        (--engine-port ENGINE, default = SHELL + 1)
    #
    # Pair convention: ENGINE = SHELL + 1
    # =========================================================================
    # Instance 1 (primary / first loaded model)
    SAGELLM_SERVE_PORT: ClassVar[int] = 8901  # sage-llm --port  (shell process)
    SAGELLM_ENGINE_PORT: ClassVar[int] = 8902  # sage-llm --engine-port  (real vLLM)

    # Instance 2 (secondary / second loaded model)
    SAGELLM_SERVE_PORT_2: ClassVar[int] = 8903  # second shell process
    SAGELLM_ENGINE_PORT_2: ClassVar[int] = 8904  # second real vLLM engine

    # Legacy non-WSL2 default (vLLM direct, without sageLLM shell wrapper)
    LLM_DEFAULT: ClassVar[int] = 8001  # vLLM direct port (may be unreliable on WSL2)
    LLM_SECONDARY: ClassVar[int] = 8002  # Secondary LLM instance

    # =========================================================================
    # Group 3: Embedding Services
    # =========================================================================
    EMBEDDING_DEFAULT: ClassVar[int] = 8090  # Primary embedding server (e.g. BAAI/bge-*)
    EMBEDDING_SECONDARY: ClassVar[int] = 8091  # Secondary embedding instance

    # =========================================================================
    # Group 4: Benchmark & Testing Services (8950-8959, separate from inference)
    # =========================================================================
    BENCHMARK_EMBEDDING: ClassVar[int] = 8950  # Benchmark-dedicated embedding server
    BENCHMARK_API: ClassVar[int] = 8951  # Benchmark API server

    # =========================================================================
    # Backward-compat aliases (deprecated — use the named constants above)
    # =========================================================================
    SAGELLM_DEFAULT: ClassVar[int] = 8001  # Deprecated → LLM_DEFAULT
    GATEWAY_DEFAULT: ClassVar[int] = 8889  # Deprecated → SAGELLM_GATEWAY
    LLM_WSL_FALLBACK: ClassVar[int] = 8901  # Deprecated → SAGELLM_SERVE_PORT
    BENCHMARK_LLM: ClassVar[int] = 8901  # Deprecated → SAGELLM_SERVE_PORT

    @classmethod
    def get_recommended_llm_port(cls) -> int:
        """
        Get recommended port for a sageLLM shell process.

        On WSL2 port 8001 may have connectivity issues; use SAGELLM_SERVE_PORT (8901).

        Returns:
            Recommended shell port for sageLLM serve
        """
        if is_wsl():
            return cls.SAGELLM_SERVE_PORT
        return cls.LLM_DEFAULT

    @classmethod
    def get_llm_ports(cls) -> list[int]:
        """Get sageLLM shell ports in priority order (also includes legacy vLLM direct port)."""
        return [
            cls.SAGELLM_SERVE_PORT,
            cls.SAGELLM_SERVE_PORT_2,
            cls.LLM_DEFAULT,
            cls.SAGELLM_GATEWAY,
        ]

    @classmethod
    def get_embedding_ports(cls) -> list[int]:
        """Get all embedding-related ports in priority order."""
        return [cls.EMBEDDING_DEFAULT, cls.EMBEDDING_SECONDARY]

    @classmethod
    def get_benchmark_ports(cls) -> list[int]:
        """Get benchmark-dedicated ports (8950+, separate from inference engine ports)."""
        return [cls.BENCHMARK_LLM, cls.BENCHMARK_EMBEDDING, cls.BENCHMARK_API]

    @classmethod
    def is_available(cls, port: int, host: str = "localhost") -> bool:
        """
        Check if a port is available for binding.

        Args:
            port: Port number to check
            host: Host to check (default: localhost)

        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result != 0  # 0 means connection succeeded (port in use)
        except OSError:
            return True  # Assume available if we can't check

    @classmethod
    def find_available_port(cls, start: int = 8900, end: int = 8999) -> int | None:
        """
        Find an available port in the given range.

        Args:
            start: Start of port range (inclusive)
            end: End of port range (inclusive)

        Returns:
            Available port number, or None if no port available
        """
        for port in range(start, end + 1):
            if cls.is_available(port):
                return port
        return None

    @classmethod
    def get_from_env(cls, env_var: str, default: int) -> int:
        """
        Get port from environment variable with fallback to default.

        Args:
            env_var: Environment variable name
            default: Default port if env var not set

        Returns:
            Port number
        """
        value = os.environ.get(env_var)
        if value:
            try:
                return int(value)
            except ValueError:
                pass
        return default

    @classmethod
    def check_port_status(cls, port: int, host: str = "localhost") -> dict:
        """
        Check detailed status of a port.

        Returns:
            dict: {
                "port": int,
                "is_available": bool,  # True if port is free (can bind), False if in use
                "is_listening": bool,  # True if something is listening (connect success)
            }
        """
        is_listening = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex((host, port))
                if result == 0:
                    is_listening = True
        except OSError:
            pass

        return {
            "port": port,
            "is_available": not is_listening,
            "is_listening": is_listening,
        }

    @classmethod
    def diagnose(cls) -> None:
        """Print a diagnostic report of all SAGE ports."""
        print("=" * 65)
        print("🔍 SAGE Port Diagnostic Tool")
        print("=" * 70)

        if is_wsl():
            print("⚠️  Environment: WSL2 Detected (Port 8001 may be unreliable — use 8901)")
        else:
            print("✅ Environment: Standard Linux/Unix")

        print()

        groups: list[tuple[str, list[tuple[str, int]]]] = [
            (
                "Platform Services",
                [
                    ("Studio Frontend (Vite)", cls.STUDIO_FRONTEND),
                    ("Studio Backend (FastAPI)", cls.STUDIO_BACKEND),
                    ("sageLLM Gateway", cls.SAGELLM_GATEWAY),
                    ("Edge Aggregator", cls.EDGE_DEFAULT),
                ],
            ),
            (
                "sageLLM Inference Engine",
                [
                    ("Serve shell #1  (--port)", cls.SAGELLM_SERVE_PORT),
                    ("Real engine #1 (--engine-port)", cls.SAGELLM_ENGINE_PORT),
                    ("Serve shell #2  (--port)", cls.SAGELLM_SERVE_PORT_2),
                    ("Real engine #2 (--engine-port)", cls.SAGELLM_ENGINE_PORT_2),
                    ("vLLM direct (non-WSL2)", cls.LLM_DEFAULT),
                ],
            ),
            (
                "Embedding Services",
                [
                    ("Embedding (primary)", cls.EMBEDDING_DEFAULT),
                    ("Embedding (secondary)", cls.EMBEDDING_SECONDARY),
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


# Convenience aliases (backward-compat — prefer accessing SagePorts directly)
DEFAULT_SAGELLM_PORT = SagePorts.SAGELLM_SERVE_PORT  # primary sageLLM shell port
DEFAULT_LLM_PORT = SagePorts.LLM_DEFAULT  # legacy vLLM direct port
DEFAULT_EMBEDDING_PORT = SagePorts.EMBEDDING_DEFAULT
DEFAULT_BENCHMARK_LLM_PORT = SagePorts.BENCHMARK_LLM  # deprecated, same as SAGELLM_SERVE_PORT

if __name__ == "__main__":
    SagePorts.diagnose()
