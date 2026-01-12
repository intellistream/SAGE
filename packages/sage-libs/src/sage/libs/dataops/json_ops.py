"""JSON schema validation and transformation utilities."""

from __future__ import annotations

from typing import Any


def validate_schema(data: dict[str, Any], schema: dict[str, type]) -> tuple[bool, list[str]]:
    """Validate data against a simple type schema.

    Args:
        data: Data dictionary to validate
        schema: Dictionary mapping field names to expected types

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    for field, expected_type in schema.items():
        if field not in data:
            errors.append(f"Missing required field: {field}")
            continue

        value = data[field]
        if not isinstance(value, expected_type):
            errors.append(
                f"Field {field} has wrong type: expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

    return len(errors) == 0, errors


def extract_fields(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Extract specific fields from nested JSON.

    Args:
        data: Input JSON dictionary
        fields: List of field paths (dot-separated for nested fields)

    Returns:
        Dictionary with extracted fields
    """
    result = {}

    for field_path in fields:
        parts = field_path.split(".")
        value = data

        try:
            for part in parts:
                if isinstance(value, dict):
                    value = value[part]
                elif isinstance(value, list) and part.isdigit():
                    value = value[int(part)]
                else:
                    value = None
                    break

            if value is not None:
                result[field_path] = value
        except (KeyError, IndexError, ValueError):
            pass

    return result


def flatten_json(data: dict[str, Any], prefix: str = "", sep: str = ".") -> dict[str, Any]:
    """Flatten nested JSON to single-level dictionary.

    Args:
        data: Nested JSON dictionary
        prefix: Prefix for keys (used in recursion)
        sep: Separator for nested keys

    Returns:
        Flattened dictionary
    """
    result = {}

    for key, value in data.items():
        new_key = f"{prefix}{sep}{key}" if prefix else key

        if isinstance(value, dict):
            result.update(flatten_json(value, new_key, sep))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    result.update(flatten_json(item, f"{new_key}[{i}]", sep))
                else:
                    result[f"{new_key}[{i}]"] = item
        else:
            result[new_key] = value

    return result


def merge_json(base: dict[str, Any], update: dict[str, Any], deep: bool = True) -> dict[str, Any]:
    """Merge two JSON dictionaries.

    Args:
        base: Base dictionary
        update: Dictionary with updates
        deep: If True, recursively merge nested dicts

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in update.items():
        if deep and key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_json(result[key], value, deep=True)
        else:
            result[key] = value

    return result


__all__ = [
    "validate_schema",
    "extract_fields",
    "flatten_json",
    "merge_json",
]
