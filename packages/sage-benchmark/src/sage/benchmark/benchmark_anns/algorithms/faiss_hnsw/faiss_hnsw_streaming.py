"""
Faiss HNSW algorithm for streaming ANNS
"""
import numpy as np
from numpy import typing as npt

try:
    import PyCANDYAlgo
    HAS_PYCANDY = True
except ModuleNotFoundError:
    HAS_PYCANDY = False
    print("Warning: PyCANDYAlgo not found, FaissHNSW will not work")

from benchmark_anns.core import BaseStreamingANN


class FaissHNSW(BaseStreamingANN):
    """
    Faiss HNSW implementation for streaming scenarios.
    Supports insert and query operations (delete is no-op).
    """
    
    def __init__(self, metric, index_params):
        """
        Args:
            metric: Distance metric ('euclidean' or 'angular')
            index_params: Dictionary containing 'indexkey' parameter
        """
        if not HAS_PYCANDY:
            raise ModuleNotFoundError("PyCANDYAlgo is required for FaissHNSW")
        
        self.indexkey = index_params.get('indexkey', 'HNSW32')
        self.metric = metric
        self.name = "faiss_hnsw"
        self.ef = 16
        self.trained = False
        
        self.index = None
        self.my_index = None  # Maps faiss index id -> global id
        self.my_inverse_index = None  # Maps global id -> faiss index id
        self.ntotal = 0

    def setup(self, dtype, max_pts, ndim):
        """Initialize the index structure"""
        # Create index based on metric
        if self.metric == 'euclidean':
            self.index = PyCANDYAlgo.index_factory_l2(ndim, self.indexkey)
        else:  # angular / IP
            self.index = PyCANDYAlgo.index_factory_ip(ndim, self.indexkey)
        
        # Initialize ID mappings
        # my_index[faiss_id] = global_id
        self.my_index = -1 * np.ones(max_pts, dtype=np.int32)
        # my_inverse_index[global_id] = faiss_id
        self.my_inverse_index = -1 * np.ones(max_pts, dtype=np.int32)
        
        self.ntotal = 0
        self.trained = False
        
        print(f"FaissHNSW setup: metric={self.metric}, indexkey={self.indexkey}, "
              f"dtype={dtype}, max_pts={max_pts}, ndim={ndim}")

    def insert(self, X, ids):
        """
        Insert vectors into the index.
        
        Args:
            X: Vectors to insert (num_vectors, num_dims)
            ids: IDs for each vector (num_vectors,)
        """
        if X.shape[0] == 0:
            return
        
        # Filter out already-inserted IDs
        mask = self.my_inverse_index[ids] == -1
        new_ids = ids[mask]
        new_data = X[mask]
        
        if new_data.shape[0] == 0:
            print("Not inserting duplicate data!")
            return
        
        # Train and add data
        if self.trained:
            self.index.add(new_data.shape[0], new_data.flatten())
        else:
            self.index.train(new_data.shape[0], new_data.flatten())
            self.index.add(new_data.shape[0], new_data.flatten())
            self.trained = True
        
        # Update ID mappings
        indices = np.arange(self.ntotal, self.ntotal + new_data.shape[0], dtype=np.int32)
        self.my_index[indices] = new_ids
        self.my_inverse_index[new_ids] = indices
        
        if self.ntotal == 0 or (self.ntotal + new_data.shape[0] - 1) % 10000 < new_data.shape[0]:
            print(f"Faiss indices {indices[0]} : {indices[-1]} -> "
                  f"Global {new_ids[0]}:{new_ids[-1]}")
        
        self.ntotal += new_data.shape[0]

    def delete(self, ids):
        """
        Delete operation (not supported by basic HNSW).
        This is a no-op placeholder.
        """
        # HNSW doesn't support efficient deletion
        # In a real implementation, this might mark vectors as deleted
        pass

    def query(self, X, k):
        """
        Query k nearest neighbors for each query vector.
        
        Args:
            X: Query vectors (nq, d)
            k: Number of nearest neighbors
        """
        if X.shape[0] == 0:
            self.res = np.array([]).reshape(0, k)
            return
        
        query_size = X.shape[0]
        
        # Perform search
        results = np.array(self.index.search(query_size, X.flatten(), k, self.ef))
        
        # Map faiss indices back to global IDs
        ids = self.my_index[results]
        self.res = ids.reshape(query_size, k)

    def set_query_arguments(self, query_args):
        """Set query-time parameters"""
        if "ef" in query_args:
            self.ef = query_args['ef']
        else:
            self.ef = 16
        print(f"FaissHNSW query ef set to {self.ef}")

    def index_name(self, name):
        """Return index filename for this algorithm"""
        return f"data/{name}.{self.indexkey}.faiss_hnsw.index"
