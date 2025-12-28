"""
Puck Algorithm Implementation
使用 PyCANDYAlgo.puck.PuckSearcher
"""

import os

import numpy as np

from ..base import BaseStreamingANN

try:
    from PyCANDYAlgo import puck

    PUCK_AVAILABLE = True
except ImportError:
    PUCK_AVAILABLE = False


class Puck(BaseStreamingANN):
    def __init__(self, metric, index_params):
        self.metric = metric
        self.index_params = index_params
        self.name = "puck"
        self.index = None
        self.indexkey = "NA"
        self.threads_count = index_params.get("threads_count", 1)
        self.context_pool_size = 2 * self.threads_count

    def setup(self, dtype, max_pts, ndim):
        if not PUCK_AVAILABLE:
            raise RuntimeError("PyCANDYAlgo.puck not available")

        self.ndim = ndim
        self.max_pts = max_pts

        self.index = puck.PuckSearcher()

        puck.update_gflag("max_point_stored", str(max_pts))
        puck.update_gflag("whether_norm", "false")
        puck.update_gflag("feature_dim", str(ndim))

        # Build indexkey from params
        self._init_indexkey()

        dataset = "streaming"
        puck.update_gflag("kmeans_iterations_count", "1")
        puck.update_gflag("threads_count", str(self.threads_count))
        puck.update_gflag("context_initial_pool_size", str(self.context_pool_size))

        index_path = f"data/{dataset}.{self.indexkey}.puckindex"
        puck.update_gflag("index_path", index_path)

        if not os.path.exists(index_path):
            os.makedirs(index_path, mode=0o777, exist_ok=True)

        if not os.path.exists("mid-data"):
            os.mkdir("mid-data")

        self.index.init()

    def _init_indexkey(self):
        # Coarse cluster count
        if "C" in self.index_params:
            puck.update_gflag("coarse_cluster_count", str(self.index_params["C"]))
            self.indexkey = f"C{self.index_params['C']}"

        # Fine cluster count
        if "F" in self.index_params:
            puck.update_gflag("fine_cluster_count", str(self.index_params["F"]))
            self.indexkey += f"_F{self.index_params['F']}"

        # Filter
        if "FN" in self.index_params:
            puck.update_gflag("filter_nsq", str(self.index_params["FN"]))
            self.indexkey += f"_FN{self.index_params['FN']}"

        # Quantization
        if "N" in self.index_params:
            if int(self.index_params["N"]) > 1:
                puck.update_gflag("whether_pq", "true")
                puck.update_gflag("nsq", str(self.index_params["N"]))
                self.indexkey += f"_N{self.index_params['N']}"
            else:
                puck.update_gflag("whether_pq", "false")
                self.indexkey += "_Flat"

        if "tinker_neighborhood" in self.index_params:
            puck.update_gflag("tinker_neighborhood", str(self.index_params["tinker_neighborhood"]))
            self.indexkey += f"_Neighborhood{self.index_params['tinker_neighborhood']}"

        if "tinker_construction" in self.index_params:
            puck.update_gflag("tinker_construction", str(self.index_params["tinker_construction"]))
            self.indexkey += f"_Construction{self.index_params['tinker_construction']}"

        if "index_type" in self.index_params:
            puck.update_gflag("index_type", str(self.index_params["index_type"]))

        if "radius_rate" in self.index_params:
            puck.update_gflag("radius_rate", str(self.index_params["radius_rate"]))
            self.indexkey += f"_RadiusRate{self.index_params['radius_rate']}"

        if "filter_topk" in self.index_params:
            puck.update_gflag("filter_topk", str(self.index_params["filter_topk"]))
            self.indexkey += f"_filter_topk{self.index_params['filter_topk']}"

    def insert(self, X, ids):
        n, d = X.shape
        self.index.batch_add(n, d, X.flatten(), ids.tolist())

    def delete(self, ids):
        n = len(ids)
        self.index.batch_delete(n, ids.tolist())

    def query(self, X, k):
        n, d = X.shape
        results = self.index.search(n, X.flatten(), k)
        res = np.array(results).reshape(n, k)
        self.res = res
        return res, None

    def set_query_arguments(self, query_args):
        for key, value in query_args.items():
            puck.update_gflag(key, str(value))
        puck.update_gflag("threads_count", str(self.threads_count))
        self.index.init()
