"""Unit tests for `IndexManifest` helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sage.middleware.operators.rag.index_builder.manifest import IndexManifest


def test_manifest_roundtrip_and_helpers(tmp_path: Path):
    persist = tmp_path / "db"
    created_at = (datetime.utcnow() - timedelta(seconds=5)).isoformat()

    manifest = IndexManifest(
        index_name="docs",
        backend_type="DummyStore",
        persist_path=persist,
        source_dir="docs-src",
        embedding_config={"model": "tiny", "dim": 3},
        chunk_size=256,
        chunk_overlap=64,
        num_documents=10,
        num_chunks=123,
        created_at=created_at,
        metadata={"env": "test"},
    )

    data = manifest.to_dict()
    assert data["persist_path"] == str(persist)

    restored = IndexManifest.from_dict(data)
    assert restored.persist_path == persist
    assert restored.embedding_config == manifest.embedding_config
    assert restored.metadata["env"] == "test"
    assert restored.num_chunks == 123

    # Age helper should be close to the delta we set
    assert restored.age_seconds >= 5
    assert not restored.is_empty
    assert "docs" in repr(restored)

    empty_manifest = IndexManifest(
        index_name="empty",
        backend_type="DummyStore",
        persist_path=persist,
        source_dir="docs-src",
        embedding_config={"model": "tiny", "dim": 3},
        chunk_size=256,
        chunk_overlap=64,
        num_documents=0,
        num_chunks=0,
        created_at=datetime.utcnow().isoformat(),
    )

    assert empty_manifest.is_empty is True
