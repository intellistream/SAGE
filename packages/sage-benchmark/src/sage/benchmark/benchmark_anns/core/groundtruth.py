"""
Groundtruth computation for congestion testing scenarios

This module computes the exact k-nearest neighbors at each step of a runbook,
tracking inserts and deletes to maintain the correct active dataset.
"""
import os
import numpy as np
from typing import Dict, List, Tuple, Optional
import time


def compute_euclidean_distances(queries: np.ndarray, data: np.ndarray) -> np.ndarray:
    """
    Compute L2 distances between queries and data points.
    
    Args:
        queries: Query vectors (nq, dim)
        data: Data vectors (n, dim)
    
    Returns:
        Distance matrix (nq, n)
    """
    # Using efficient numpy operations
    # ||q - d||^2 = ||q||^2 + ||d||^2 - 2*q*d
    queries_sq = np.sum(queries ** 2, axis=1, keepdims=True)  # (nq, 1)
    data_sq = np.sum(data ** 2, axis=1, keepdims=True)  # (n, 1)
    cross = np.dot(queries, data.T)  # (nq, n)
    
    distances = queries_sq + data_sq.T - 2 * cross
    # Handle numerical errors that might make distances slightly negative
    distances = np.maximum(distances, 0)
    return np.sqrt(distances)


def compute_inner_product_distances(queries: np.ndarray, data: np.ndarray) -> np.ndarray:
    """
    Compute negative inner product (for MIPS).
    
    Args:
        queries: Query vectors (nq, dim)
        data: Data vectors (n, dim)
    
    Returns:
        Distance matrix (nq, n) - negative inner products
    """
    # For MIPS, we want to maximize inner product, so we use negative values
    return -np.dot(queries, data.T)


def compute_groundtruth(queries: np.ndarray, 
                       data: np.ndarray, 
                       k: int,
                       metric: str = 'euclidean') -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute exact k-nearest neighbors.
    
    Args:
        queries: Query vectors (nq, dim)
        data: Data vectors (n, dim)
        k: Number of neighbors to find
        metric: Distance metric ('euclidean' or 'ip')
    
    Returns:
        Tuple of (indices, distances) both of shape (nq, k)
    """
    if metric == 'euclidean' or metric == 'l2':
        distances = compute_euclidean_distances(queries, data)
    elif metric == 'ip' or metric == 'angular':
        distances = compute_inner_product_distances(queries, data)
    else:
        raise ValueError(f"Unknown metric: {metric}")
    
    # Get k nearest neighbors
    k = min(k, data.shape[0])  # Can't get more neighbors than points
    indices = np.argsort(distances, axis=1)[:, :k]
    
    # Get corresponding distances
    batch_indices = np.arange(queries.shape[0])[:, np.newaxis]
    sorted_distances = distances[batch_indices, indices]
    
    return indices, sorted_distances


class GroundtruthTracker:
    """
    Track groundtruth through a runbook execution.
    
    Maintains the active dataset as operations are performed,
    and computes groundtruth at each search step.
    
    This implementation follows the original compute_gt.py logic to ensure
    correct tag-to-data-index mapping, especially for replace operations.
    """
    
    def __init__(self, dataset, metric: str = 'euclidean'):
        """
        Initialize the tracker.
        
        Args:
            dataset: Dataset object with get_dataset() method
            metric: Distance metric to use
        """
        self.full_data = dataset.get_dataset()
        self.metric = metric
        # Key difference from old implementation:
        # tag_to_id maps tag (key in index) -> data_index (position in full_data)
        # This allows replace operations to change which data a tag points to
        self.tag_to_id = {}  # tag -> data_index mapping
        self.groundtruths = {}  # step -> (indices, distances, tags)
        
    def process_initial(self, entry: dict):
        """
        Process initial load operation.
        
        Following compute_gt.py logic: tag_to_id[tag] = data_index
        For initial load, tag equals data_index.
        """
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        for i in range(start, end):
            self.tag_to_id[i] = i
    
    def process_insert(self, entry: dict):
        """
        Process insert operation.
        
        For insert, tag equals data_index.
        """
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        for i in range(start, end):
            self.tag_to_id[i] = i
    
    def process_batch_insert(self, entry: dict, queries: np.ndarray = None, 
                            k: int = 10, step: int = 0,
                            output_dir: str = None, dataset_name: str = None,
                            runbook_params: dict = None, verbose: bool = False):
        """
        Process batch_insert operation with continuous query groundtruth computation.
        
        This follows the original compute_gt.py logic for batch processing and
        continuous query computation frequency.
        
        Args:
            entry: Runbook entry for batch_insert
            queries: Query vectors for continuous queries
            k: Number of neighbors
            step: Step number for naming
            output_dir: Output directory for saving groundtruths
            dataset_name: Dataset name for organizing files
            runbook_params: Runbook parameters for directory naming
            verbose: Print progress
        
        Returns:
            List of groundtruth results for continuous queries
        """
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        batch_size = entry.get('batchSize', 1000)
        
        continuous_gts = []
        
        # Calculate total inserts and batch count
        total_inserts = end - start
        batch_count = (total_inserts + batch_size - 1) // batch_size
        
        # Compute groundtruth every 1% of total inserts
        # This matches the original compute_gt.py logic
        query_interval = max(total_inserts // 100, 1)
        continuous_counter = 0
        continuous_query_count = 0
        
        for i in range(batch_count):
            batch_start_idx = start + i * batch_size
            batch_end_idx = min(start + (i + 1) * batch_size, end)
            
            # Insert this batch - tag equals data_index
            for idx in range(batch_start_idx, batch_end_idx):
                self.tag_to_id[idx] = idx
            
            # Update counter
            batch_inserts = batch_end_idx - batch_start_idx
            continuous_counter += batch_inserts
            
            # Check if we should compute continuous query GT
            # Original logic: every 1% of total inserts
            if continuous_counter >= query_interval and queries is not None:
                # Compute groundtruth at this point
                gt_key = f"{step}_continuous_{continuous_query_count}"
                
                tags, data = self.get_active_data()
                
                if len(data) > 0:
                    start_time = time.time()
                    indices, distances = compute_groundtruth(queries, data, k, self.metric)
                    result_tags = tags[indices]
                    elapsed = time.time() - start_time
                    
                    gt_result = {
                        'step': step,
                        'continuous_query_id': continuous_query_count,
                        'batch_number': i,
                        'tags': result_tags,
                        'indices': indices,
                        'distances': distances,
                        'num_active_points': len(data)
                    }
                    
                    continuous_gts.append(gt_result)
                    self.groundtruths[gt_key] = gt_result
                    
                    if verbose:
                        print(f"  Continuous query {continuous_query_count} (batch {i}): "
                              f"{len(queries)} queries, {len(data)} active points, "
                              f"k={k} in {elapsed:.2f}s")
                    
                    # Save to disk if output_dir specified
                    if output_dir:
                        self._save_continuous_groundtruth(
                            step=step,
                            continuous_id=continuous_query_count,
                            gt_result=gt_result,
                            output_dir=output_dir,
                            dataset_name=dataset_name,
                            runbook_params=runbook_params
                        )
                
                continuous_counter = 0
                continuous_query_count += 1
        
        return continuous_gts
    
    def _save_continuous_groundtruth(self, step: int, continuous_id: int, 
                                    gt_result: dict, output_dir: str,
                                    dataset_name: str = None, 
                                    runbook_params: dict = None):
        """Save continuous query groundtruth"""
        # Create organized directory structure
        if dataset_name and runbook_params:
            initial_size = runbook_params.get('initial_size', 0)
            batch_size = runbook_params.get('batch_size', 0)
            event_rate = runbook_params.get('event_rate', 0)
            
            runbook_dir = f"initial{initial_size}_batch{batch_size}_rate{event_rate}"
            final_dir = os.path.join(output_dir, dataset_name, runbook_dir)
        else:
            final_dir = output_dir
        
        os.makedirs(final_dir, exist_ok=True)
        
        # Use naming: step{N}_continuous_{M}
        base_path = os.path.join(final_dir, f"step{step}_continuous_{continuous_id}")
        
        # Save data
        np.save(f"{base_path}_tags.npy", gt_result['tags'])
        np.save(f"{base_path}_distances.npy", gt_result['distances'])
        
        # Save metadata
        metadata = {
            'step': step,
            'continuous_query_id': continuous_id,
            'batch_number': gt_result['batch_number'],
            'num_queries': gt_result['tags'].shape[0],
            'k': gt_result['tags'].shape[1],
            'num_active_points': gt_result['num_active_points'],
            'metric': self.metric,
            'dataset_name': dataset_name,
            'runbook_params': runbook_params
        }
        
        import json
        with open(f"{base_path}_meta.json", 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def process_delete(self, entry: dict):
        """
        Process delete operation.
        
        Following compute_gt.py: delete is by tag (key).
        """
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        for i in range(start, end):
            self.tag_to_id.pop(i, None)
    
    def process_batch_insert_delete(self, entry: dict, queries: np.ndarray = None,
                                   k: int = 10, step: int = 0,
                                   output_dir: str = None, dataset_name: str = None,
                                   runbook_params: dict = None, verbose: bool = False):
        """
        Process batch_insert_delete operation with continuous query groundtruth.
        
        This operation inserts batches and then deletes a percentage from each batch.
        Following compute_gt.py logic for proper deletion handling.
        
        Args:
            entry: Runbook entry for batch_insert_delete
            queries: Query vectors for continuous queries
            k: Number of neighbors
            step: Step number for naming
            output_dir: Output directory for saving groundtruths
            dataset_name: Dataset name for organizing files
            runbook_params: Runbook parameters for directory naming
            verbose: Print progress
        
        Returns:
            List of groundtruth results for continuous queries
        """
        start = entry.get('start', 0)
        end = entry.get('end', 0)
        batch_size = entry.get('batchSize', 1000)
        deletion_percentage = entry.get('deletion_percentage', 0.0)
        
        continuous_gts = []
        
        # Calculate total inserts and batch count
        total_inserts = end - start
        batch_count = (total_inserts + batch_size - 1) // batch_size
        
        # Compute groundtruth every 1% of total inserts
        query_interval = max(total_inserts // 100, 1)
        continuous_counter = 0
        continuous_query_count = 0
        
        for i in range(batch_count):
            batch_start_idx = start + i * batch_size
            batch_end_idx = min(start + (i + 1) * batch_size, end)
            
            # Insert this batch
            for idx in range(batch_start_idx, batch_end_idx):
                self.tag_to_id[idx] = idx
            
            # Delete percentage from this batch (from the end of the batch)
            # Following compute_gt.py: delete from (batch_end - percentage*batch_size) to batch_end
            delete_count = int((batch_end_idx - batch_start_idx) * deletion_percentage)
            delete_start = batch_end_idx - delete_count
            for idx in range(delete_start, batch_end_idx):
                self.tag_to_id.pop(idx, None)
            
            # Update counter (count insertions before deletions)
            batch_inserts = batch_end_idx - batch_start_idx
            continuous_counter += batch_inserts
            
            # Check if we should compute continuous query GT
            if continuous_counter >= query_interval and queries is not None:
                # Compute groundtruth at this point
                gt_key = f"{step}_continuous_{continuous_query_count}"
                
                tags, data = self.get_active_data()
                
                if len(data) > 0:
                    start_time = time.time()
                    indices, distances = compute_groundtruth(queries, data, k, self.metric)
                    result_tags = tags[indices]
                    elapsed = time.time() - start_time
                    
                    gt_result = {
                        'step': step,
                        'continuous_query_id': continuous_query_count,
                        'batch_number': i,
                        'tags': result_tags,
                        'indices': indices,
                        'distances': distances,
                        'num_active_points': len(data),
                        'deletion_percentage': deletion_percentage
                    }
                    
                    continuous_gts.append(gt_result)
                    self.groundtruths[gt_key] = gt_result
                    
                    if verbose:
                        print(f"  Continuous query {continuous_query_count} (batch {i}, "
                              f"del {deletion_percentage*100:.0f}%): "
                              f"{len(queries)} queries, {len(data)} active points, "
                              f"k={k} in {elapsed:.2f}s")
                    
                    # Save to disk if output_dir specified
                    if output_dir:
                        self._save_continuous_groundtruth(
                            step=step,
                            continuous_id=continuous_query_count,
                            gt_result=gt_result,
                            output_dir=output_dir,
                            dataset_name=dataset_name,
                            runbook_params=runbook_params
                        )
                
                continuous_counter = 0
                continuous_query_count += 1
        
        return continuous_gts
    
    def process_replace(self, entry: dict):
        """
        Process replace operation.
        
        This is the KEY difference from the old implementation:
        Replace updates the mapping so that tags point to different data indices.
        Following compute_gt.py: tag_to_id[tag] = new_data_index
        
        For example, if we replace tags 0-999 with data from indices 10000-10999,
        then tag 0 now points to data[10000], tag 1 to data[10001], etc.
        """
        tags_start = entry.get('tags_start', 0)
        tags_end = entry.get('tags_end', 0)
        ids_start = entry.get('ids_start', 0)
        
        for i, tag in enumerate(range(tags_start, tags_end)):
            # Update mapping: this tag now points to a different data index
            self.tag_to_id[tag] = ids_start + i
    
    def get_active_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get currently active data points.
        
        Following compute_gt.py logic: extract data based on tag_to_id mapping.
        This correctly handles replace operations where tags may point to different data indices.
        
        Returns:
            Tuple of (tags, data) where:
            - tags: Array of tag IDs (keys in the index)
            - data: Corresponding data vectors from full_data
        """
        if not self.tag_to_id:
            return np.array([], dtype=np.uint32), np.zeros((0, self.full_data.shape[1]), dtype=self.full_data.dtype)
        
        # Extract tags and their corresponding data indices
        tags_list = []
        data_indices_list = []
        
        for tag, data_idx in self.tag_to_id.items():
            tags_list.append(tag)
            data_indices_list.append(data_idx)
        
        tags = np.array(tags_list, dtype=np.uint32)
        data_indices = np.array(data_indices_list, dtype=np.uint32)
        
        # Get the actual data vectors
        data = self.full_data[data_indices]
        
        return tags, data
    
    def compute_search_groundtruth(self, queries: np.ndarray, k: int, step: int) -> Dict:
        """
        Compute groundtruth for a search operation.
        
        Args:
            queries: Query vectors
            k: Number of neighbors
            step: Step number in runbook
        
        Returns:
            Dictionary with 'tags', 'indices', 'distances', and 'step'
        """
        tags, data = self.get_active_data()
        
        if len(data) == 0:
            print(f"Warning: No active data at step {step}")
            return {
                'step': step,
                'tags': np.array([], dtype=np.uint32),
                'indices': np.zeros((len(queries), 0), dtype=np.uint32),
                'distances': np.zeros((len(queries), 0), dtype=np.float32),
                'num_active_points': 0
            }
        
        # Compute exact k-NN
        indices, distances = compute_groundtruth(queries, data, k, self.metric)
        
        # Convert indices to tags
        result_tags = tags[indices]
        
        result = {
            'step': step,
            'tags': result_tags,  # (nq, k) array of tag IDs
            'indices': indices,   # (nq, k) indices into active data
            'distances': distances,  # (nq, k) distances
            'num_active_points': len(data)
        }
        
        self.groundtruths[step] = result
        return result
    
    def save_groundtruth(self, step: int, output_dir: str, prefix: str = "step",
                        dataset_name: str = None, runbook_params: dict = None):
        """
        Save groundtruth for a specific step to disk with organized directory structure.
        
        Args:
            step: Step number
            output_dir: Base output directory
            prefix: Filename prefix
            dataset_name: Name of the dataset (for directory organization)
            runbook_params: Dictionary with runbook parameters (initial_size, batch_size, event_rate)
        """
        if step not in self.groundtruths:
            print(f"Warning: No groundtruth computed for step {step}")
            return
        
        # Create organized directory structure
        if dataset_name and runbook_params:
            # Format: output_dir/dataset_name/initial{N}_batch{M}_rate{R}/
            initial_size = runbook_params.get('initial_size', 0)
            batch_size = runbook_params.get('batch_size', 0)
            event_rate = runbook_params.get('event_rate', 0)
            
            runbook_dir = f"initial{initial_size}_batch{batch_size}_rate{event_rate}"
            final_dir = os.path.join(output_dir, dataset_name, runbook_dir)
        else:
            final_dir = output_dir
        
        os.makedirs(final_dir, exist_ok=True)
        
        gt = self.groundtruths[step]
        base_path = os.path.join(final_dir, f"{prefix}{step}")
        
        # Save in numpy format (easy to load)
        np.save(f"{base_path}_tags.npy", gt['tags'])
        np.save(f"{base_path}_distances.npy", gt['distances'])
        
        # Also save metadata
        metadata = {
            'step': step,
            'num_queries': gt['tags'].shape[0],
            'k': gt['tags'].shape[1],
            'num_active_points': gt['num_active_points'],
            'metric': self.metric,
            'dataset_name': dataset_name,
            'runbook_params': runbook_params
        }
        
        import json
        with open(f"{base_path}_meta.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        if dataset_name and runbook_params:
            print(f"Saved groundtruth for step {step} to {final_dir}")
        else:
            print(f"Saved groundtruth for step {step} to {output_dir}")


def compute_runbook_groundtruth(dataset, runbook, queries, k: int = 10, 
                               metric: str = 'euclidean',
                               output_dir: Optional[str] = None,
                               dataset_name: str = None,
                               verbose: bool = True) -> Dict[int, Dict]:
    """
    Compute groundtruth for all search operations in a runbook.
    
    Args:
        dataset: Dataset object
        runbook: List of runbook entries (from Runbook.entries)
        queries: Query vectors
        k: Number of neighbors to compute
        metric: Distance metric
        output_dir: Optional directory to save results
        dataset_name: Name of dataset (for organizing output files)
        verbose: Print progress
    
    Returns:
        Dictionary mapping step number to groundtruth results
    """
    tracker = GroundtruthTracker(dataset, metric)
    
    # Extract runbook parameters for directory naming
    runbook_params = {
        'initial_size': 0,
        'batch_size': 0,
        'event_rate': 0
    }
    
    # Scan runbook to extract key parameters
    for entry in runbook:
        operation = entry.get('operation', '')
        if operation == 'initial':
            runbook_params['initial_size'] = entry.get('end', 0) - entry.get('start', 0)
        elif operation == 'batch_insert':
            if runbook_params['batch_size'] == 0:  # Get first batch_insert params
                runbook_params['batch_size'] = entry.get('batchSize', 0)
                runbook_params['event_rate'] = entry.get('eventRate', 0)
    
    step = 0
    for entry in runbook:
        operation = entry.get('operation', '')
        
        if verbose:
            print(f"Step {step}: {operation}")
        
        # Update active dataset based on operation
        if operation == 'initial':
            tracker.process_initial(entry)
        elif operation == 'insert':
            tracker.process_insert(entry)
        elif operation == 'batch_insert':
            # Process batch_insert with continuous queries
            continuous_gts = tracker.process_batch_insert(
                entry=entry,
                queries=queries,
                k=k,
                step=step,
                output_dir=output_dir,
                dataset_name=dataset_name,
                runbook_params=runbook_params,
                verbose=verbose
            )
            if verbose and continuous_gts:
                print(f"  Computed {len(continuous_gts)} continuous query GTs during batch_insert")
        elif operation == 'delete':
            tracker.process_delete(entry)
        elif operation == 'batch_insert_delete':
            # Process batch_insert_delete with continuous queries
            continuous_gts = tracker.process_batch_insert_delete(
                entry=entry,
                queries=queries,
                k=k,
                step=step,
                output_dir=output_dir,
                dataset_name=dataset_name,
                runbook_params=runbook_params,
                verbose=verbose
            )
            if verbose and continuous_gts:
                print(f"  Computed {len(continuous_gts)} continuous query GTs during batch_insert_delete")
        elif operation == 'replace':
            tracker.process_replace(entry)
        elif operation == 'search':
            # Compute groundtruth
            start_time = time.time()
            gt = tracker.compute_search_groundtruth(queries, k, step)
            elapsed = time.time() - start_time
            
            if verbose:
                print(f"  Computed GT for {len(queries)} queries, "
                      f"{gt['num_active_points']} active points, "
                      f"k={k} in {elapsed:.2f}s")
            
            # Optionally save to disk with organized directory structure
            if output_dir:
                tracker.save_groundtruth(
                    step=step, 
                    output_dir=output_dir,
                    dataset_name=dataset_name,
                    runbook_params=runbook_params
                )
        
        step += 1
    
    return tracker.groundtruths
