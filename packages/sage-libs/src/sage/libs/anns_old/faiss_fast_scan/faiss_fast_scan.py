"""
Faiss Fast Scan Algorithm Implementation
使用 PyCANDYAlgo 封装的 faiss 接口
"""

import numpy as np

from ..base import BaseStreamingANN

try:
    import PyCANDYAlgo

    PYCANDY_AVAILABLE = True
except ImportError:
    PYCANDY_AVAILABLE = False


class FaissFastScan(BaseStreamingANN):
    def __init__(self, metric, index_params):
        if index_params.get("indexkey") is None:
            self.indexkey = "IVF50,PQ10x4fsr_64"
        else:
            self.indexkey = index_params["indexkey"]
        self.metric = metric
        self.name = "faiss_fast_scan"
        self.ef = 16
        self.trained = False
        self.index = None
        self.ntotal = 0

        # ID 映射：faiss 内部 ID <-> 外部 ID
        self.my_index = None
        self.my_inverse_index = None

    def setup(self, dtype, max_pts, ndim):
        if not PYCANDY_AVAILABLE:
            raise RuntimeError("PyCANDYAlgo not available")

        if self.metric == "euclidean":
            self.index = PyCANDYAlgo.index_factory_l2(ndim, self.indexkey)
        else:
            self.index = PyCANDYAlgo.index_factory_ip(ndim, self.indexkey)

        self.my_index = -1 * np.ones(max_pts, dtype=int)
        self.my_inverse_index = -1 * np.ones(max_pts, dtype=int)
        self.ntotal = 0

    def insert(self, X, ids):
        X = X.astype(np.float32)
        mask = self.my_inverse_index[ids] == -1
        new_ids = ids[mask]
        new_data = X[mask]

        if new_data.shape[0] == 0:
            print("Not Inserting Same Data!")
            return

        if not self.trained:
            self.index.train(new_data.shape[0], new_data.flatten())
            self.index.add(new_data.shape[0], new_data.flatten())
            self.trained = True
        else:
            self.index.add(new_data.shape[0], new_data.flatten())

        indices = np.arange(self.ntotal, self.ntotal + new_data.shape[0])
        self.my_index[indices] = new_ids
        self.my_inverse_index[new_ids] = indices
        self.ntotal += new_data.shape[0]
        print(f"Faiss indices {indices[0]}:{indices[-1]} to Global {new_ids[0]}:{new_ids[-1]}")

    def delete(self, ids):
        for ext_id in ids:
            ext_id = int(ext_id)
            if ext_id < len(self.my_inverse_index):
                internal_id = self.my_inverse_index[ext_id]
                if internal_id != -1:
                    self.my_inverse_index[ext_id] = -1
                    if internal_id < len(self.my_index):
                        self.my_index[internal_id] = -1

    def query(self, X, k):
        X = X.astype(np.float32)
        query_size = X.shape[0]
        results = np.array(self.index.search(query_size, X.flatten(), k, self.ef))
        ids = self.my_index[results]
        res = ids.reshape(X.shape[0], k)
        self.res = res
        return res, None

    def set_query_arguments(self, query_args):
        self.ef = query_args.get("ef", 16)

    def get_results(self):
        return self.res
