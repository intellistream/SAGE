"""
Congestion-aware ANN algorithm implementation with multiple workers
"""
from typing import List, Optional, Tuple
import time
import numpy as np

from benchmark_anns.core.base_algorithm import BaseCongestionANN
from benchmark_anns.core.congestion_worker import CongestionWorker


class CongestionANN(BaseCongestionANN):
    """
    Multi-worker congestion-aware ANN algorithm wrapper.
    Distributes operations across parallel workers with congestion handling.
    """
    
    def __init__(self, index_algos, metric, index_params, 
                 parallel_workers=1, fine_grained=False,
                 single_worker_opt=True, clear_pending_operations=True,
                 queue_capacity=10):
        """
        Args:
            index_algos: List of underlying index algorithm instances
            metric: Distance metric ('euclidean' or 'angular')
            index_params: Parameters for the index
            parallel_workers: Number of parallel workers
            fine_grained: Whether to use fine-grained parallel insert
            single_worker_opt: Enable single-worker optimizations
            clear_pending_operations: Whether to clear pending ops on wait
            queue_capacity: Capacity of operation queues
        """
        self.parallel_workers = parallel_workers
        self.insert_idx = 0
        self.fine_grained_parallel_insert = fine_grained
        self.single_worker_opt = single_worker_opt
        self.clear_pending_operations = clear_pending_operations
        self.verbose = False
        
        # Worker management
        self.workers: List[CongestionWorker] = []
        self.workerMap: List[int] = []
        
        # State tracking
        self._drop_snapshot = 0
        self._last_setup_params: Optional[Tuple[str, int, int]] = None
        self._hpc_active = False
        
        # Create workers
        for i in range(parallel_workers):
            worker = CongestionWorker(index_algos[i], queue_capacity=queue_capacity)
            worker.single_worker_opt = single_worker_opt
            self.workers.append(worker)

    def setup(self, dtype, max_pts, ndims) -> None:
        """Initialize all workers with dataset parameters"""
        for i in range(self.parallel_workers):
            worker = self.workers[i]
            worker.setup(dtype, max_pts, ndims)
            worker.my_id = i
        self._last_setup_params = (dtype, max_pts, ndims)

    def startHPC(self):
        """Start all background worker threads"""
        if self._hpc_active:
            return
        for i in range(self.parallel_workers):
            self.workers[i].startHPC()
        self._hpc_active = True

    def endHPC(self):
        """Stop all background worker threads"""
        if not self._hpc_active:
            return
        for i in range(self.parallel_workers):
            self.workers[i].endHPC()
        for i in range(self.parallel_workers):
            self.workers[i].join_thread()
        self._hpc_active = False

    def waitPendingOperations(self):
        """Wait for all pending operations to complete"""
        if self.clear_pending_operations:
            if self.verbose:
                print("CLEAR CURRENT OPERATION QUEUE!")
            for i in range(self.parallel_workers):
                while (self.workers[i].insert_queue.size() != 0 or 
                       self.workers[i].delete_queue.size() != 0):
                    self.workers[i].waitPendingOperations()
            return
        
        for i in range(self.parallel_workers):
            self.workers[i].waitPendingOperations()

    def initial_load(self, X, ids):
        """Load initial dataset before streaming operations"""
        if self.parallel_workers == 1 and self.single_worker_opt:
            if self.verbose:
                print("Initial_Load Optimized for single worker!")
            self.workers[0].initial_load(X, ids)
            time.sleep(2)
            self.workers[0].waitPendingOperations()
            return
        
        self.partition_initial_load(X, ids)
        for i in range(self.parallel_workers):
            self.waitPendingOperations()

    def insert(self, X, ids):
        """Insert vectors with load balancing across workers"""
        if not self.fine_grained_parallel_insert:
            self.insertInline(X, ids)
        else:
            rows = X.shape[0]
            for i in range(rows):
                rowI = X[i:i+1]
                idI = ids[i:i+1]
                self.insertInline(rowI, idI)

    def delete(self, ids):
        """Delete vectors by IDs"""
        if self.parallel_workers == 1 and self.single_worker_opt:
            if self.verbose:
                print("Delete Optimized for single worker!")
            self.workers[0].delete(ids)
        else:
            # Distribute deletes based on worker mapping
            mapping = {i: [] for i in range(self.parallel_workers)}
            for idx in ids:
                if idx < len(self.workerMap):
                    worker_id = self.workerMap[idx]
                    mapping[worker_id].append(idx)
            
            for i in range(self.parallel_workers):
                if mapping[i]:
                    self.workers[i].delete(mapping[i])

    def query(self, X, k):
        """Execute query (single worker optimization)"""
        if self.parallel_workers == 1 and self.single_worker_opt:
            self.workers[0].query(X, k)
            self.res = self.workers[0].res
            return
        
        # Multi-worker query not implemented in basic version
        self.workers[0].query(X, k)
        self.res = self.workers[0].res

    def partition_initial_load(self, X, ids):
        """Partition initial load across multiple workers"""
        rows = X.shape[0]
        step = rows // self.parallel_workers
        
        startPos = [0] * self.parallel_workers
        endPos = [0] * self.parallel_workers
        
        startPos[0] = 0
        endPos[self.parallel_workers - 1] = rows
        
        for i in range(1, self.parallel_workers):
            startPos[i] = i * step
            endPos[i - 1] = i * step
        
        for i in range(self.parallel_workers):
            sub = X[startPos[i]:endPos[i]]
            sub_id = ids[startPos[i]:endPos[i]]
            self.workerMap.extend([i] * (endPos[i] - startPos[i]))
            self.workers[i].initial_load(sub, sub_id)

    def insertInline(self, X, ids):
        """Insert data to next worker in round-robin fashion"""
        self.workers[self.insert_idx].insert(X, ids)
        
        if not self.single_worker_opt or self.parallel_workers > 1:
            for idx in ids:
                if idx >= len(self.workerMap):
                    self.workerMap.extend([-1] * (idx - len(self.workerMap) + 1))
                self.workerMap[idx] = self.insert_idx
        
        self.insert_idx += 1
        if self.insert_idx >= self.parallel_workers:
            self.insert_idx = 0

    def set_query_arguments(self, query_args):
        """Set query parameters for all workers"""
        for worker in self.workers:
            worker.my_index_algo.set_query_arguments(query_args)

    def index_name(self, name):
        """Get index filename"""
        return self.workers[0].my_index_algo.index_name(name)

    def reset_index(self):
        """Reset index to initial state"""
        if self._last_setup_params is None:
            raise RuntimeError("Cannot reset index before setup.")
        
        dtype, max_pts, ndims = self._last_setup_params
        for worker in self.workers:
            worker.reset_state(dtype, max_pts, ndims)
        
        for i, worker in enumerate(self.workers):
            worker.my_id = i
        
        self.insert_idx = 0
        self.workerMap = []
        self._drop_snapshot = 0
        self._hpc_active = False

    def enableScenario(self, randomContamination=False, randomContaminationProb=0.0,
                      randomDrop=False, randomDropProb=0.0, outOfOrder=False):
        """Enable special test scenarios on all workers"""
        for i in range(self.parallel_workers):
            self.workers[i].enableScenario(
                randomContamination, randomContaminationProb,
                randomDrop, randomDropProb, outOfOrder
            )

    def setBackpressureLogic(self, use_backpressure=False):
        """Configure backpressure logic for all workers"""
        for i in range(self.parallel_workers):
            self.workers[i].setBackpressureLogic(use_backpressure)

    def get_drop_count_delta(self):
        """Get total dropped operations since last call"""
        total = 0
        for worker in self.workers:
            total += worker.drop_count_total
        delta = total - self._drop_snapshot
        self._drop_snapshot = total
        return delta

    def get_pending_queue_len(self):
        """Get total pending queue length across all workers"""
        pending = 0
        for worker in self.workers:
            pending += worker.insert_queue.size()
            pending += worker.delete_queue.size()
        return pending
