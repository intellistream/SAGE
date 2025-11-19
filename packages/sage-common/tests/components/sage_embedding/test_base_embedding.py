"""Unit tests for the BaseEmbedding abstract helper."""

import pytest

from sage.common.components.sage_embedding.base import BaseEmbedding


class ExampleEmbedding(BaseEmbedding):
    """Simple concrete embedding for testing BaseEmbedding defaults."""

    def __init__(self, scale: float = 1.0, **kwargs):
        super().__init__(scale=scale, **kwargs)
        self._scale = scale

    def embed(self, text: str) -> list[float]:
        return [self._scale * float(ord(ch)) for ch in text]

    def get_dim(self) -> int:
        return len(self.embed("dim"))

    @property
    def method_name(self) -> str:  # pragma: no cover - property used indirectly
        return "example"


@pytest.mark.unit
class TestBaseEmbedding:
    def test_embed_batch_uses_single_embed(self):
        emb = ExampleEmbedding(scale=0.5)

        result = emb.embed_batch(["hi", "bye"])

        assert len(result) == 2
        assert result[0] == emb.embed("hi")
        assert result[1] == emb.embed("bye")

    def test_repr_includes_config(self):
        emb = ExampleEmbedding(scale=2.0, extra="value")

        repr_str = repr(emb)

        assert "ExampleEmbedding" in repr_str
        assert "scale" in repr_str
        assert "extra" in repr_str

    def test_default_model_info(self):
        info = BaseEmbedding.get_model_info()

        assert "method" in info
        assert info["requires_api_key"] is False
        assert info["requires_model_download"] is False

    def test_method_name_property(self):
        emb = ExampleEmbedding()

        assert emb.method_name == "example"
        assert emb.get_dim() == len(emb.embed("dim"))
