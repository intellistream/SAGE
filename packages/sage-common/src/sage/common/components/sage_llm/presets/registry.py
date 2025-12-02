"""Built-in preset registry for sageLLM multi-engine launcher."""
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
    """Return all builtin presets sorted by name."""

    return [preset for _, preset in sorted(_BUILTIN_PRESETS.items(), key=lambda item: item[0])]


def get_builtin_preset(name: str) -> EnginePreset | None:
    """Fetch a builtin preset by its name."""

    return _BUILTIN_PRESETS.get(name)


def iter_builtin_presets() -> Iterator[EnginePreset]:
    """Yield builtin presets for tooling."""

    return iter(_BUILTIN_PRESETS.values())


__all__ = [
    "get_builtin_preset",
    "iter_builtin_presets",
    "list_builtin_presets",
]
