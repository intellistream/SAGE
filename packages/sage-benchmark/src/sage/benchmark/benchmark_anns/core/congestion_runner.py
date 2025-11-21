"""
Runner for congestion benchmark tests
"""
import time
import numpy as np
from typing import Dict, Any
import tracemalloc

from ..utils import generate_timestamps, calculate_statistics


class CongestionRunner:
    """
    Runner for executing congestion benchmark tests.
    Processes runbook operations and collects performance metrics.
    """
    
    @staticmethod
    def setup_algorithm(algo, dataset, max_pts):
        """
        Setup the algorithm with dataset parameters.
        
        Args:
            algo: Algorithm instance
            dataset: Dataset instance
            max_pts: Maximum number of points
        
        Returns:
            Setup time in seconds
        """
        t0 = time.time()
        ndims = dataset.d
        dtype = dataset.dtype
        algo.setup(dtype, max_pts, ndims)
        setup_time = time.time() - t0
        print(f'Algorithm setup completed in {setup_time:.2f}s')
        return setup_time
    
    @staticmethod
    def run_test(algo, dataset, runbook, query_args=None, k=10):
        """
        Run congestion test based on runbook.
        
        Args:
            algo: Algorithm instance (must implement BaseCongestionANN)
            dataset: Dataset instance
            runbook: Runbook defining test operations
            query_args: Query parameters (e.g., {'ef': 64})
            k: Number of nearest neighbors for queries
        
        Returns:
            Dictionary with test results and metrics
        """
        # Set query arguments
        if query_args:
            algo.set_query_arguments(query_args)
        
        # Get queries
        Q = dataset.get_queries()
        print(f"Loaded {Q.shape[0]} queries")
        
        # Initialize metrics
        attrs = {
            "name": getattr(algo, 'name', str(type(algo).__name__)),
            "setup_time": 0,
            "total_time": 0,
            "insert_latencies": [],
            "query_latencies": [],
            "delete_latencies": [],
            "continuous_query_latencies": [],
            "continuous_query_results": [],
            "batch_throughputs": [],
            "insert_throughputs": [],
            "pending_queue_lengths": [],
            "drop_counts": [],
        }
        
        counts = {
            'initial': 0,
            'batch_insert': 0,
            'insert': 0,
            'delete': 0,
            'search': 0,
        }
        
        # Execute runbook
        total_start = time.time()
        
        for step_idx, entry in enumerate(runbook):
            operation = entry['operation']
            print(f"\nStep {step_idx}: {operation}")
            
            step_start = time.time()
            
            try:
                if operation == 'initial':
                    CongestionRunner._execute_initial(algo, dataset, entry, attrs, counts)
                
                elif operation == 'startHPC':
                    CongestionRunner._execute_start_hpc(algo, attrs)
                
                elif operation == 'batch_insert':
                    CongestionRunner._execute_batch_insert(
                        algo, dataset, entry, Q, k, attrs, counts
                    )
                
                elif operation == 'insert':
                    CongestionRunner._execute_insert(algo, dataset, entry, attrs, counts)
                
                elif operation == 'delete':
                    CongestionRunner._execute_delete(algo, entry, attrs, counts)
                
                elif operation == 'search':
                    CongestionRunner._execute_search(algo, Q, k, attrs, counts)
                
                elif operation == 'waitPending':
                    CongestionRunner._execute_wait_pending(algo, attrs)
                
                elif operation == 'endHPC':
                    CongestionRunner._execute_end_hpc(algo, attrs)
                
                elif operation == 'enableScenario':
                    CongestionRunner._execute_enable_scenario(algo, entry)
                
                else:
                    print(f"Warning: Unknown operation '{operation}'")
            
            except Exception as e:
                print(f"Error in step {step_idx} ({operation}): {e}")
                import traceback
                traceback.print_exc()
                raise
            
            step_time = time.time() - step_start
            print(f"Step {step_idx} completed in {step_time:.2f}s")
        
        attrs['total_time'] = time.time() - total_start
        attrs['operation_counts'] = counts
        
        # Calculate summary statistics
        attrs['insert_stats'] = calculate_statistics(attrs['insert_latencies'])
        attrs['query_stats'] = calculate_statistics(attrs['query_latencies'])
        attrs['delete_stats'] = calculate_statistics(attrs['delete_latencies'])
        
        print(f"\nTest completed in {attrs['total_time']:.2f}s")
        print(f"Operations: {counts}")
        
        return attrs
    
    @staticmethod
    def _execute_initial(algo, dataset, entry, attrs, counts):
        """Execute initial load operation"""
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        ids = np.arange(start, end, dtype=np.uint32)
        data = dataset.get_dataset()[start:end]
        
        print(f"Initial load: {start} to {end} ({len(ids)} vectors)")
        t0 = time.time()
        algo.initial_load(data, ids)
        load_time = (time.time() - t0) * 1e6
        
        attrs['insert_latencies'].append(load_time)
        counts['initial'] += 1
        print(f"Initial load completed in {load_time/1e6:.2f}s")
    
    @staticmethod
    def _execute_start_hpc(algo, attrs):
        """Start HPC workers"""
        print("Starting HPC workers...")
        algo.startHPC()
        time.sleep(0.5)  # Give workers time to start
    
    @staticmethod
    def _execute_end_hpc(algo, attrs):
        """Stop HPC workers"""
        print("Stopping HPC workers...")
        algo.endHPC()
    
    @staticmethod
    def _execute_batch_insert(algo, dataset, entry, queries, k, attrs, counts):
        """Execute batch insert with timing"""
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        batch_size = entry.get('batchSize', 1000)
        event_rate = entry.get('eventRate', 1000)
        
        print(f"Batch insert: {start} to {end}, batch_size={batch_size}, "
              f"event_rate={event_rate}")
        
        data = dataset.get_dataset()
        ids = np.arange(start, end, dtype=np.uint32)
        event_timestamps = generate_timestamps(end - start, event_rate)
        
        batch_count = (end - start + batch_size - 1) // batch_size
        print(f"Total batches to insert: {batch_count}")
        insert_latency_total = 0
        throughputs = []
        
        test_start = time.time()
        continuous_counter = 0
        query_interval = max((end - start) // 100, batch_size)  # Query every 1%
        print(f"Query interval set to {query_interval}")
        for i in range(batch_count):
            print(f"Inserting batch {i+1}/{batch_count}")
            batch_start_idx = start + i * batch_size
            batch_end_idx = min(start + (i + 1) * batch_size, end)
            batch_data = data[batch_start_idx:batch_end_idx]
            batch_ids = ids[i * batch_size : i * batch_size + (batch_end_idx - batch_start_idx)]
            
            # Wait for event time
            t_now = (time.time() - test_start) * 1e6
            t_expected = event_timestamps[min((i + 1) * batch_size - 1, len(event_timestamps) - 1)]
            if t_now < t_expected:
                time.sleep((t_expected - t_now) / 1e6)
            
            # Insert batch
            t0 = time.time()
            algo.insert(batch_data, batch_ids)
            insert_time = time.time() - t0
            insert_latency_total += insert_time * 1e6
            throughputs.append(len(batch_ids) / insert_time)
            
            # Periodic query
            continuous_counter += len(batch_ids)
            if continuous_counter >= query_interval:
                t1 = time.time()
                algo.query(queries, k)
                query_latency = (time.time() - t1) * 1e6
                attrs['continuous_query_latencies'].append(query_latency)
                attrs['continuous_query_results'].append(algo.get_results())
                continuous_counter = 0
            
            # Track queue status
            if hasattr(algo, 'get_pending_queue_len'):
                attrs['pending_queue_lengths'].append(algo.get_pending_queue_len())
            if hasattr(algo, 'get_drop_count_delta'):
                attrs['drop_counts'].append(algo.get_drop_count_delta())
        
        attrs['insert_latencies'].append(insert_latency_total)
        attrs['insert_throughputs'].extend(throughputs)
        counts['batch_insert'] += 1
        
        print(f"Batch insert completed: {len(throughputs)} batches, "
              f"avg throughput: {np.mean(throughputs):.2f} ops/s")
    
    @staticmethod
    def _execute_insert(algo, dataset, entry, attrs, counts):
        """Execute single insert operation"""
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        ids = np.arange(start, end, dtype=np.uint32)
        data = dataset.get_dataset()[start:end]
        
        t0 = time.time()
        algo.insert(data, ids)
        insert_time = (time.time() - t0) * 1e6
        
        attrs['insert_latencies'].append(insert_time)
        counts['insert'] += 1
    
    @staticmethod
    def _execute_delete(algo, entry, attrs, counts):
        """Execute delete operation"""
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        ids = np.arange(start, end, dtype=np.uint32)
        
        print(f"Delete: {start} to {end}")
        t0 = time.time()
        algo.delete(ids)
        delete_time = (time.time() - t0) * 1e6
        
        attrs['delete_latencies'].append(delete_time)
        counts['delete'] += 1
    
    @staticmethod
    def _execute_search(algo, queries, k, attrs, counts):
        """Execute search operation"""
        t0 = time.time()
        algo.query(queries, k)
        query_time = (time.time() - t0) * 1e6
        
        results = algo.get_results()
        attrs['query_latencies'].append(query_time)
        counts['search'] += 1
    
    @staticmethod
    def _execute_wait_pending(algo, attrs):
        """Wait for pending operations"""
        print("Waiting for pending operations...")
        t0 = time.time()
        algo.waitPendingOperations()
        wait_time = (time.time() - t0) * 1e6
        attrs.setdefault('pending_wait_time', 0)
        attrs['pending_wait_time'] += wait_time
        print(f"Waited {wait_time/1e6:.2f}s for pending operations")
    
    @staticmethod
    def _execute_enable_scenario(algo, entry):
        """Enable special test scenarios"""
        random_contamination = bool(entry.get('randomContamination', 0))
        random_contamination_prob = float(entry.get('randomContaminationProb', 0.0))
        random_drop = bool(entry.get('randomDrop', 0))
        random_drop_prob = float(entry.get('randomDropProb', 0.0))
        out_of_order = bool(entry.get('outOfOrder', 0))
        
        print(f"Enable scenario: contamination={random_contamination}, "
              f"drop={random_drop}, out_of_order={out_of_order}")
        
        algo.enableScenario(
            randomContamination=random_contamination,
            randomContaminationProb=random_contamination_prob,
            randomDrop=random_drop,
            randomDropProb=random_drop_prob,
            outOfOrder=out_of_order
        )
