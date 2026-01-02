"""Built-in preset registry for multi-engine launcher.

Layer: L1 (Foundation - LLM Core)

This module maintains a registry of built-in engine presets that provide
common multi-engine deployment configurations. Users can select these
presets by name or create custom presets using the same schema.

Built-in presets are designed for:
- Quick prototyping and testing
- Common deployment patterns
- Reference configurations

For production deployments, consider creating custom preset files
tailored to your specific requirements.

Current built-in presets:
- qwen-mini-with-embeddings: Qwen 1.5B chat + BGE-small embedding (lightweight)
- qwen-lite: Qwen 0.5B chat only (minimal resource usage)

Future presets may include:
- Large-scale multi-GPU configurations
- sageLLM engine presets (when available)
- Specialized embedding configurations
"""

from __future__ import annotations

from typing import Iterator

from .models import EnginePreset


def _build_builtin_presets() -> dict[str, EnginePreset]:
    presets: dict[str, EnginePreset] = {}
    baseline = EnginePreset.from_dict(
        {
            "version": 1,
            "name": "qwen-mini-with-embeddings",
            "description": "Start a Qwen 1.5B chat engine and BGE-small embedding server.",
            "engines": [
                {
                    "name": "chat",
                    "kind": "llm",
                    "model": "Qwen/Qwen2.5-1.5B-Instruct",
                    "tensor_parallel": 1,
                    "pipeline_parallel": 1,
                    "label": "chat-qwen15b",
                    "metadata": {"preset": "qwen-mini-with-embeddings", "role": "chat"},
                },
                {
                    "name": "embed",
                    "kind": "embedding",
                    "model": "BAAI/bge-small-zh-v1.5",
                    "label": "embedding-bge",
                    "metadata": {"preset": "qwen-mini-with-embeddings", "role": "embedding"},
                },
            ],
        }
    )
    presets[baseline.name] = baseline
    lite = EnginePreset.from_dict(
        {
            "version": 1,
            "name": "qwen-lite",
            "description": "Single Qwen 0.5B engine (no embedding server).",
            "engines": [
                {
                    "name": "chat",
                    "kind": "llm",
                    "model": "Qwen/Qwen2.5-0.5B-Instruct",
                    "tensor_parallel": 1,
                    "pipeline_parallel": 1,
                    "label": "chat-qwen05b",
                    "metadata": {"preset": "qwen-lite"},
                }
            ],
        }
    )
    presets[lite.name] = lite
    return presets


_BUILTIN_PRESETS = _build_builtin_presets()


def list_builtin_presets() -> list[EnginePreset]:
    """Return all builtin presets sorted by name.

    Returns:
        List of all built-in EnginePreset objects, sorted alphabetically

    Example:
        >>> presets = list_builtin_presets()
        >>> for preset in presets:
        ...     print(f"{preset.name}: {preset.description}")
    """

    return [preset for _, preset in sorted(_BUILTIN_PRESETS.items(), key=lambda item: item[0])]


def get_builtin_preset(name: str) -> EnginePreset | None:
    """Fetch a builtin preset by its name.

    Args:
        name: Preset identifier (e.g., "qwen-mini-with-embeddings")

    Returns:
        EnginePreset if found, None otherwise

    Example:
        >>> preset = get_builtin_preset("qwen-lite")
        >>> if preset:
        ...     print(f"Found preset with {len(preset.engines)} engines")
    """

    return _BUILTIN_PRESETS.get(name)


def iter_builtin_presets() -> Iterator[EnginePreset]:
    """Yield builtin presets for iteration.

    Returns:
        Iterator over all built-in EnginePreset objects

    Example:
        >>> for preset in iter_builtin_presets():
        ...     print(preset.name)
    """

    return iter(_BUILTIN_PRESETS.values())


__all__ = [
    "get_builtin_preset",
    "iter_builtin_presets",
    "list_builtin_presets",
]
