"""Reference brute-force ANN for testing and smoke checks."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from sage.libs.anns.interface.base import AnnIndex, AnnIndexMeta
from sage.libs.anns.interface.factory import register


class DummyBruteForce(AnnIndex):
    """A simple brute-force ANN used for validation and tests."""

    def __init__(self, metric: str = "euclidean"):
        self._meta = AnnIndexMeta(name="dummy_bruteforce", metric=metric)
        self._metric = metric
        self._vectors: list[np.ndarray] = []
        self._ids: list[int] = []
        self._dim = 0

    @property
    def meta(self) -> AnnIndexMeta:
        return self._meta

    def setup(self, dtype: str, max_points: int, dim: int) -> None:  # noqa: ARG002
        self._dim = dim
        self._vectors = []
        self._ids = []

    def insert(self, vectors: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        if vectors.shape[1] != self._dim:
            raise ValueError(f"Expected dim={self._dim}, got {vectors.shape[1]}")
        for vec, vid in zip(vectors, ids):
            if int(vid) in self._ids:
                continue
            self._vectors.append(vec.astype(np.float32, copy=False))
            self._ids.append(int(vid))

    def delete(self, ids: npt.NDArray[np.uint32]) -> None:
        ids_set = {int(i) for i in ids}
        keep_vecs = []
        keep_ids = []
        for vec, vid in zip(self._vectors, self._ids):
            if vid not in ids_set:
                keep_vecs.append(vec)
                keep_ids.append(vid)
        self._vectors = keep_vecs
        self._ids = keep_ids

    def search(self, queries: np.ndarray, k: int):
        if len(self._vectors) == 0:
            n = len(queries)
            return (
                np.full((n, k), -1, dtype=np.int32),
                np.full((n, k), np.inf, dtype=np.float32),
            )

        data = np.stack(self._vectors, axis=0)
        ids_arr = np.array(self._ids, dtype=np.int32)

        if self._metric == "ip":
            dists = -np.dot(queries, data.T)
        else:
            dists = np.linalg.norm(data[np.newaxis, :, :] - queries[:, np.newaxis, :], axis=2)

        k_actual = min(k, data.shape[0])
        idx = np.argsort(dists, axis=1)[:, :k_actual]
        indices = ids_arr[idx]
        distances = np.take_along_axis(dists, idx, axis=1)

        if k > k_actual:
            indices_pad = np.full((len(queries), k), -1, dtype=np.int32)
            distances_pad = np.full((len(queries), k), np.inf, dtype=np.float32)
            indices_pad[:, :k_actual] = indices
            distances_pad[:, :k_actual] = distances
            return indices_pad, distances_pad

        return indices, distances


def register_dummy() -> None:
    """Register the dummy implementation with the global factory."""

    register("dummy_bruteforce", lambda **kwargs: DummyBruteForce(**kwargs))
