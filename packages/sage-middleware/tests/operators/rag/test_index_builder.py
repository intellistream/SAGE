"""Tests for the RAG index builder orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from sage.middleware.operators.rag.index_builder import IndexBuilder


@dataclass
class DummyStore:
    persist_path: Path
    dim: int

    def __post_init__(self):
        self.add_calls: list[tuple[list[float], dict[str, Any]]] = []
        self.index_built = False
        self.saved_path: str | None = None

    def add(self, vector: list[float], metadata: dict[str, Any]) -> None:
        self.add_calls.append((vector, metadata))

    def build_index(self) -> None:
        self.index_built = True

    def save(self, path: str) -> None:
        self.saved_path = path

    # Unused protocol methods (kept for completeness/testing)
    def load(self, path: str) -> None:  # pragma: no cover - helper stub
        self.saved_path = path

    def search(self, query_vector, top_k: int = 5, filter_metadata=None):  # pragma: no cover
        return []

    def get_dim(self) -> int:  # pragma: no cover - helper stub
        return self.dim

    def count(self) -> int:  # pragma: no cover - helper stub
        return len(self.add_calls)


class DummyEmbedModel:
    def __init__(self, dim: int = 4):
        self.dim = dim
        self.seen_chunks: list[str] = []

    def get_dim(self) -> int:
        return self.dim

    def embed(self, chunk: str) -> list[float]:
        self.seen_chunks.append(chunk)
        return [float(len(chunk))] * self.dim


@pytest.fixture()
def builder_factory() -> tuple[IndexBuilder, list[DummyStore]]:
    created: list[DummyStore] = []

    def factory(path: Path, dim: int) -> DummyStore:
        store = DummyStore(path, dim)
        created.append(store)
        return store

    return IndexBuilder(factory), created


@pytest.fixture()
def docs_dir(tmp_path: Path) -> Path:
    path = tmp_path / "docs"
    path.mkdir()
    return path


def test_build_from_docs_creates_manifest_and_vectors(builder_factory, docs_dir, tmp_path):
    builder, stores = builder_factory
    embedder = DummyEmbedModel(dim=3)

    processed_sections = [
        {"content": "Alpha " * 50, "metadata": {"doc_path": "alpha.md", "title": "Alpha"}},
        {"content": "Beta " * 25, "metadata": {"doc_path": "beta.md", "title": "Beta"}},
    ]

    manifest = builder.build_from_docs(
        source_dir=docs_dir,
        persist_path=tmp_path / "index",
        embedding_model=embedder,
        index_name="demo-index",
        chunk_size=120,
        chunk_overlap=20,
        document_processor=lambda _dir: processed_sections,
    )

    store = stores[0]
    assert store.index_built is True
    assert store.saved_path == str(tmp_path / "index")
    assert len(store.add_calls) >= len(processed_sections)

    vector, metadata = store.add_calls[0]
    assert len(vector) == embedder.dim
    assert metadata["chunk"] == "0"
    assert "text" in metadata and metadata["text"]

    assert manifest.index_name == "demo-index"
    assert manifest.num_documents == 2
    assert manifest.num_chunks == len(store.add_calls)
    assert manifest.backend_type == type(store).__name__


def test_build_from_docs_respects_document_limit(builder_factory, docs_dir, tmp_path):
    builder, stores = builder_factory
    embedder = DummyEmbedModel(dim=2)

    sections = [{"content": f"Doc {i}", "metadata": {"doc_path": f"doc-{i}.md"}} for i in range(5)]

    builder.build_from_docs(
        source_dir=docs_dir,
        persist_path=tmp_path / "limited",
        embedding_model=embedder,
        chunk_size=512,
        chunk_overlap=0,
        document_processor=lambda _dir: sections,
        max_documents=2,
    )

    store = stores[0]
    # chunk_size is large enough to keep one chunk per doc
    assert len(store.add_calls) == 2


def test_default_document_processor_reads_text_and_markdown(tmp_path: Path):
    docs_root = tmp_path / "source"
    docs_root.mkdir()
    (docs_root / "intro.txt").write_text("Hello from txt", encoding="utf-8")
    sub = docs_root / "sub"
    sub.mkdir()
    (sub / "guide.md").write_text("# Heading\ncontent", encoding="utf-8")

    builder = IndexBuilder(lambda path, dim: DummyStore(path, dim))
    chunks = builder._default_document_processor(docs_root)

    assert len(chunks) == 2
    doc_paths = {chunk["metadata"]["doc_path"] for chunk in chunks}
    assert "intro.txt" in doc_paths
    assert "sub/guide.md" in doc_paths


def test_build_from_docs_requires_existing_directory(builder_factory, tmp_path: Path):
    builder, _ = builder_factory
    embedder = DummyEmbedModel()

    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        builder.build_from_docs(
            source_dir=missing,
            persist_path=tmp_path / "index",
            embedding_model=embedder,
        )
