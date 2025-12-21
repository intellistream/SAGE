# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Strategy Adapter Module
=======================

Provides adapters for Control Plane scheduling strategies.

This module bridges the benchmark framework with the actual strategy
implementations in sage.common.components.sage_llm.sageLLM.control_plane.strategies
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Try to import strategies, provide fallback if not available
try:
    from sage.common.components.sage_llm.sageLLM.control_plane.strategies import (
        AdaptivePolicy,
        AegaeonPolicy,
        CostOptimizedPolicy,
        FIFOPolicy,
        HybridSchedulingPolicy,
        PriorityPolicy,
        SchedulingPolicy,
        SLOAwarePolicy,
    )

    STRATEGIES_AVAILABLE = True
except ImportError:
    STRATEGIES_AVAILABLE = False
    SchedulingPolicy = None  # type: ignore[assignment, misc]
    FIFOPolicy = None  # type: ignore[assignment, misc]
    PriorityPolicy = None  # type: ignore[assignment, misc]
    SLOAwarePolicy = None  # type: ignore[assignment, misc]
    CostOptimizedPolicy = None  # type: ignore[assignment, misc]
    AdaptivePolicy = None  # type: ignore[assignment, misc]
    AegaeonPolicy = None  # type: ignore[assignment, misc]
    HybridSchedulingPolicy = None  # type: ignore[assignment, misc]
    logger.warning("Control Plane strategies not available. Install sage-common package.")


class StrategyInfo:
    """Information about a scheduling strategy."""

    def __init__(
        self,
        name: str,
        cls: type | None,
        description: str,
        supports_llm: bool = True,
        supports_embedding: bool = False,
        is_hybrid: bool = False,
    ):
        """Initialize strategy info.

        Args:
            name: Strategy name (used in config)
            cls: Strategy class
            description: Human-readable description
            supports_llm: Whether strategy supports LLM requests
            supports_embedding: Whether strategy supports embedding requests
            is_hybrid: Whether strategy is a hybrid scheduler
        """
        self.name = name
        self.cls = cls
        self.description = description
        self.supports_llm = supports_llm
        self.supports_embedding = supports_embedding
        self.is_hybrid = is_hybrid

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "supports_llm": self.supports_llm,
            "supports_embedding": self.supports_embedding,
            "is_hybrid": self.is_hybrid,
            "available": self.cls is not None,
        }


class StrategyAdapter:
    """Adapter for Control Plane scheduling strategies.

    This class provides a uniform interface to:
    - List available strategies
    - Create strategy instances
    - Get strategy information
    - Switch strategies on a running Control Plane

    Example:
        # List available strategies
        strategies = StrategyAdapter.list_strategies()

        # Create a strategy instance
        fifo = StrategyAdapter.get_strategy("fifo")

        # Get strategy info
        info = StrategyAdapter.get_strategy_info("hybrid")
    """

    # Strategy registry
    _STRATEGIES: dict[str, StrategyInfo] = {
        "fifo": StrategyInfo(
            name="fifo",
            cls=FIFOPolicy if STRATEGIES_AVAILABLE else None,
            description="First-In-First-Out scheduling",
            supports_llm=True,
            supports_embedding=False,
        ),
        "priority": StrategyInfo(
            name="priority",
            cls=PriorityPolicy if STRATEGIES_AVAILABLE else None,
            description="Priority-based scheduling",
            supports_llm=True,
            supports_embedding=False,
        ),
        "slo_aware": StrategyInfo(
            name="slo_aware",
            cls=SLOAwarePolicy if STRATEGIES_AVAILABLE else None,
            description="SLO deadline-aware scheduling",
            supports_llm=True,
            supports_embedding=False,
        ),
        "cost_optimized": StrategyInfo(
            name="cost_optimized",
            cls=CostOptimizedPolicy if STRATEGIES_AVAILABLE else None,
            description="Cost-optimized scheduling",
            supports_llm=True,
            supports_embedding=False,
        ),
        "adaptive": StrategyInfo(
            name="adaptive",
            cls=AdaptivePolicy if STRATEGIES_AVAILABLE else None,
            description="Adaptive strategy selection based on system state",
            supports_llm=True,
            supports_embedding=False,
        ),
        "aegaeon": StrategyInfo(
            name="aegaeon",
            cls=AegaeonPolicy if STRATEGIES_AVAILABLE else None,
            description="Advanced Aegaeon scheduling with multiple optimizations",
            supports_llm=True,
            supports_embedding=False,
        ),
        "hybrid": StrategyInfo(
            name="hybrid",
            cls=HybridSchedulingPolicy if STRATEGIES_AVAILABLE else None,
            description="Hybrid LLM + Embedding mixed scheduling",
            supports_llm=True,
            supports_embedding=True,
            is_hybrid=True,
        ),
    }

    @classmethod
    def is_available(cls) -> bool:
        """Check if strategies are available.

        Returns:
            True if strategies can be imported
        """
        return STRATEGIES_AVAILABLE

    @classmethod
    def list_strategies(cls, include_hybrid: bool = True) -> list[str]:
        """List available strategy names.

        Args:
            include_hybrid: Whether to include hybrid strategies

        Returns:
            List of strategy names
        """
        if include_hybrid:
            return list(cls._STRATEGIES.keys())
        return [name for name, info in cls._STRATEGIES.items() if not info.is_hybrid]

    @classmethod
    def list_llm_strategies(cls) -> list[str]:
        """List strategies that support LLM requests.

        Returns:
            List of LLM-capable strategy names
        """
        return [name for name, info in cls._STRATEGIES.items() if info.supports_llm]

    @classmethod
    def list_embedding_strategies(cls) -> list[str]:
        """List strategies that support embedding requests.

        Returns:
            List of embedding-capable strategy names
        """
        return [name for name, info in cls._STRATEGIES.items() if info.supports_embedding]

    @classmethod
    def list_hybrid_strategies(cls) -> list[str]:
        """List hybrid strategies.

        Returns:
            List of hybrid strategy names
        """
        return [name for name, info in cls._STRATEGIES.items() if info.is_hybrid]

    @classmethod
    def get_strategy_info(cls, name: str) -> StrategyInfo | None:
        """Get information about a strategy.

        Args:
            name: Strategy name

        Returns:
            StrategyInfo or None if not found
        """
        return cls._STRATEGIES.get(name)

    @classmethod
    def get_all_strategy_info(cls) -> dict[str, StrategyInfo]:
        """Get information about all strategies.

        Returns:
            Dictionary mapping strategy names to StrategyInfo
        """
        return cls._STRATEGIES.copy()

    @classmethod
    def get_strategy(cls, name: str, **config: Any) -> Any:
        """Get a strategy instance.

        Args:
            name: Strategy name
            **config: Configuration to pass to strategy constructor

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy not found
            RuntimeError: If strategies not available
        """
        if not STRATEGIES_AVAILABLE:
            raise RuntimeError(
                "Control Plane strategies not available. Install sage-common package."
            )

        info = cls._STRATEGIES.get(name)
        if info is None:
            raise ValueError(f"Unknown strategy: {name}. Available: {cls.list_strategies()}")

        if info.cls is None:
            raise RuntimeError(f"Strategy {name} class not available")

        # Create instance
        try:
            if config:
                return info.cls(**config)
            return info.cls()
        except Exception as e:
            logger.error(f"Failed to create strategy {name}: {e}")
            raise

    @classmethod
    def get_strategy_class(cls, name: str) -> type | None:
        """Get the strategy class (not instance).

        Args:
            name: Strategy name

        Returns:
            Strategy class or None
        """
        info = cls._STRATEGIES.get(name)
        return info.cls if info else None

    @classmethod
    async def switch_policy(
        cls,
        control_plane_url: str,
        policy_name: str,
        timeout: float = 10.0,
    ) -> bool:
        """Switch scheduling policy on a running Control Plane.

        This sends a policy switch request to the Control Plane API.

        Args:
            control_plane_url: Control Plane URL (e.g., "http://localhost:8888")
            policy_name: Name of policy to switch to
            timeout: Request timeout in seconds

        Returns:
            True if switch was successful

        Note:
            This requires the Control Plane to support the /admin/policy endpoint.
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"{control_plane_url.rstrip('/')}/admin/policy"
                async with session.post(
                    url,
                    json={"policy": policy_name},
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status == 200:
                        logger.info(f"Switched policy to {policy_name}")
                        return True
                    else:
                        text = await response.text()
                        logger.warning(f"Policy switch failed: {response.status} - {text}")
                        return False

        except ImportError:
            logger.error("aiohttp required for policy switching")
            return False
        except Exception as e:
            logger.error(f"Error switching policy: {e}")
            return False

    @classmethod
    def validate_policy(cls, policy_name: str, benchmark_type: str = "llm") -> list[str]:
        """Validate if a policy is suitable for a benchmark type.

        Args:
            policy_name: Policy name to validate
            benchmark_type: Type of benchmark ("llm", "embedding", "hybrid")

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        info = cls._STRATEGIES.get(policy_name)
        if info is None:
            errors.append(f"Unknown policy: {policy_name}")
            return errors

        if info.cls is None:
            errors.append(f"Policy {policy_name} is not available (missing dependency)")

        if benchmark_type == "embedding" and not info.supports_embedding:
            errors.append(f"Policy {policy_name} does not support embedding requests")

        if benchmark_type == "hybrid" and not info.is_hybrid:
            errors.append(
                f"Policy {policy_name} is not a hybrid policy. "
                f"Use one of: {cls.list_hybrid_strategies()}"
            )

        return errors
