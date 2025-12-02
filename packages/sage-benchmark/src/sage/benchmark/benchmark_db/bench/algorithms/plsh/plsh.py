"""
PLSH Algorithm Implementation
使用 plsh_python.Index
"""

import numpy as np

from ..base import BaseStreamingANN

try:
    import plsh_python

    PLSH_AVAILABLE = True
except ImportError:
    PLSH_AVAILABLE = False


class Plsh(BaseStreamingANN):
    def __init__(self, metric, index_params):
        self.metric = metric
        self.index_params = index_params
        self.name = "plsh"
        self.is_built = False
        self.index = None
        self.insert_count = 0
        self.merge_threshold = index_params.get("merge_threshold", 50000)

    def setup(self, dtype, max_pts, ndim):
        if not PLSH_AVAILABLE:
            raise RuntimeError("plsh_python not available")

        self.ndim = ndim
        self.max_pts = max_pts

        k = self.index_params.get("k", 10)
        m = self.index_params.get("m", 5)
        num_threads = self.index_params.get("num_threads", 1)

        self.index = plsh_python.Index(ndim, k, m, num_threads)

    def insert(self, X, ids):
        X = X.astype(np.float32)
        ids = ids.astype(np.uint32)

        if not self.is_built:
            self.index.build(X, X.shape[0], ids.tolist())
            self.is_built = True
        else:
            self.index.insert(X, ids.tolist())
            self.insert_count += X.shape[0]

            if self.insert_count >= self.merge_threshold:
                self.index.merge_delta_to_static()
                self.insert_count = 0

    def delete(self, ids):
        # PLSH does not support deletion
        pass

    def query(self, X, k):
        X = X.astype(np.float32)
        n = X.shape[0]
        results = np.zeros((n, k), dtype=np.uint32)
        dists = np.zeros((n, k), dtype=np.float32)

        for i in range(n):
            tags, distances = self.index.query_topk(X[i], k)

            actual_k = min(len(tags), k)
            if actual_k > 0:
                results[i, :actual_k] = np.array(tags[:actual_k], dtype=np.uint32) - 1
                dists[i, :actual_k] = distances[:actual_k]

            if actual_k < k:
                if actual_k > 0:
                    results[i, actual_k:] = results[i, actual_k - 1]
                    dists[i, actual_k:] = np.inf
                else:
                    results[i, :] = 0
                    dists[i, :] = np.inf

        self.res = results
        return results, dists

    def set_query_arguments(self, query_args):
        pass
