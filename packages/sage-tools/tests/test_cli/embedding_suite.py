"""Test cases for ``sage embedding`` command group."""

from __future__ import annotations

from unittest.mock import patch

from .helpers import CLITestCase

EMBED_MODULE = "sage.cli.commands.apps.embedding"

SAMPLE_MODELS = {
    "hash": {
        "display_name": "Hash",
        "requires_api_key": False,
        "requires_download": False,
        "default_dimension": 384,
        "examples": ["hash"],
    },
    "openai": {
        "display_name": "OpenAI",
        "requires_api_key": True,
        "requires_download": False,
        "default_dimension": 1536,
        "examples": ["text-embedding-3-small"],
    },
}


def _patch_list_models():
    return patch(f"{EMBED_MODULE}.list_embedding_models", return_value=SAMPLE_MODELS)


def _patch_check_availability():
    payload = {
        "status": "available",
        "message": "ok",
        "action": "none",
    }
    return patch(f"{EMBED_MODULE}.check_model_availability", return_value=payload)


def _patch_get_embedder():
    class DummyEmbedder:
        def __init__(self):
            self.calls = 0

        def embed(self, text: str):
            self.calls += 1
            return [0.1, 0.2, 0.3]

        def __str__(self) -> str:  # pragma: no cover - repr only
            return "DummyEmbedder"

    def factory(*args, **kwargs):
        return DummyEmbedder()

    return patch(f"{EMBED_MODULE}.get_embedding_model", side_effect=factory)


def collect_cases() -> list[CLITestCase]:
    return [
        CLITestCase("sage embedding --help", ["embedding", "--help"]),
        CLITestCase(
            "sage embedding list simple",
            ["embedding", "list", "--format", "simple"],
            patch_factories=[_patch_list_models()],
        ),
        CLITestCase(
            "sage embedding list json api-only",
            ["embedding", "list", "--format", "json", "--api-key-only"],
            patch_factories=[_patch_list_models()],
        ),
        CLITestCase(
            "sage embedding check",
            ["embedding", "check", "hash"],
            patch_factories=[_patch_check_availability(), _patch_list_models()],
        ),
        CLITestCase(
            "sage embedding test",
            ["embedding", "test", "hash", "--text", "hi"],
            patch_factories=[_patch_get_embedder()],
        ),
        CLITestCase(
            "sage embedding benchmark",
            ["embedding", "benchmark", "hash", "mockembedder"],
            patch_factories=[_patch_get_embedder()],
        ),
    ]
