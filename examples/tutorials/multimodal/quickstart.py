#!/usr/bin/env python3
"""Quick tour of the MultimodalSageDB helper with text+image content."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SAGE_MIDDLEWARE_SRC = REPO_ROOT / "packages" / "sage-middleware" / "src"
if str(SAGE_MIDDLEWARE_SRC) not in sys.path:
    sys.path.insert(0, str(SAGE_MIDDLEWARE_SRC))

from sage.middleware.components.sage_db.python.multimodal_sage_db import (  # noqa: E402
    ModalityType,
    MultimodalSearchParams,
    create_text_image_db,
)


def make_embedding(seed: int, dimension: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vec = rng.normal(size=dimension).astype("float32")
    norm = np.linalg.norm(vec) + 1e-12
    return vec / norm


def build_dataset() -> Dict[str, Dict[str, Any]]:
    return {
        "aurora": {
            "text": make_embedding(1, 768),
            "image": make_embedding(2, 512),
            "meta": {"genre": "photography", "location": "iceland"},
        },
        "latte-art": {
            "text": make_embedding(3, 768),
            "image": make_embedding(4, 512),
            "meta": {"genre": "food", "mood": "cozy"},
        },
        "city-skyline": {
            "text": make_embedding(5, 768),
            "image": make_embedding(6, 512),
            "meta": {"genre": "architecture", "time": "night"},
        },
        "trail-run": {
            "text": make_embedding(7, 768),
            "image": make_embedding(8, 512),
            "meta": {"genre": "outdoor", "mood": "energetic"},
        },
        "catnap": {
            "text": make_embedding(9, 768),
            "image": make_embedding(10, 512),
            "meta": {"genre": "pets", "mood": "calm"},
        },
    }


def populate(db, items: Dict[str, Dict[str, Any]]) -> None:
    for name, payload in items.items():
        embeddings = {
            ModalityType.TEXT: payload["text"],
            ModalityType.IMAGE: payload["image"],
        }
        data_id = db.add_from_embeddings(embeddings, {"label": name, **payload["meta"]})
        print(f"➕ added '{name}' -> id={data_id}")


def main() -> None:
    print("=== Multimodal text+image quickstart ===")

    db = create_text_image_db(dimension=512)
    native = getattr(db, "_db", None) is not None
    print(
        "Backend:",
        "C++ accelerated" if native else "Python mock (build to enable native)",
    )

    dataset = build_dataset()
    populate(db, dataset)

    params = MultimodalSearchParams(k=3)
    params.query_fusion_params.target_dimension = 512

    query = {
        ModalityType.TEXT: make_embedding(11, 768),
        ModalityType.IMAGE: make_embedding(12, 512),
    }

    print("\n🔎 fused retrieval (text + image cues)")
    results = db.search_multimodal(query, params)
    for idx, result in enumerate(results, start=1):
        print(f"  {idx}. id={result.id:>2} score={result.score:.4f} metadata={result.metadata}")

    stats = db.get_modality_statistics()
    print("\n📊 modality stats:")
    for modality, info in stats.items():
        print(f"  {modality.name:<6} -> count={info['count']} avg_dim={info['avg_dimension']:.1f}")


if __name__ == "__main__":
    main()
