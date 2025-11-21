"""
Faiss HNSW algorithm for congestion scenarios
"""
from benchmark_anns.core import CongestionANN
from .faiss_hnsw_streaming import FaissHNSW as FaissHNSWStreaming


class FaissHNSW(CongestionANN):
    """
    Congestion-aware Faiss HNSW implementation.
    Wraps the streaming version with multi-worker congestion handling.
    """
    
    def __init__(self, metric, index_params, parallel_workers=1):
        """
        Args:
            metric: Distance metric ('euclidean' or 'angular')
            index_params: Dictionary containing index parameters
            parallel_workers: Number of parallel workers
        """
        # Create underlying streaming algorithms for each worker
        streaming_algos = [
            FaissHNSWStreaming(metric, index_params) 
            for _ in range(parallel_workers)
        ]
        
        super().__init__(
            index_algos=streaming_algos,
            metric=metric,
            index_params=index_params,
            parallel_workers=parallel_workers,
            single_worker_opt=True,
            clear_pending_operations=True
        )
        
        self.metric = metric
        self.indexkey = index_params.get('indexkey', 'HNSW32')
        self.name = "faiss_hnsw_congestion"

    def set_query_arguments(self, query_args):
        """Set query parameters for all workers"""
        super().set_query_arguments(query_args)
