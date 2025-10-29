#!/usr/bin/env python3
"""Cross-modal retrieval demo highlighting fusion vs. single-modality ranking."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SAGE_MIDDLEWARE_SRC = REPO_ROOT / "packages" / "sage-middleware" / "src"
if str(SAGE_MIDDLEWARE_SRC) not in sys.path:
    sys.path.insert(0, str(SAGE_MIDDLEWARE_SRC))

from sage.middleware.components.sage_db.python.multimodal_sage_db import (  # noqa: E402
    FusionParams,
    FusionStrategy,
    ModalityType,
    MultimodalSearchParams,
    create_text_image_db,
)


def seeded_embedding(seed: int, dim: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vec = rng.normal(size=dim).astype("float32")
    return vec / (np.linalg.norm(vec) + 1e-12)


def sample_collection() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    return {
        "sunrise-cliffs": (seeded_embedding(21, 768), seeded_embedding(22, 512)),
        "rooftop-dusk": (seeded_embedding(23, 768), seeded_embedding(24, 512)),
        "forest-trail": (seeded_embedding(25, 768), seeded_embedding(26, 512)),
        "city-rain": (seeded_embedding(27, 768), seeded_embedding(28, 512)),
        "gallery-exhibit": (seeded_embedding(29, 768), seeded_embedding(30, 512)),
    }


def load_demo_db():
    db = create_text_image_db(dimension=512)
    for name, (text_emb, image_emb) in sample_collection().items():
        db.add_from_embeddings(
            {
                ModalityType.TEXT: text_emb,
                ModalityType.IMAGE: image_emb,
            },
            {"label": name, "collection": "demo"},
        )
    return db


def describe_results(title: str, results) -> None:
    print(f"\n{title}")
    for idx, result in enumerate(results, start=1):
        print(
            f"  {idx}. id={result.id:>2} score={result.score:.4f} metadata={result.metadata}"
        )


def main() -> None:
    print("=== Cross-modal search walkthrough ===")

    db = load_demo_db()
    backend = (
        "C++ accelerated" if getattr(db, "_db", None) is not None else "Python mock"
    )
    print("Backend:", backend)

    query_text = seeded_embedding(31, 768)
    query_image = seeded_embedding(32, 512)

    fused_params = MultimodalSearchParams(k=3)
    fused_params.query_fusion_params.strategy = FusionStrategy.WEIGHTED_AVERAGE

    fusion_results = db.search_multimodal(
        {ModalityType.TEXT: query_text, ModalityType.IMAGE: query_image}, fused_params
    )
    describe_results("🔗 Fusion search (text + image)", fusion_results)

    cross_params = MultimodalSearchParams(k=3)
    cross_params.use_cross_modal_search = True
    cross_params.target_modalities = [ModalityType.IMAGE]
    cross_results = db.cross_modal_search(
        ModalityType.TEXT,
        query_text,
        target_modalities=[ModalityType.IMAGE],
        params=cross_params,
    )
    describe_results("🧭 Text → image cross search", cross_results)

    print("\n🎛️ Re-weighting modalities (text emphasis)")
    tuned = FusionParams(strategy=FusionStrategy.WEIGHTED_AVERAGE)
    tuned.modality_weights[ModalityType.TEXT] = 0.7
    tuned.modality_weights[ModalityType.IMAGE] = 0.3
    db.update_fusion_params(tuned)

    adjusted_results = db.search_multimodal(
        {ModalityType.TEXT: query_text, ModalityType.IMAGE: query_image}, fused_params
    )
    describe_results("🎯 Fusion search after weight tweak", adjusted_results)


if __name__ == "__main__":
    main()
