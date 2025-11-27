"""
SAGE Port Configuration

Centralized port configuration for all SAGE services to avoid conflicts.

Port Allocation Strategy:
- 8000-8099: Core services (vLLM, OpenAI-compatible APIs)
- 8100-8199: Studio & UI services
- 8200-8299: Gateway & API routing
- 8300-8399: Embedding services
- 8900-8999: Benchmark & testing services

Usage:
    from sage.common.config.ports import SagePorts

    # Get default ports
    port = SagePorts.LLM_DEFAULT

    # Check if port is available
    if SagePorts.is_available(8001):
        ...

    # Get all ports for a service category
    llm_ports = SagePorts.get_llm_ports()
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class SagePorts:
    """
    Centralized port configuration for SAGE services.

    All port numbers are defined here to prevent conflicts between services.
    """

    # =========================================================================
    # Core LLM Services (8000-8099)
    # =========================================================================
    LLM_DEFAULT: ClassVar[int] = 8001  # Primary vLLM server
    LLM_VLLM_DEFAULT: ClassVar[int] = 8000  # vLLM's own default
    LLM_SECONDARY: ClassVar[int] = 8002  # Secondary LLM instance

    # =========================================================================
    # Studio & UI Services (8100-8199)
    # =========================================================================
    STUDIO_BACKEND: ClassVar[int] = 8080  # Studio API backend (legacy, using 8080)
    STUDIO_FRONTEND: ClassVar[int] = 5173  # Studio frontend dev server (Vite default)
    STUDIO_WEBSOCKET: ClassVar[int] = 8102  # Studio WebSocket server

    # =========================================================================
    # Gateway & API Routing (8000, 8200-8299)
    # =========================================================================
    GATEWAY_DEFAULT: ClassVar[int] = 8000  # API Gateway (OpenAI-compatible endpoint)
    GATEWAY_ADMIN: ClassVar[int] = 8201  # Gateway admin API

    # =========================================================================
    # Embedding Services (8300-8399)
    # =========================================================================
    EMBEDDING_DEFAULT: ClassVar[int] = 8300  # Primary embedding server
    EMBEDDING_SECONDARY: ClassVar[int] = 8301  # Secondary embedding instance

    # =========================================================================
    # Benchmark & Testing Services (8900-8999)
    # =========================================================================
    BENCHMARK_LLM: ClassVar[int] = 8901  # Benchmark-dedicated LLM server
    BENCHMARK_EMBEDDING: ClassVar[int] = 8902  # Benchmark embedding server
    BENCHMARK_API: ClassVar[int] = 8903  # Benchmark API server

    # =========================================================================
    # Legacy/Compatibility Ports
    # =========================================================================
    LEGACY_EMBEDDING_8080: ClassVar[int] = 8080  # Old embedding port
    LEGACY_EMBEDDING_8090: ClassVar[int] = 8090  # Old embedding port

    @classmethod
    def get_llm_ports(cls) -> list[int]:
        """Get all LLM-related ports in priority order."""
        return [cls.LLM_DEFAULT, cls.LLM_VLLM_DEFAULT, cls.LLM_SECONDARY]

    @classmethod
    def get_embedding_ports(cls) -> list[int]:
        """Get all embedding-related ports in priority order."""
        return [
            cls.EMBEDDING_DEFAULT,
            cls.EMBEDDING_SECONDARY,
            cls.LEGACY_EMBEDDING_8090,
            cls.LEGACY_EMBEDDING_8080,
        ]

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


# Convenience aliases
DEFAULT_LLM_PORT = SagePorts.LLM_DEFAULT
DEFAULT_EMBEDDING_PORT = SagePorts.EMBEDDING_DEFAULT
DEFAULT_BENCHMARK_LLM_PORT = SagePorts.BENCHMARK_LLM
