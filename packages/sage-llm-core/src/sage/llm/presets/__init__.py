"""Preset configurations for multi-engine orchestration.

Layer: L1 (Foundation - LLM Core)

This module provides preset configurations for launching multiple LLM/Embedding engines
through the unified Control Plane. Presets define bundles of engines with their
configurations, making it easy to deploy common multi-engine setups.

## Architecture Context

Presets work with the multi-engine architecture:
```
Control Plane (engine-agnostic)
    ├─> Engine 1 (vLLM: Qwen2.5-7B-Instruct)
    ├─> Engine 2 (vLLM: BGE-M3 Embedding)
    └─> Engine 3 (sageLLM: future)  [PLANNED]
```

## Usage

```python
from sage.llm.presets import get_builtin_preset, load_preset_file

# Use built-in preset
preset = get_builtin_preset("qwen-mini-with-embeddings")
for engine in preset.engines:
    print(f"Engine: {engine.name}, Model: {engine.model}, Kind: {engine.kind}")

# Load custom preset from file
preset = load_preset_file("config/my-preset.yaml")
```

## Preset File Format (YAML)

```yaml
version: 1
name: my-custom-preset
description: Custom multi-engine setup
engines:
  - name: chat
    kind: llm                           # "llm" or "embedding"
    model: Qwen/Qwen2.5-7B-Instruct
    tensor_parallel: 2
    pipeline_parallel: 1
    port: 8001
    label: main-chat
    max_concurrent_requests: 256
    use_gpu: true                       # Optional: force GPU usage
    metadata:
      role: primary-chat
    extra_args:
      - --max-model-len=4096

  - name: embed
    kind: embedding
    model: BAAI/bge-m3
    port: 8090
    label: embeddings
    use_gpu: false                      # Run on CPU
    metadata:
      role: embedding-server
```

## Engine Kinds

- **llm**: LLM inference engines (chat, completion)
  - Currently: vLLM
  - Future: sageLLM, TensorRT-LLM, etc.

- **embedding**: Text embedding engines
  - Currently: vLLM (with embedding models), sage-embedding
  - Future: sageLLM embedding support

## Built-in Presets

- `qwen-mini-with-embeddings`: Qwen 1.5B + BGE-small embedding
- `qwen-lite`: Qwen 0.5B (no embedding)

See `registry.py` for full list and definitions.
"""

from .models import EnginePreset, PresetEngine, load_preset_file
from .registry import get_builtin_preset, iter_builtin_presets, list_builtin_presets

__all__ = [
    "EnginePreset",
    "PresetEngine",
    "get_builtin_preset",
    "iter_builtin_presets",
    "list_builtin_presets",
    "load_preset_file",
]
