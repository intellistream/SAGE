"""
IP-DiskANN Algorithm Implementation
使用 ipdiskann 库的接口
"""

import numpy as np

from ..base import BaseStreamingANN

try:
    import ipdiskann

    IPDISKANN_AVAILABLE = True
except ImportError:
    IPDISKANN_AVAILABLE = False


class Ipdiskann(BaseStreamingANN):
    def __init__(self, metric, index_params):
        self.metric = metric
        self.index_params = index_params
        self.name = "ipdiskann"
        self.is_built = False
        self.index = None

    def setup(self, dtype, max_pts, ndim):
        if not IPDISKANN_AVAILABLE:
            raise RuntimeError("ipdiskann not available")

        self.ndim = ndim
        self.max_pts = max_pts
        self.index = ipdiskann.Index()

        R = self.index_params.get("R", 64)
        L = self.index_params.get("L", 100)
        num_threads = self.index_params.get("num_threads", 1)
        self.insert_thread_count = self.index_params.get("insert_thread_count", 1)
        self.search_thread_count = self.index_params.get("search_thread_count", 1)
        self.index.setup(max_pts, ndim, R, L, num_threads)

    def insert(self, X, ids):
        X = X.astype(np.float32)
        ids = ids.astype(np.uint32) + 1

        if not self.is_built:
            self.index.build(X, X.shape[0], ids.tolist())
            self.is_built = True
        else:
            self.index.insert_concurrent(X, ids, self.insert_thread_count)

    def delete(self, ids):
        ids = ids.astype(np.uint32) + 1
        self.index.remove(ids.tolist())

    def query(self, X, k):
        n = X.shape[0]
        results = np.zeros((n, k), dtype=np.uint32)
        dists = np.zeros((n, k), dtype=np.float32)

        for i in range(n):
            query_vec = X[i].astype(np.float32)
            tags, distances = self.index.query(query_vec, k)
            results[i] = np.array(tags, dtype=np.uint32) - 1
            dists[i] = distances

        self.res = results
        return results, dists

    def set_query_arguments(self, query_args):
        self.query_L = query_args.get("L", 128)

    def get_results(self):
        return self.res
