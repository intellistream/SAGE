"""Table/dataframe operations."""

from __future__ import annotations

from typing import Any, Callable


def filter_rows(
    data: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]
) -> list[dict[str, Any]]:
    """Filter rows based on predicate function.

    Args:
        data: List of row dictionaries
        predicate: Function that returns True for rows to keep

    Returns:
        Filtered rows
    """
    return [row for row in data if predicate(row)]


def select_columns(data: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    """Select specific columns from data.

    Args:
        data: List of row dictionaries
        columns: Column names to select

    Returns:
        Data with only selected columns
    """
    return [{k: row.get(k) for k in columns} for row in data]


def aggregate(
    data: list[dict[str, Any]],
    group_by: str,
    agg_col: str,
    agg_fn: Callable[[list[Any]], Any],
) -> dict[Any, Any]:
    """Group by column and aggregate.

    Args:
        data: List of row dictionaries
        group_by: Column to group by
        agg_col: Column to aggregate
        agg_fn: Aggregation function

    Returns:
        Dictionary mapping group_by values to aggregated values
    """
    from collections import defaultdict

    groups: dict[Any, list[Any]] = defaultdict(list)

    for row in data:
        key = row.get(group_by)
        value = row.get(agg_col)
        if key is not None and value is not None:
            groups[key].append(value)

    return {k: agg_fn(v) for k, v in groups.items()}


def sort_rows(data: list[dict[str, Any]], by: str, reverse: bool = False) -> list[dict[str, Any]]:
    """Sort rows by column.

    Args:
        data: List of row dictionaries
        by: Column name to sort by
        reverse: If True, sort in descending order

    Returns:
        Sorted data
    """
    return sorted(data, key=lambda row: row.get(by, ""), reverse=reverse)


def pivot(
    data: list[dict[str, Any]], index: str, columns: str, values: str
) -> dict[tuple[Any, Any], Any]:
    """Simple pivot operation.

    Args:
        data: List of row dictionaries
        index: Column to use as row index
        columns: Column to use as column index
        values: Column to use as values

    Returns:
        Dictionary mapping (index, column) tuples to values
    """
    result: dict[tuple[Any, Any], Any] = {}

    for row in data:
        idx = row.get(index)
        col = row.get(columns)
        val = row.get(values)

        if idx is not None and col is not None and val is not None:
            result[(idx, col)] = val

    return result


__all__ = [
    "filter_rows",
    "select_columns",
    "aggregate",
    "sort_rows",
    "pivot",
]
