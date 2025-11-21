"""
Worker classes for handling concurrent insert/delete/query operations in congestion scenarios
"""
from threading import Thread, Lock
from typing import Optional, List
import numpy as np
import random

# Import bind_to_core from our own utils
from ..utils.system_utils import bind_to_core

# Fallback queue implementations when PyCANDYAlgo is not available
try:
    from PyCANDYAlgo.utils import NumpyIdxPair, NumpyIdxQueue, IdxQueue
except (ModuleNotFoundError, ImportError):
    import collections

    class NumpyIdxPair:
        """Pair of numpy array and index list"""
        def __init__(self, vectors, idx):
            self.vectors = vectors
            self.idx = idx

    class _BaseQueue:
        """Base queue implementation using deque"""
        def __init__(self, cap: int = 10):
            self._dq = collections.deque()
            self._cap = int(cap)

        def capacity(self) -> int:
            return self._cap

        def size(self) -> int:
            return len(self._dq)

        def empty(self) -> bool:
            return not self._dq

        def front(self):
            return self._dq[0]

        def pop(self):
            self._dq.popleft()

        def push(self, item):
            self._dq.append(item)

    class NumpyIdxQueue(_BaseQueue):
        """Queue for NumpyIdxPair objects"""
        pass

    class IdxQueue(_BaseQueue):
        """Queue for simple index values"""
        pass

    def bind_to_core(core_id: int):
        """Bind current thread to CPU core (fallback no-op)"""
        import os
        if core_id == -1:
            return -1
        max_cpus = os.cpu_count()
        if max_cpus is None:
            return -1
        cpu_id = core_id % max_cpus
        try:
            pid = os.getpid()
            os.sched_setaffinity(pid, {cpu_id})
            return cpu_id
        except (AttributeError, Exception):
            return -1


class AbstractThread:
    """Base abstraction for a worker thread"""
    def __init__(self):
        self.thread: Optional[Thread] = None

    def inline_main(self):
        """Main thread logic to be implemented by subclasses"""
        pass

    def start_thread(self):
        """Start the worker thread"""
        self.thread = Thread(target=self.inline_main)
        self.thread.start()

    def join_thread(self):
        """Wait for the thread to complete"""
        if self.thread:
            self.thread.join()


class CongestionWorker(AbstractThread):
    """
    Worker that processes insert, delete, and query operations in parallel.
    Handles congestion through queue management and optional drop logic.
    """
    
    def __init__(self, index_algo, queue_capacity=10):
        super().__init__()
        
        # Operation queues
        self.insert_queue = NumpyIdxQueue(queue_capacity)
        self.initial_load_queue = NumpyIdxQueue(queue_capacity)
        self.delete_queue = NumpyIdxQueue(queue_capacity)
        self.query_queue = NumpyIdxQueue(queue_capacity)
        self.cmd_queue = IdxQueue(queue_capacity)
        
        # Worker configuration
        self.my_id = 0
        self.vec_dim = 0
        self.congestion_drop = True
        self.single_worker_opt = True
        self.use_backpressure_logic = False
        
        # State tracking
        self.ingested_vectors = 0
        self.drop_count_total = 0
        
        # Thread synchronization
        self.m_mut = Lock()
        
        # Reference to the underlying index algorithm
        self.my_index_algo = index_algo
        
        # Queue capacities for reset
        self.insert_queue_capacity = self.insert_queue.capacity()
        self.initial_load_queue_capacity = self.initial_load_queue.capacity()
        self.delete_queue_capacity = self.delete_queue.capacity()
        self.query_queue_capacity = self.query_queue.capacity()
        self.cmd_queue_capacity = self.cmd_queue.capacity()
        
        # Special scenario flags
        self.randomContamination = False
        self.randomDrop = False
        self.randomDropProb = 0.0
        self.randomContaminationProb = 0.0
        self.outOfOrder = False

    def setup(self, dtype, max_pts, ndim):
        """Initialize the worker and underlying algorithm"""
        self.vec_dim = ndim
        self.my_index_algo.setup(dtype, max_pts, ndim)

    def inline_main(self):
        """Main thread loop processing queued operations"""
        print(f"Worker {self.my_id}: Starting main thread logic.")
        should_loop = True
        bind_to_core(self.my_id)
        
        while should_loop:
            # 1. Process initial load stage
            while not self.m_mut.acquire(blocking=False):
                pass
            
            initial_vectors = []
            initial_ids = []
            while not self.initial_load_queue.empty():
                pair = self.initial_load_queue.front()
                self.initial_load_queue.pop()
                initial_vectors.append(pair.vectors)
                initial_ids.append(pair.idx)
            
            if len(initial_vectors) > 0:
                initial_vectors = np.vstack(initial_vectors)
                initial_ids = np.concatenate(initial_ids)
                self.my_index_algo.insert(initial_vectors, initial_ids)
            
            self.m_mut.release()
            
            # 2. Process insert operations
            while not self.m_mut.acquire(blocking=False):
                pass
            
            while not self.insert_queue.empty():
                pair = self.insert_queue.front()
                self.insert_queue.pop()
                self.my_index_algo.insert(pair.vectors, np.array(pair.idx))
                self.ingested_vectors += pair.vectors.shape[0]
            
            # 3. Process delete operations
            while not self.delete_queue.empty():
                idx = self.delete_queue.front().idx
                self.delete_queue.pop()
                self.my_index_algo.delete(np.array(idx))
            
            self.m_mut.release()
            
            # 4. Check for termination command
            while not self.cmd_queue.empty():
                cmd = self.cmd_queue.front()
                self.cmd_queue.pop()
                if cmd == -1:
                    should_loop = False
                    print(f"Worker {self.my_id} terminates")
                    return

    def startHPC(self):
        """Start the worker thread"""
        self.start_thread()
        return True

    def endHPC(self):
        """Signal the worker to terminate"""
        self.cmd_queue.push(-1)
        return False

    def set_id(self, worker_id):
        """Set the worker ID"""
        self.my_id = worker_id

    def waitPendingOperations(self):
        """Wait for the worker to finish current operations"""
        while not self.m_mut.acquire(blocking=False):
            pass
        self.m_mut.release()
        return True

    def reset_state(self, dtype, max_pts, ndim):
        """Reset worker state to initial configuration"""
        self.insert_queue = NumpyIdxQueue(self.insert_queue_capacity)
        self.initial_load_queue = NumpyIdxQueue(self.initial_load_queue_capacity)
        self.delete_queue = NumpyIdxQueue(self.delete_queue_capacity)
        self.query_queue = NumpyIdxQueue(self.query_queue_capacity)
        self.cmd_queue = IdxQueue(self.cmd_queue_capacity)
        self.ingested_vectors = 0
        self.drop_count_total = 0
        self.vec_dim = ndim
        self.my_index_algo.setup(dtype, max_pts, ndim)

    def initial_load(self, X, ids):
        """Load initial dataset directly (optimized for single worker)"""
        if self.single_worker_opt:
            while not self.m_mut.acquire(blocking=False):
                pass
            self.my_index_algo.insert(X, ids)
            self.m_mut.release()

    def insert(self, X, ids):
        """
        Insert vectors with congestion handling.
        May drop inserts based on queue status and configuration.
        """
        def _record_drop(dropped_ids):
            try:
                dropped = len(dropped_ids)
            except TypeError:
                dropped = 1
            self.drop_count_total += dropped

        if self.use_backpressure_logic:
            queue_full = self.insert_queue.size() >= self.insert_queue_capacity
            
            if not self.randomDrop:
                if self.congestion_drop and queue_full:
                    _record_drop(ids)
                    print(f"DROPPING DATA {ids[0]}:{ids[-1]} (queue full)")
                    return
                self.insert_queue.push(NumpyIdxPair(X, ids))
                return
            
            # Random drop scenario
            rand_drop = random.random()
            if rand_drop < self.randomDropProb:
                _record_drop(ids)
                print(f"RANDOM DROPPING DATA {ids[0]}:{ids[-1]}")
                return
            if self.congestion_drop and queue_full:
                _record_drop(ids)
                print(f"DROPPING DATA {ids[0]}:{ids[-1]} (queue full)")
                return
            self.insert_queue.push(NumpyIdxPair(X, ids))
        else:
            # Normal logic: drop only when queue is not empty
            if not self.randomDrop:
                if self.insert_queue.empty() or (not self.congestion_drop):
                    self.insert_queue.push(NumpyIdxPair(X, ids))
                else:
                    _record_drop(ids)
                    print(f"DROPPING DATA {ids[0]}:{ids[-1]}")
            else:
                rand_drop = random.random()
                if rand_drop < self.randomDropProb:
                    _record_drop(ids)
                    print(f"RANDOM DROPPING DATA {ids[0]}:{ids[-1]}")
                    return
                if self.insert_queue.empty() or (not self.congestion_drop):
                    self.insert_queue.push(NumpyIdxPair(X, ids))
                else:
                    _record_drop(ids)
                    print(f"DROPPING DATA {ids[0]}:{ids[-1]}")

    def delete(self, ids):
        """Delete vectors with congestion handling"""
        if self.use_backpressure_logic:
            queue_full = self.delete_queue.size() >= self.delete_queue_capacity
            if self.congestion_drop and queue_full:
                print("Failed to process deletion! (queue full)")
                return
            self.delete_queue.push(NumpyIdxPair(np.array([0.0]), ids))
        else:
            if self.delete_queue.empty() or (not self.congestion_drop):
                self.delete_queue.push(NumpyIdxPair(np.array([0.0]), ids))
            else:
                print("Failed to process deletion!")

    def query(self, X, k):
        """Execute query on the underlying index"""
        self.my_index_algo.query(X, k)
        self.res = self.my_index_algo.res

    def enableScenario(self, randomContamination=False, randomContaminationProb=0.0,
                      randomDrop=False, randomDropProb=0.0, outOfOrder=False):
        """Enable special test scenarios"""
        self.randomDrop = randomDrop
        self.randomDropProb = randomDropProb
        if randomDrop:
            print(f"Enabling random dropping with prob {randomDropProb}!")
        
        self.randomContamination = randomContamination
        self.randomContaminationProb = randomContaminationProb
        if randomContamination:
            print(f"Enabling random contamination with prob {randomContaminationProb}!")
        
        self.outOfOrder = outOfOrder
        if outOfOrder:
            print("Enabling out-of-order ingestion!")

    def setBackpressureLogic(self, use_backpressure=True):
        """Configure backpressure logic"""
        self.use_backpressure_logic = use_backpressure
        if use_backpressure:
            print(f"Worker {self.my_id}: Using backpressure logic (queue capacity-based)")
        else:
            print(f"Worker {self.my_id}: Using normal logic (empty queue only)")
