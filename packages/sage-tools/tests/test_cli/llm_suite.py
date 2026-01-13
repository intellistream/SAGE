"""Test cases for the ``sage llm`` command group."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from sage.cli.main import app as sage_app
from sage.middleware.operators import SageLLMGenerator

from .helpers import CLITestCase


def _raise_not_implemented(*_args, **_kwargs):
    raise NotImplementedError("placeholder")


def collect_cases() -> list[CLITestCase]:
    fake_info = SimpleNamespace(
        model_id="demo/model",
        revision="main",
        path="/tmp/demo",
        size_bytes=1024,
        size_mb=1.0,
        last_used_iso="2024-01-01T00:00:00",
        tags=["text"],
    )

    return [
        CLITestCase(
            "sage llm model show --json",
            ["llm", "model", "show", "--json"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.common.model_registry.sagellm_registry.list_models",
                    return_value=[fake_info],
                )
            ],
        ),
        CLITestCase(
            "sage llm run (stub)",
            ["llm", "run", "--model", "demo/model"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.middleware.operators.llm.sagellm_generator.SageLLMGenerator",
                    return_value=SimpleNamespace(
                        setup=lambda: None,
                        execute=lambda *_a, **_k: "hi",
                        cleanup=lambda: None,
                    ),
                ),
                lambda: patch(
                    "sage.tools.cli.commands.llm.typer.prompt",
                    return_value="",
                ),
            ],
        ),
        CLITestCase(
            "sage llm model download",
            ["llm", "model", "download", "--model", "demo/model"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.common.model_registry.sagellm_registry.download_model",
                    return_value=fake_info,
                )
            ],
        ),
        CLITestCase(
            "sage llm model delete",
            ["llm", "model", "delete", "--model", "demo/model", "--yes"],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.common.model_registry.sagellm_registry.delete_model",
                    return_value=None,
                )
            ],
        ),
        CLITestCase(
            "sage llm fine-tune (stub)",
            [
                "llm",
                "fine-tune",
                "--base-model",
                "demo/model",
                "--dataset",
                "data.json",
                "--output",
                "out",
            ],
            app=sage_app,
            patch_factories=[
                lambda: patch(
                    "sage.middleware.operators.llm.sagellm_generator.SageLLMGenerator",
                    return_value=SimpleNamespace(
                        fine_tune=_raise_not_implemented,
                        setup=lambda: None,
                        cleanup=lambda: None,
                    ),
                )
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# SageLLMGenerator unit tests (GPU-free, CI-compatible)
# ---------------------------------------------------------------------------


class TestSageLLMGeneratorMockMode:
    """Test SageLLMGenerator with mock backend (no GPU required)."""

    def test_sagellm_generator_mock_mode(self):
        """SageLLMGenerator should work in mock mode without GPU."""
        generator = SageLLMGenerator(backend_type="mock")
        result = generator.execute("test prompt")
        # Mock backend returns dict with 'text' and 'usage' keys
        assert result is not None
        assert isinstance(result, dict)
        assert "text" in result
        assert "usage" in result
        # Check that output contains generated text
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0

    def test_sagellm_generator_mock_dict_input(self):
        """SageLLMGenerator mock mode should handle dict inputs."""
        generator = SageLLMGenerator(backend_type="mock")
        result = generator.execute({"prompt": "test prompt", "options": {"max_tokens": 100}})
        assert result is not None
        assert isinstance(result, dict)
        assert "text" in result
        assert len(result["text"]) > 0

    def test_sagellm_generator_default_config(self):
        """SageLLMGenerator should have sensible defaults."""
        generator = SageLLMGenerator(backend_type="mock")
        assert generator.backend_type == "mock"
        # device_map should default to "auto"
        assert generator.device_map == "auto"
