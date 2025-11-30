"""Tests for the `VectorStore` Protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sage.middleware.operators.rag.index_builder.storage import VectorStore


class GoodStore:
    def __init__(self):
        self.data: list[tuple[list[float], dict[str, Any]]] = []

    def add(self, vector: list[float], metadata: dict[str, Any]) -> None:
        self.data.append((vector, metadata))

    def build_index(self) -> None:  # pragma: no cover - trivial
        pass

    def save(self, path: str) -> None:  # pragma: no cover - trivial
        Path(path).touch()

    def load(self, path: str) -> None:  # pragma: no cover - trivial
        Path(path)

    def search(self, query_vector, top_k: int = 5, filter_metadata=None):  # pragma: no cover
        return []

    def get_dim(self) -> int:  # pragma: no cover - trivial
        return 3

    def count(self) -> int:  # pragma: no cover - trivial
        return len(self.data)


class IncompleteStore:
    def add(self, vector, metadata):  # pragma: no cover - trivial
        pass


def test_vector_store_protocol_checks_methods():
    assert isinstance(GoodStore(), VectorStore)
    assert not isinstance(IncompleteStore(), VectorStore)
