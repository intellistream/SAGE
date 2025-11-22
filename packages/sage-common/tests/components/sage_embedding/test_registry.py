"""Unit tests for the EmbeddingRegistry helper."""

from __future__ import annotations

import pytest

from sage.common.components.sage_embedding.registry import EmbeddingRegistry, ModelStatus


class DummyWrapper:
    """Minimal wrapper used for registry tests."""

    def __init__(self, **_kwargs):
        self.called = True


@pytest.fixture(autouse=True)
def reset_registry():
    """Ensure a clean registry for every test to avoid cross contamination."""

    EmbeddingRegistry.clear()
    yield
    EmbeddingRegistry.clear()


@pytest.mark.unit
class TestEmbeddingRegistry:
    def test_register_and_list_methods(self):
        EmbeddingRegistry.register(
            method="mock",
            display_name="Mock",
            description="Mock embedding",
            wrapper_class=DummyWrapper,
            default_dimension=42,
            example_models=["demo"],
        )

        methods = EmbeddingRegistry.list_methods()
        info = EmbeddingRegistry.get_model_info("mock")

        assert methods == ["mock"]
        assert info is not None
        assert info.display_name == "Mock"
        assert info.default_dimension == 42
        assert info.example_models == ["demo"]

    def test_get_wrapper_class_supports_string_path(self):
        EmbeddingRegistry.register(
            method="string_wrapper",
            display_name="String Wrapper",
            description="Uses import string",
            wrapper_class=f"{__name__}:DummyWrapper",
        )

        wrapper_cls = EmbeddingRegistry.get_wrapper_class("string_wrapper")

        assert wrapper_cls is DummyWrapper

    def test_check_status_needs_api_key(self, monkeypatch):
        monkeypatch.delenv("SECURE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        EmbeddingRegistry.register(
            method="secure",
            display_name="Needs Key",
            description="",
            wrapper_class=DummyWrapper,
            requires_api_key=True,
        )

        assert EmbeddingRegistry.check_status("secure") == ModelStatus.NEEDS_API_KEY
        status_with_key = EmbeddingRegistry.check_status("secure", api_key="fake-key")
        assert status_with_key == ModelStatus.AVAILABLE

    def test_check_status_model_download(self, monkeypatch):
        EmbeddingRegistry.register(
            method="hf",
            display_name="HF",
            description="",
            wrapper_class=DummyWrapper,
            requires_model_download=True,
        )

        monkeypatch.setattr(
            EmbeddingRegistry,
            "_is_model_cached",
            classmethod(lambda cls, model_name: False),
        )
        assert (
            EmbeddingRegistry.check_status("hf", model="test/model") == ModelStatus.NEEDS_DOWNLOAD
        )

        monkeypatch.setattr(
            EmbeddingRegistry,
            "_is_model_cached",
            classmethod(lambda cls, model_name: True),
        )
        assert EmbeddingRegistry.check_status("hf", model="test/model") == ModelStatus.CACHED

    def test_is_model_cached_reads_filesystem(self, monkeypatch, tmp_path):
        cache_dir = tmp_path / ".cache" / "huggingface" / "hub"
        cache_dir.mkdir(parents=True)
        cached_model_dir = cache_dir / "models--foo--bar"
        cached_model_dir.mkdir()

        monkeypatch.setattr(
            "sage.common.components.sage_embedding.registry.Path.home", lambda: tmp_path
        )

        assert EmbeddingRegistry._is_model_cached("foo/bar") is True
        assert EmbeddingRegistry._is_model_cached("other/model") is False

    def test_check_status_unavailable_for_unknown_method(self):
        """Test check_status returns UNAVAILABLE for unregistered method"""
        # Don't register anything, just check a non-existent method
        status = EmbeddingRegistry.check_status("nonexistent_method")
        assert status == ModelStatus.UNAVAILABLE

    def test_is_model_cached_returns_false_on_exception(self, monkeypatch):
        """Test _is_model_cached returns False when exception occurs"""

        def raise_exception(*args, **kwargs):
            raise RuntimeError("Simulated filesystem error")

        # Make Path.home() raise an exception
        monkeypatch.setattr(
            "sage.common.components.sage_embedding.registry.Path.home", raise_exception
        )

        # Should return False instead of propagating the exception
        assert EmbeddingRegistry._is_model_cached("any/model") is False

    def test_is_model_cached_returns_false_when_cache_dir_not_exists(self, monkeypatch, tmp_path):
        """Test _is_model_cached returns False when cache directory doesn't exist"""
        # Use tmp_path without creating the cache directory
        monkeypatch.setattr(
            "sage.common.components.sage_embedding.registry.Path.home", lambda: tmp_path
        )

        # Cache directory doesn't exist, should return False
        assert EmbeddingRegistry._is_model_cached("any/model") is False
