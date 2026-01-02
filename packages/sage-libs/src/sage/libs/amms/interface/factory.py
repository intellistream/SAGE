"""Factory functions for creating AMM algorithm instances.

Provides high-level convenience functions for algorithm creation.
"""

from __future__ import annotations

from typing import Any

from sage.libs.amms.interface.base import AmmIndex
from sage.libs.amms.interface.registry import create_amm_index as _create
from sage.libs.amms.interface.registry import get_meta, registered

__all__ = [
    "create",
    "registered",
    "get_meta",
]


def create(algorithm: str, config: dict[str, Any] | None = None, **kwargs: Any) -> AmmIndex:
    """Create an AMM algorithm instance.

    Args:
        algorithm: Algorithm name (e.g., "countsketch", "fastjlt")
        config: Algorithm configuration dictionary
        **kwargs: Additional keyword arguments merged with config

    Returns:
        Configured AmmIndex instance

    Example:
        >>> amm = create("countsketch", config={"sketch_size": 1000})
        >>> result = amm.multiply(matrix_a, matrix_b)

        >>> amm = create("fastjlt", sketch_size=500, use_gpu=False)
        >>> result = amm.multiply(matrix_a, matrix_b)
    """
    # Merge config dict with kwargs
    merged_config = {}
    if config is not None:
        merged_config.update(config)
    merged_config.update(kwargs)

    return _create(algorithm, **merged_config)
