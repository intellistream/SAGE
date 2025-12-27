"""Compatibility shim for legacy ``sage.llm.presets`` imports.

Routes callers to ``sage.common.components.sage_llm.presets`` definitions.
"""

from sage.common.components.sage_llm.presets import (
    EnginePreset,
    PresetEngine,
    get_builtin_preset,
    iter_builtin_presets,
    list_builtin_presets,
    load_preset_file,
)

__all__ = [
    "EnginePreset",
    "PresetEngine",
    "get_builtin_preset",
    "iter_builtin_presets",
    "list_builtin_presets",
    "load_preset_file",
]
