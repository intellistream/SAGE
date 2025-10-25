#!/usr/bin/env python3
"""Showcase for the FAISS ANNS plugin with graceful fallback when unavailable."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGES_ROOT = REPO_ROOT / "packages"
if str(PACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGES_ROOT))

try:
    import _sage_db  # type: ignore[import]
except ImportError as exc:  # pragma: no cover - documented failure mode
    raise SystemExit(
        "❌ Unable to import _sage_db. Please install the extension with:\n"
        "   sage extensions install sage_db  # add --force to rebuild"
    ) from exc


def build_faiss_config(dimension: int = 8) -> _sage_db.DatabaseConfig:
    cfg = _sage_db.DatabaseConfig(dimension)
    cfg.metric = _sage_db.DistanceMetric.COSINE
    cfg.index_type = _sage_db.IndexType.AUTO
    cfg.anns_algorithm = "FAISS"
    cfg.anns_build_params = {
        "index_type": "ivf_flat",
        "metric": "cosine",
        "nlist": "16",
        "auto_threshold_ivf": "200",
    }
    cfg.anns_query_params = {
        "nprobe": "4",
        "efSearch": "64",
    }
    return cfg


def build_fallback_config(dimension: int = 8) -> _sage_db.DatabaseConfig:
    cfg = _sage_db.DatabaseConfig(dimension)
    cfg.metric = _sage_db.DistanceMetric.COSINE
    cfg.index_type = _sage_db.IndexType.AUTO
    cfg.anns_algorithm = "brute_force"
    cfg.anns_build_params = {"metric": "cosine"}
    cfg.anns_query_params = {"nprobe": "1"}
    return cfg


def generate_vectors(dim: int, count: int = 64) -> tuple[np.ndarray, list[dict[str, str]]]:
    rng = np.random.default_rng(seed=13)
    raw = rng.normal(size=(count, dim)).astype("float32")
    # Normalise to unit vectors for cosine distance
    norms = np.linalg.norm(raw, axis=1, keepdims=True) + 1e-12
    vectors = raw / norms
    metadata: list[dict[str, str]] = []
    for idx in range(count):
        metadata.append(
            {
                "id": f"vec-{idx}",
                "bucket": str(idx // 8),
                "parity": "even" if idx % 2 == 0 else "odd",
            }
        )
    return vectors, metadata


def ingest_numpy_batch(
    db: _sage_db.SageDB, vectors: np.ndarray, metadata: list[dict[str, str]]
) -> None:
    print(f"➕ ingesting {len(vectors)} vectors via add_batch (numpy)")
    _sage_db.add_numpy(db, vectors, metadata)
    print("   stored vectors:", db.size())


def run_demo(db: _sage_db.SageDB, query: np.ndarray) -> None:
    params = _sage_db.SearchParams(5)
    params.include_metadata = True
    params.nprobe = 4

    print("\n🔍 Top-5 cosine neighbours for query vector")
    results = _sage_db.search_numpy(db, query, params)
    for rank, res in enumerate(results, start=1):
        print(f"  {rank}. id={res.id:>3} score={res.score:.4f} metadata={res.metadata}")

    engine = db.query_engine()
    stats = engine.get_last_search_stats()
    print(
        f"   stats: candidates={stats.total_candidates} filter={stats.filtered_candidates} "
        f"time={stats.total_time_ms:.3f}ms"
    )


def main() -> None:
    vectors, metadata = generate_vectors(dim=8)
    query = vectors[0] * 0.95 + vectors[1] * 0.05

    print("=== SageDB FAISS plugin demo ===")

    cfg = build_faiss_config(dimension=vectors.shape[1])
    try:
        db = _sage_db.SageDB(cfg)
        ingest_numpy_batch(db, vectors, metadata)
        db.build_index()
        print("✅ FAISS index built successfully")
    except (_sage_db.SageDBException, RuntimeError) as exc:
        print("⚠️ FAISS backend unavailable, falling back to brute_force:\n   ", exc)
        cfg = build_fallback_config(dimension=vectors.shape[1])
        db = _sage_db.SageDB(cfg)
        ingest_numpy_batch(db, vectors, metadata)
        db.build_index()
        print("✅ fallback brute_force index built")

    run_demo(db, query)

    print("\nℹ️ resolved config:")
    print(
        {
            "algorithm": db.config().anns_algorithm,
            "metric": db.config().metric.name,
            "anns_build_params": dict(db.config().anns_build_params),
            "anns_query_params": dict(db.config().anns_query_params),
        }
    )


if __name__ == "__main__":
    main()
