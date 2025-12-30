"""
SAGE Port Configuration

Centralized port configuration for all SAGE services to avoid conflicts.

Port Allocation Strategy:
- 8889: sage-gateway (OpenAI-compatible API Gateway)
- 8001: vLLM/LLM inference service (SAGE recommended, may have issues on WSL2)
- 5173: sage-studio frontend (Vite dev server)
- 8090: Embedding service
- 8900-8999: Benchmark & testing services

Known Issues:
- WSL2: Port 8001 may show as listening but refuse connections due to WSL2
  network stack issues. Use BENCHMARK_LLM (8901) as fallback.

Usage:
    from sage.common.config.ports import SagePorts

    # Get default ports
    port = SagePorts.LLM_DEFAULT

    # Check if port is available
    if SagePorts.is_available(8001):
        ...

    # Get all ports for a service category
    llm_ports = SagePorts.get_llm_ports()

    # For WSL2, use benchmark port as fallback
    port = SagePorts.BENCHMARK_LLM  # 8901 - more reliable on WSL2
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

    Architecture:
        User → Gateway (8889) → LLM (8001)
        User → Studio Frontend (5173) → Gateway (8889)

    Note: Studio Backend has been merged into Gateway.
    """

    # =========================================================================
    # sage-gateway (OpenAI-compatible API Gateway)
    # =========================================================================
    GATEWAY_DEFAULT: ClassVar[int] = 8889  # API Gateway main port (default moved off 8888)

    # =========================================================================
    # sage-edge (L6 aggregator shell)
    # =========================================================================
    EDGE_DEFAULT: ClassVar[int] = 8899  # Edge aggregator (mounts LLM gateway by default)

    # =========================================================================
    # LLM Services (vLLM, etc.)
    # =========================================================================
    LLM_DEFAULT: ClassVar[int] = 8001  # SAGE recommended vLLM port
    LLM_SECONDARY: ClassVar[int] = 8002  # Secondary LLM instance (if needed)
    LLM_WSL_FALLBACK: ClassVar[int] = 8901  # Fallback for WSL2 (same as BENCHMARK_LLM)

    # =========================================================================
    # sage-studio (Frontend only, Backend merged into Gateway)
    # =========================================================================
    STUDIO_BACKEND: ClassVar[int] = 8889  # Deprecated: now same as GATEWAY_DEFAULT
    STUDIO_FRONTEND: ClassVar[int] = 5173  # Studio frontend (Vite dev server)

    # =========================================================================
    # Embedding Services
    # =========================================================================
    EMBEDDING_DEFAULT: ClassVar[int] = 8090  # Primary embedding server
    EMBEDDING_SECONDARY: ClassVar[int] = 8091  # Secondary embedding instance

    # =========================================================================
    # Benchmark & Testing Services (8900-8999)
    # =========================================================================
    BENCHMARK_LLM: ClassVar[int] = 8901  # Benchmark-dedicated LLM server
    BENCHMARK_EMBEDDING: ClassVar[int] = 8902  # Benchmark embedding server
    BENCHMARK_API: ClassVar[int] = 8903  # Benchmark API server

    @classmethod
    def get_recommended_llm_port(cls) -> int:
        """
        Get recommended LLM port based on platform.

        On WSL2, port 8001 may have connectivity issues, so use 8901 as fallback.

        Returns:
            Recommended port number for LLM services
        """
        if is_wsl():
            return cls.LLM_WSL_FALLBACK
        return cls.LLM_DEFAULT

    @classmethod
    def get_llm_ports(cls) -> list[int]:
        """Get all LLM-related ports in priority order.

        Includes fallback ports for WSL2 compatibility.
        """
        return [cls.LLM_DEFAULT, cls.BENCHMARK_LLM, cls.LLM_SECONDARY, cls.GATEWAY_DEFAULT]

    @classmethod
    def get_embedding_ports(cls) -> list[int]:
        """Get all embedding-related ports in priority order."""
        return [cls.EMBEDDING_DEFAULT, cls.EMBEDDING_SECONDARY]

    @classmethod
    def get_benchmark_ports(cls) -> list[int]:
        """Get all benchmark-related ports."""
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
        print("=" * 65)

        if is_wsl():
            print("⚠️  Environment: WSL2 Detected (Port 8001 might be unreliable)")
        else:
            print("✅ Environment: Standard Linux/Unix")

        print("-" * 65)
        print(f"{'Service':<20} | {'Port':<6} | {'Status':<15} | {'Recommendation':<15}")
        print("-" * 65)

        services = [
            ("Gateway", cls.GATEWAY_DEFAULT),
            ("Edge", cls.EDGE_DEFAULT),
            ("LLM (Default)", cls.LLM_DEFAULT),
            ("LLM (WSL/Bench)", cls.LLM_WSL_FALLBACK),
            ("Embedding", cls.EMBEDDING_DEFAULT),
            ("Studio Frontend", cls.STUDIO_FRONTEND),
        ]

        for name, port in services:
            status = cls.check_port_status(port)
            state = "🔴 In Use" if status["is_listening"] else "🟢 Available"

            rec = ""
            if name == "LLM (Default)" and is_wsl():
                rec = "Avoid (WSL)"
            elif name == "LLM (WSL/Bench)" and is_wsl():
                rec = "Recommended"
            elif status["is_listening"]:
                rec = "Check PID"

            print(f"{name:<20} | {port:<6} | {state:<15} | {rec:<15}")

        print("-" * 65)


# Convenience aliases
DEFAULT_LLM_PORT = SagePorts.LLM_DEFAULT
DEFAULT_EMBEDDING_PORT = SagePorts.EMBEDDING_DEFAULT
DEFAULT_BENCHMARK_LLM_PORT = SagePorts.BENCHMARK_LLM

if __name__ == "__main__":
    SagePorts.diagnose()
