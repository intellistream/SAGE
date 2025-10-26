#!/usr/bin/env python3
"""Minimal SageDB quickstart demo for the pluggable ANNS stack."""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

# Ensure we can import the locally built extension/module without installation.
REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGES_ROOT = REPO_ROOT / "packages"
if str(PACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGES_ROOT))

try:
    import _sage_db  # type: ignore[import]
except ImportError as exc:  # pragma: no cover - the example should exit cleanly
    raise SystemExit(
        "❌ Unable to import _sage_db. Install the extension by running:\n"
        "   sage extensions install sage_db  # add --force to rebuild"
    ) from exc


def build_config(dimension: int = 4) -> _sage_db.DatabaseConfig:
    """Create a DatabaseConfig wired to the default brute-force plugin."""
    cfg = _sage_db.DatabaseConfig(dimension)
    cfg.metric = _sage_db.DistanceMetric.L2
    cfg.index_type = _sage_db.IndexType.AUTO  # delegate selection to the plugin
    cfg.anns_algorithm = "brute_force"
    cfg.anns_build_params = {"metric": "l2"}
    cfg.anns_query_params = {"nprobe": "1"}
    return cfg


def make_demo_vectors() -> list[list[float]]:
    """Create a tiny set of 4D vectors arranged on a circle for easy inspection."""
    base_angles = [0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4, math.pi]
    vectors: list[list[float]] = []
    for idx, angle in enumerate(base_angles):
        vectors.append(
            [
                math.cos(angle),
                math.sin(angle),
                0.25 * (-1) ** idx,
                0.1 * idx,
            ]
        )
    return vectors


def add_vectors(db: _sage_db.SageDB, vectors: list[list[float]]) -> list[int]:
    """Insert vectors with metadata and return their ids."""
    ids: list[int] = []
    rng = random.Random(42)
    for i, vec in enumerate(vectors, start=1):
        metadata: dict[str, str] = {
            "label": f"demo-{i}",
            "quadrant": str((i - 1) % 4 + 1),
            "color": rng.choice(["red", "green", "blue", "yellow"]),
        }
        vec_id = db.add(vec, metadata)
        ids.append(vec_id)
        print(f"➕ inserted vector #{i} -> id={vec_id}, metadata={metadata}")
    return ids


def run_search(db: _sage_db.SageDB, query: list[float]) -> None:
    params = _sage_db.SearchParams(k=3)
    params.include_metadata = True
    params.nprobe = 1

    print("\n🔎 running 3-NN search for:", query)
    results = db.search(query, params)
    for rank, result in enumerate(results, start=1):
        print(
            f"  {rank}. id={result.id:>3}  score={result.score:.4f}  metadata={result.metadata}"
        )


def demonstrate_updates(db: _sage_db.SageDB, target_id: int) -> None:
    print(
        f"\n🛠️ updating vector id={target_id} to move it closer to the query direction"
    )
    new_vector = [0.8, 0.6, 0.0, 0.0]
    db.update(target_id, new_vector, {"label": "demo-updated", "quadrant": "1"})
    print("   metadata now:", db.get_metadata(target_id))


def demonstrate_persistence(db: _sage_db.SageDB, query: list[float]) -> None:
    print("\n💾 saving database to a temporary location and loading it back")
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "demo_db"
        db.save(str(db_path))
        print(f"   saved artefacts to {db_path}")

        # Restore using a fresh instance with the same configuration
        cfg = _sage_db.DatabaseConfig(db.dimension())
        cfg.metric = db.config().metric
        cfg.index_type = db.config().index_type
        cfg.anns_algorithm = db.config().anns_algorithm
        cfg.anns_build_params = dict(db.config().anns_build_params)
        cfg.anns_query_params = dict(db.config().anns_query_params)

        reloaded = _sage_db.SageDB(cfg)
        reloaded.load(str(db_path))
        print("   reloaded DB size:", reloaded.size())
        run_search(reloaded, query)


def main() -> None:
    print("=== SageDB Quickstart ===")
    cfg = build_config()
    db = _sage_db.SageDB(cfg)

    vectors = make_demo_vectors()
    ids = add_vectors(db, vectors)

    db.build_index()
    print("📦 total vectors:", db.size())

    query = [0.9, 0.3, 0.0, 0.0]
    run_search(db, query)

    demonstrate_updates(db, ids[0])
    run_search(db, query)

    print("\n🗑️ removing the furthest vector and rebuilding the index")
    db.remove(ids[-1])
    db.build_index()
    print("   size after removal:", db.size())
    run_search(db, query)

    demonstrate_persistence(db, query)

    print("\n📄 current configuration:")
    print(
        json.dumps(
            {
                "dimension": db.dimension(),
                "metric": db.config().metric.name,
                "anns_algorithm": db.config().anns_algorithm,
                "anns_build_params": dict(db.config().anns_build_params),
                "anns_query_params": dict(db.config().anns_query_params),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    np.random.seed(0)
    main()
