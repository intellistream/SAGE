"""
Base algorithm interfaces for ANNS benchmarking in congestion scenarios
"""
from __future__ import absolute_import
import numpy as np
import numpy.typing as npt
from abc import ABC, abstractmethod


class BaseANN(ABC):
    """Base class for all ANN algorithms"""
    
    @abstractmethod
    def query(self, X, k):
        """
        Carry out a batch query for k-NN of query set X.
        
        Args:
            X: Query vectors (nq, d)
            k: Number of nearest neighbors to return
        """
        raise NotImplementedError()

    def get_results(self):
        """
        Return query results as (nq, k) array of integers representing indices.
        """
        return self.res

    def done(self):
        """Called after results have been processed. Use for cleanup."""
        pass


class BaseStreamingANN(BaseANN):
    """Base class for streaming ANN algorithms with insert/delete support"""
    
    @abstractmethod
    def setup(self, dtype, max_pts, ndims) -> None:
        """
        Initialize the data structures for the algorithm.
        
        Args:
            dtype: Data type ('uint8', 'int8', 'float32')
            max_pts: Upper bound on non-deleted points
            ndims: Dimensionality of vectors
        """
        raise NotImplementedError()
        
    @abstractmethod
    def insert(self, X: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        """
        Insert vectors into the index.
        
        Args:
            X: Vectors to insert (num_vectors, num_dims)
            ids: IDs for each vector (num_vectors,)
        """
        raise NotImplementedError()
    
    @abstractmethod
    def delete(self, ids: npt.NDArray[np.uint32]) -> None:
        """
        Delete vectors from the index.
        
        Args:
            ids: IDs of vectors to delete
        """
        raise NotImplementedError()

    def set_query_arguments(self, query_args):
        """Set algorithm-specific query parameters"""
        pass

    def index_name(self, name):
        """Return index filename for this algorithm and dataset"""
        return f"data/{name}.index"


class BaseCongestionANN(BaseANN):
    """
    Base class for congestion-aware ANN algorithms.
    Supports concurrent insert/delete/query operations with drop handling.
    """
    
    @abstractmethod
    def setup(self, dtype, max_pts, ndims) -> None:
        """Initialize the algorithm with dataset parameters"""
        raise NotImplementedError()
    
    @abstractmethod
    def startHPC(self):
        """Start background worker threads for concurrent operations"""
        raise NotImplementedError()
    
    @abstractmethod
    def endHPC(self):
        """Stop background worker threads"""
        raise NotImplementedError()
    
    @abstractmethod
    def initial_load(self, X, ids):
        """Load initial dataset before streaming operations"""
        raise NotImplementedError()
    
    @abstractmethod
    def insert(self, X, ids):
        """Insert vectors with congestion handling"""
        raise NotImplementedError()
    
    @abstractmethod
    def delete(self, ids):
        """Delete vectors by IDs"""
        raise NotImplementedError()
    
    @abstractmethod
    def waitPendingOperations(self):
        """Wait for all pending operations to complete"""
        raise NotImplementedError()
    
    def reset_index(self):
        """Reset index to initial state"""
        raise NotImplementedError()
    
    def get_drop_count_delta(self):
        """Get number of dropped operations since last call"""
        return 0
    
    def get_pending_queue_len(self):
        """Get current pending queue length"""
        return 0
    
    def enableScenario(self, **kwargs):
        """Enable special test scenarios (random drop, contamination, etc.)"""
        pass
    
    def setBackpressureLogic(self, use_backpressure=False):
        """Configure backpressure logic for queue management"""
        pass
