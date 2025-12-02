"""Preset schema definitions for multi-engine launcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ALLOWED_ENGINE_KINDS = {"llm", "embedding"}


def _ensure_positive(value: int | None, field_name: str, default: int = 1) -> int:
    if value is None:
        return default
    if value <= 0:
        raise ValueError(f"{field_name} must be > 0 (got {value})")
    return value


@dataclass(slots=True)
class PresetEngine:
    """Single engine configuration entry."""

    name: str
    model: str
    kind: str = "llm"
    tensor_parallel: int = 1
    pipeline_parallel: int = 1
    port: int | None = None
    label: str | None = None
    max_concurrent_requests: int = 256
    use_gpu: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extra_args: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresetEngine:
        if "name" not in data:
            raise ValueError("Preset engine entry must include 'name'")
        if "model" not in data:
            raise ValueError("Preset engine entry must include 'model'")
        kind = str(data.get("kind", "llm")).lower()
        if kind not in _ALLOWED_ENGINE_KINDS:
            raise ValueError(
                f"Unsupported engine kind '{kind}'. Expected one of {_ALLOWED_ENGINE_KINDS}"
            )
        tensor_parallel = _ensure_positive(data.get("tensor_parallel"), "tensor_parallel")
        pipeline_parallel = _ensure_positive(
            data.get("pipeline_parallel"),
            "pipeline_parallel",
        )
        max_req = _ensure_positive(
            data.get("max_concurrent_requests"), "max_concurrent_requests", 256
        )
        raw_use_gpu = data.get("use_gpu")
        use_gpu = None if raw_use_gpu is None else bool(raw_use_gpu)
        extra_args = list(data.get("extra_args") or [])
        metadata = dict(data.get("metadata") or {})
        return cls(
            name=str(data["name"]),
            model=str(data["model"]),
            kind=kind,
            tensor_parallel=tensor_parallel,
            pipeline_parallel=pipeline_parallel,
            port=data.get("port"),
            label=data.get("label"),
            max_concurrent_requests=max_req,
            use_gpu=use_gpu,
            metadata=metadata,
            extra_args=extra_args,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model_id": self.model,
            "tensor_parallel_size": self.tensor_parallel,
            "pipeline_parallel_size": self.pipeline_parallel,
            "max_concurrent_requests": self.max_concurrent_requests,
            "engine_kind": self.kind,
        }
        if self.port is not None:
            payload["port"] = self.port
        if self.label:
            payload["engine_label"] = self.label
        if self.use_gpu is not None:
            payload["use_gpu"] = self.use_gpu
        if self.metadata:
            payload["metadata"] = self.metadata
        if self.extra_args:
            payload["extra_args"] = self.extra_args
        return payload


@dataclass(slots=True)
class EnginePreset:
    """Preset representing a bundle of engines."""

    name: str
    version: int = 1
    description: str | None = None
    engines: list[PresetEngine] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnginePreset:
        if "name" not in data:
            raise ValueError("Preset definition requires 'name'")
        raw_engines = data.get("engines")
        if not raw_engines or not isinstance(raw_engines, list):
            raise ValueError("Preset definition must include a non-empty 'engines' list")
        engines = [PresetEngine.from_dict(item) for item in raw_engines]
        version = int(data.get("version", 1))
        description = data.get("description")
        return cls(
            name=str(data["name"]), version=version, description=description, engines=engines
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "engines": [
                {
                    "name": engine.name,
                    "kind": engine.kind,
                    "model": engine.model,
                    "tensor_parallel": engine.tensor_parallel,
                    "pipeline_parallel": engine.pipeline_parallel,
                    "port": engine.port,
                    "label": engine.label,
                    "max_concurrent_requests": engine.max_concurrent_requests,
                    "use_gpu": engine.use_gpu,
                    "metadata": engine.metadata or None,
                    "extra_args": engine.extra_args or None,
                }
                for engine in self.engines
            ],
        }


def load_preset_file(path: str | Path) -> EnginePreset:
    """Load preset YAML/JSON from disk."""

    preset_path = Path(path)
    if not preset_path.exists():
        raise FileNotFoundError(f"Preset file not found: {preset_path}")
    with preset_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Preset file must contain a mapping at the top level")
    return EnginePreset.from_dict(payload)


__all__ = ["EnginePreset", "PresetEngine", "load_preset_file"]
