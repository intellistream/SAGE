"""
GTI Algorithm Implementation
使用 gti_wrapper.GTIWrapper
"""

import numpy as np

from ..base import BaseStreamingANN

try:
    from gti_wrapper import GTIWrapper

    GTI_AVAILABLE = True
except ImportError:
    GTI_AVAILABLE = False


class Gti(BaseStreamingANN):
    def __init__(self, metric, index_params):
        self.metric = metric
        self.index_params = index_params
        self.name = "gti"
        self.is_built = False
        self.index = None

        # Extract parameters with defaults
        self.capacity_up_i = index_params.get("capacity_up_i", 100)
        self.capacity_up_l = index_params.get("capacity_up_l", 100)
        self.m = index_params.get("m", 4)
        self.query_L = 60

    def setup(self, dtype, max_pts, ndim):
        if not GTI_AVAILABLE:
            raise RuntimeError("gti_wrapper not available")

        self.ndim = ndim
        self.max_pts = max_pts
        self.dtype = dtype

        self.index = GTIWrapper()
        self.index.setup(max_pts, ndim, self.capacity_up_i, self.capacity_up_l, self.m)

    def insert(self, X, ids):
        X = np.ascontiguousarray(X.astype(np.float32))
        ids = ids.astype(np.int32)

        if not self.is_built:
            self.index.build(X, ids, self.capacity_up_i, self.capacity_up_l, self.m)
            self.is_built = True
        else:
            self.index.insert(X, ids)

    def delete(self, ids):
        if not self.is_built:
            return
        ids = ids.astype(np.int32)
        self.index.remove(ids)

    def query(self, X, k):
        if not self.is_built:
            raise RuntimeError("Index must be built before querying")

        X = np.ascontiguousarray(X.astype(np.float32))
        results, distances = self.index.query(X, k, self.query_L)
        self.res = results
        return results, distances

    def set_query_arguments(self, query_args):
        self.query_L = query_args.get("L", 60)
