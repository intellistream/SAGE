# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unit tests for preset models and registry.

Tests YAML parsing, preset validation, and the use_gpu field.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from sage.common.components.sage_llm.presets import (
    EnginePreset,
    PresetEngine,
    get_builtin_preset,
    list_builtin_presets,
    load_preset_file,
)


class TestPresetEngine:
    """Tests for PresetEngine dataclass."""

    def test_default_values(self):
        """Test PresetEngine with default values."""
        engine = PresetEngine(name="test", model="model/test")

        assert engine.name == "test"
        assert engine.model == "model/test"
        assert engine.kind == "llm"
        assert engine.tensor_parallel == 1
        assert engine.pipeline_parallel == 1
        assert engine.port is None
        assert engine.label is None
        assert engine.max_concurrent_requests == 256
        assert engine.use_gpu is None
        assert engine.metadata == {}
        assert engine.extra_args == []

    def test_from_dict_minimal(self):
        """Test creating PresetEngine from minimal dict."""
        data = {"name": "test-engine", "model": "Qwen/Qwen2.5-7B"}
        engine = PresetEngine.from_dict(data)

        assert engine.name == "test-engine"
        assert engine.model == "Qwen/Qwen2.5-7B"
        assert engine.kind == "llm"
        assert engine.use_gpu is None

    def test_from_dict_full(self):
        """Test creating PresetEngine from full dict."""
        data = {
            "name": "test-embed",
            "model": "BAAI/bge-m3",
            "kind": "embedding",
            "tensor_parallel": 2,
            "pipeline_parallel": 1,
            "port": 8090,
            "label": "embedding-service",
            "max_concurrent_requests": 512,
            "use_gpu": True,
            "metadata": {"version": "1.0"},
            "extra_args": ["--max-batch-size", "32"],
        }
        engine = PresetEngine.from_dict(data)

        assert engine.name == "test-embed"
        assert engine.model == "BAAI/bge-m3"
        assert engine.kind == "embedding"
        assert engine.tensor_parallel == 2
        assert engine.port == 8090
        assert engine.label == "embedding-service"
        assert engine.max_concurrent_requests == 512
        assert engine.use_gpu is True
        assert engine.metadata == {"version": "1.0"}
        assert engine.extra_args == ["--max-batch-size", "32"]

    def test_from_dict_use_gpu_false(self):
        """Test creating PresetEngine with use_gpu=False."""
        data = {"name": "test", "model": "model/test", "use_gpu": False}
        engine = PresetEngine.from_dict(data)
        assert engine.use_gpu is False

    def test_from_dict_use_gpu_none(self):
        """Test creating PresetEngine with use_gpu=None (not specified)."""
        data = {"name": "test", "model": "model/test"}
        engine = PresetEngine.from_dict(data)
        assert engine.use_gpu is None

    def test_from_dict_missing_name(self):
        """Test from_dict raises error when name is missing."""
        with pytest.raises(ValueError, match="must include 'name'"):
            PresetEngine.from_dict({"model": "test-model"})

    def test_from_dict_missing_model(self):
        """Test from_dict raises error when model is missing."""
        with pytest.raises(ValueError, match="must include 'model'"):
            PresetEngine.from_dict({"name": "test-engine"})

    def test_from_dict_invalid_kind(self):
        """Test from_dict raises error for invalid engine kind."""
        with pytest.raises(ValueError, match="Unsupported engine kind"):
            PresetEngine.from_dict({"name": "test", "model": "model", "kind": "invalid"})

    def test_from_dict_invalid_tensor_parallel(self):
        """Test from_dict raises error for invalid tensor_parallel."""
        with pytest.raises(ValueError, match="tensor_parallel must be > 0"):
            PresetEngine.from_dict({"name": "test", "model": "model", "tensor_parallel": 0})

    def test_to_payload_minimal(self):
        """Test to_payload with minimal engine config."""
        engine = PresetEngine(name="test", model="model/test")
        payload = engine.to_payload()

        assert payload == {
            "model_id": "model/test",
            "tensor_parallel_size": 1,
            "pipeline_parallel_size": 1,
            "max_concurrent_requests": 256,
            "engine_kind": "llm",
        }
        # use_gpu should NOT be in payload when None
        assert "use_gpu" not in payload

    def test_to_payload_with_use_gpu_true(self):
        """Test to_payload includes use_gpu when True."""
        engine = PresetEngine(
            name="test-embed",
            model="BAAI/bge-m3",
            kind="embedding",
            use_gpu=True,
        )
        payload = engine.to_payload()

        assert payload["use_gpu"] is True
        assert payload["engine_kind"] == "embedding"

    def test_to_payload_with_use_gpu_false(self):
        """Test to_payload includes use_gpu when False."""
        engine = PresetEngine(name="test", model="model/test", use_gpu=False)
        payload = engine.to_payload()

        assert payload["use_gpu"] is False

    def test_to_payload_with_optional_fields(self):
        """Test to_payload with optional fields."""
        engine = PresetEngine(
            name="test",
            model="model/test",
            port=8001,
            label="my-engine",
            metadata={"key": "value"},
            extra_args=["--arg1", "val1"],
        )
        payload = engine.to_payload()

        assert payload["port"] == 8001
        assert payload["engine_label"] == "my-engine"
        assert payload["metadata"] == {"key": "value"}
        assert payload["extra_args"] == ["--arg1", "val1"]


class TestEnginePreset:
    """Tests for EnginePreset dataclass."""

    def test_default_values(self):
        """Test EnginePreset with default values."""
        preset = EnginePreset(name="test-preset")

        assert preset.name == "test-preset"
        assert preset.version == 1
        assert preset.description is None
        assert preset.engines == []

    def test_from_dict(self):
        """Test creating EnginePreset from dict."""
        data = {
            "name": "multi-engine",
            "version": 2,
            "description": "Multi-engine setup",
            "engines": [
                {"name": "llm", "model": "Qwen/Qwen2.5-7B"},
                {"name": "embed", "model": "BAAI/bge-m3", "kind": "embedding", "use_gpu": True},
            ],
        }
        preset = EnginePreset.from_dict(data)

        assert preset.name == "multi-engine"
        assert preset.version == 2
        assert preset.description == "Multi-engine setup"
        assert len(preset.engines) == 2
        assert preset.engines[0].name == "llm"
        assert preset.engines[1].kind == "embedding"
        assert preset.engines[1].use_gpu is True

    def test_from_dict_missing_name(self):
        """Test from_dict raises error when name is missing."""
        with pytest.raises(ValueError, match="requires 'name'"):
            EnginePreset.from_dict({"engines": [{"name": "e", "model": "m"}]})

    def test_from_dict_missing_engines(self):
        """Test from_dict raises error when engines is missing."""
        with pytest.raises(ValueError, match="non-empty 'engines' list"):
            EnginePreset.from_dict({"name": "test"})

    def test_from_dict_empty_engines(self):
        """Test from_dict raises error when engines is empty."""
        with pytest.raises(ValueError, match="non-empty 'engines' list"):
            EnginePreset.from_dict({"name": "test", "engines": []})

    def test_to_dict(self):
        """Test converting EnginePreset to dict."""
        preset = EnginePreset(
            name="test-preset",
            version=1,
            description="Test",
            engines=[
                PresetEngine(name="llm", model="model/llm"),
                PresetEngine(name="embed", model="model/embed", kind="embedding", use_gpu=True),
            ],
        )
        data = preset.to_dict()

        assert data["name"] == "test-preset"
        assert data["version"] == 1
        assert data["description"] == "Test"
        assert len(data["engines"]) == 2

        # Check use_gpu is properly serialized
        assert data["engines"][0]["use_gpu"] is None
        assert data["engines"][1]["use_gpu"] is True


class TestLoadPresetFile:
    """Tests for load_preset_file function."""

    def test_load_yaml_preset(self):
        """Test loading a YAML preset file."""
        preset_data = {
            "name": "test-preset",
            "version": 1,
            "engines": [
                {"name": "llm", "model": "Qwen/Qwen2.5-7B"},
                {"name": "embed", "model": "BAAI/bge-m3", "kind": "embedding", "use_gpu": True},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(preset_data, f)
            f.flush()
            preset_path = Path(f.name)

        try:
            preset = load_preset_file(preset_path)

            assert preset.name == "test-preset"
            assert len(preset.engines) == 2
            assert preset.engines[1].use_gpu is True
        finally:
            preset_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file raises error."""
        with pytest.raises(FileNotFoundError, match="not found"):
            load_preset_file("/nonexistent/path/preset.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("- not a mapping")
            f.flush()
            preset_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="must contain a mapping"):
                load_preset_file(preset_path)
        finally:
            preset_path.unlink()


class TestBuiltinPresets:
    """Tests for builtin preset registry."""

    def test_list_builtin_presets(self):
        """Test listing builtin presets."""
        presets = list_builtin_presets()
        # Just verify it returns a list (may be empty if no builtins defined)
        assert isinstance(presets, list)

    def test_get_builtin_preset_nonexistent(self):
        """Test getting a non-existent builtin preset."""
        result = get_builtin_preset("nonexistent-preset-name-12345")
        assert result is None


class TestPresetEngineUseGpuBehavior:
    """Tests specifically for use_gpu behavior in presets."""

    def test_use_gpu_none_default_behavior(self):
        """Test that use_gpu=None means default behavior (LLM uses GPU, embedding does not)."""
        llm_engine = PresetEngine(name="llm", model="model/llm", kind="llm", use_gpu=None)
        embed_engine = PresetEngine(
            name="embed", model="model/embed", kind="embedding", use_gpu=None
        )

        # Both should have use_gpu=None
        assert llm_engine.use_gpu is None
        assert embed_engine.use_gpu is None

        # Payload should not include use_gpu
        assert "use_gpu" not in llm_engine.to_payload()
        assert "use_gpu" not in embed_engine.to_payload()

    def test_use_gpu_true_forces_gpu(self):
        """Test that use_gpu=True forces GPU usage."""
        engine = PresetEngine(
            name="embed-gpu", model="BAAI/bge-m3", kind="embedding", use_gpu=True
        )

        assert engine.use_gpu is True
        payload = engine.to_payload()
        assert payload["use_gpu"] is True

    def test_use_gpu_false_forces_cpu(self):
        """Test that use_gpu=False forces CPU usage."""
        engine = PresetEngine(name="llm-cpu", model="model/llm", kind="llm", use_gpu=False)

        assert engine.use_gpu is False
        payload = engine.to_payload()
        assert payload["use_gpu"] is False

    def test_yaml_roundtrip_use_gpu(self):
        """Test YAML roundtrip preserves use_gpu values."""
        preset_data = {
            "name": "roundtrip-test",
            "engines": [
                {"name": "e1", "model": "m1", "use_gpu": True},
                {"name": "e2", "model": "m2", "use_gpu": False},
                {"name": "e3", "model": "m3"},  # No use_gpu specified
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(preset_data, f)
            f.flush()
            preset_path = Path(f.name)

        try:
            preset = load_preset_file(preset_path)

            assert preset.engines[0].use_gpu is True
            assert preset.engines[1].use_gpu is False
            assert preset.engines[2].use_gpu is None

            # to_dict should preserve these values
            data = preset.to_dict()
            assert data["engines"][0]["use_gpu"] is True
            assert data["engines"][1]["use_gpu"] is False
            assert data["engines"][2]["use_gpu"] is None
        finally:
            preset_path.unlink()
