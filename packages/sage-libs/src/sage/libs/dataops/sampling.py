"""Sampling, filtering, and bucketing utilities."""

from __future__ import annotations

import random
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def random_sample(items: list[T], k: int, seed: int | None = None) -> list[T]:
    """Randomly sample k items.

    Args:
        items: List of items
        k: Number of items to sample
        seed: Random seed for reproducibility

    Returns:
        List of sampled items
    """
    if seed is not None:
        random.seed(seed)

    return random.sample(items, min(k, len(items)))


def stratified_sample(
    items: list[T],
    k: int,
    key_fn: Callable[[T], Any],
    seed: int | None = None,
) -> list[T]:
    """Stratified sampling by key function.

    Args:
        items: List of items
        k: Total number of items to sample
        key_fn: Function to extract stratification key
        seed: Random seed for reproducibility

    Returns:
        List of sampled items
    """
    from collections import defaultdict

    if seed is not None:
        random.seed(seed)

    # Group by key
    groups: dict[Any, list[T]] = defaultdict(list)
    for item in items:
        key = key_fn(item)
        groups[key].append(item)

    # Sample proportionally from each group
    result = []
    items_per_group = max(1, k // len(groups))

    for group_items in groups.values():
        sampled = random.sample(group_items, min(items_per_group, len(group_items)))
        result.extend(sampled)

    # If we need more items, sample randomly from all
    if len(result) < k:
        remaining = [item for item in items if item not in result]
        additional = random.sample(remaining, min(k - len(result), len(remaining)))
        result.extend(additional)

    return result[:k]


def reservoir_sample(items: list[T], k: int, seed: int | None = None) -> list[T]:
    """Reservoir sampling for streaming scenarios.

    Args:
        items: List of items
        k: Number of items to sample
        seed: Random seed for reproducibility

    Returns:
        List of sampled items
    """
    if seed is not None:
        random.seed(seed)

    reservoir = []

    for i, item in enumerate(items):
        if i < k:
            reservoir.append(item)
        else:
            j = random.randint(0, i)
            if j < k:
                reservoir[j] = item

    return reservoir


def bucket_by(items: list[T], key_fn: Callable[[T], Any]) -> dict[Any, list[T]]:
    """Group items into buckets by key function.

    Args:
        items: List of items
        key_fn: Function to extract bucket key

    Returns:
        Dictionary mapping keys to lists of items
    """
    from collections import defaultdict

    buckets: dict[Any, list[T]] = defaultdict(list)

    for item in items:
        key = key_fn(item)
        buckets[key].append(item)

    return dict(buckets)


def filter_outliers(
    values: list[float], method: str = "iqr", threshold: float = 1.5
) -> list[float]:
    """Filter outliers from numeric values.

    Args:
        values: List of numeric values
        method: Method to use ("iqr" or "zscore")
        threshold: Threshold for outlier detection

    Returns:
        List with outliers removed
    """
    if not values:
        return []

    if method == "iqr":
        # Interquartile range method
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[(3 * n) // 4]
        iqr = q3 - q1
        lower = q1 - threshold * iqr
        upper = q3 + threshold * iqr
        return [v for v in values if lower <= v <= upper]

    elif method == "zscore":
        # Z-score method
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance**0.5

        if std == 0:
            return values

        return [v for v in values if abs((v - mean) / std) <= threshold]

    else:
        raise ValueError(f"Unknown method: {method}")


__all__ = [
    "random_sample",
    "stratified_sample",
    "reservoir_sample",
    "bucket_by",
    "filter_outliers",
]
