"""
CANDY LSHAPG Algorithm Implementation
"""

import numpy as np
import torch

from ..base import BaseStreamingANN

try:
    import PyCANDYAlgo

    PYCANDY_AVAILABLE = True
except ImportError:
    PYCANDY_AVAILABLE = False


class CandyLshapg(BaseStreamingANN):
    def __init__(self, metric, index_params):
        self.indexkey = index_params.get("indexkey", "LSHAPG")
        self.metric = metric
        self.name = "candy_lshapg"
        self.ef = 16
        self.trained = False
        self.index = None
        self.my_index = None
        self.my_inverse_index = None
        self.ntotal = 0

    def setup(self, dtype, max_pts, ndim):
        if not PYCANDY_AVAILABLE:
            raise RuntimeError("PyCANDYAlgo not available")

        self.index = PyCANDYAlgo.createIndex(self.indexkey, ndim)

        cm = PyCANDYAlgo.ConfigMap()
        if self.metric == "euclidean":
            cm.edit("metricType", "L2")
        else:
            cm.edit("metricType", "IP")
        cm.edit("indexTag", self.indexkey)
        cm.edit("vecDim", ndim)
        self.index.setConfig(cm)

        self.my_index = -1 * np.ones(max_pts, dtype=int)
        self.my_inverse_index = -1 * np.ones(max_pts, dtype=int)
        self.ntotal = 0

    def insert(self, X, ids):
        mask = self.my_inverse_index[ids] == -1
        new_ids = ids[mask]
        new_data = X[mask]

        if new_data.shape[0] != 0:
            subA = torch.from_numpy(new_data.copy())
            if self.trained:
                self.index.insertTensorWithIds(new_ids, subA)
            else:
                self.index.loadInitialTensorWithIds(new_ids, subA)
                self.trained = True

            indices = np.arange(self.ntotal, self.ntotal + new_data.shape[0])
            self.my_index[indices] = new_ids
            self.my_inverse_index[new_ids] = indices
            self.ntotal += new_data.shape[0]

    def delete(self, ids):
        self.index.deleteIndex(ids)

    def query(self, X, k):
        queryTensor = torch.from_numpy(X.copy())
        results = np.array(self.index.searchIndex(queryTensor, k))
        ids = self.my_index[results]
        self.res = ids.reshape(X.shape[0], k)

    def set_query_arguments(self, query_args):
        self.ef = query_args.get("ef", 16)

    def get_results(self):
        return self.res
