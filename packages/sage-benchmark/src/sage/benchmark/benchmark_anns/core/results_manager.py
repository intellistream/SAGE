"""
Results management for benchmark tests

This module provides organized storage and retrieval of benchmark results,
matching the groundtruth directory structure for easy comparison.
"""
import os
import json
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime


class ResultsManager:
    """
    Manage benchmark results with organized directory structure.
    
    Directory structure:
    results/
    └── {dataset_name}/
        └── {algorithm_name}/
            └── initial{N}_batch{M}_rate{R}/
                └── {index_params_str}/
                    └── {query_params_str}/
                        ├── metrics.json
                        ├── query_results.npy
                        ├── latencies.json
                        └── metadata.json
    """
    
    def __init__(self, base_dir: str = "results"):
        """
        Initialize results manager.
        
        Args:
            base_dir: Base directory for all results
        """
        self.base_dir = base_dir
    
    def _extract_runbook_params(self, runbook) -> Dict[str, int]:
        """Extract key parameters from runbook"""
        params = {
            'initial_size': 0,
            'batch_size': 0,
            'event_rate': 0
        }
        
        for entry in runbook:
            operation = entry.get('operation', '')
            if operation == 'initial':
                params['initial_size'] = entry.get('end', 0) - entry.get('start', 0)
            elif operation == 'batch_insert':
                if params['batch_size'] == 0:
                    params['batch_size'] = entry.get('batchSize', 0)
                    params['event_rate'] = entry.get('eventRate', 0)
        
        return params
    
    def _format_params(self, params: Dict[str, Any]) -> str:
        """Format parameters as a clean string for directory naming"""
        parts = []
        for key, value in sorted(params.items()):
            if isinstance(value, float):
                parts.append(f"{key}{value:.6g}")
            else:
                parts.append(f"{key}{value}")
        return "_".join(parts) if parts else "default"
    
    def get_result_path(self, 
                       dataset_name: str,
                       algorithm_name: str,
                       runbook_params: Dict[str, int],
                       index_params: Dict[str, Any],
                       query_params: Dict[str, Any]) -> str:
        """
        Get the directory path for storing results.
        
        Args:
            dataset_name: Name of the dataset
            algorithm_name: Name of the algorithm
            runbook_params: Runbook parameters (initial_size, batch_size, event_rate)
            index_params: Index construction parameters
            query_params: Query parameters
        
        Returns:
            Path to the results directory
        """
        # Create runbook directory name
        runbook_dir = f"initial{runbook_params['initial_size']}_" \
                     f"batch{runbook_params['batch_size']}_" \
                     f"rate{runbook_params['event_rate']}"
        
        # Format index and query parameters
        index_str = self._format_params(index_params)
        query_str = self._format_params(query_params)
        
        # Construct full path
        path = os.path.join(
            self.base_dir,
            dataset_name,
            algorithm_name,
            runbook_dir,
            index_str,
            query_str
        )
        
        return path
    
    def save_results(self,
                    results: Dict[str, Any],
                    dataset_name: str,
                    algorithm_name: str,
                    runbook,
                    index_params: Dict[str, Any],
                    query_params: Dict[str, Any],
                    config: Dict[str, Any] = None,
                    groundtruth_dir: str = None) -> str:
        """
        Save benchmark results to organized directory structure.
        
        Args:
            results: Results dictionary from CongestionRunner
            dataset_name: Dataset name
            algorithm_name: Algorithm name
            runbook: Runbook object or entries list
            index_params: Index parameters
            query_params: Query parameters
            config: Optional full configuration for reference
            groundtruth_dir: Optional path to groundtruth directory for recall computation
        
        Returns:
            Path where results were saved
        """
        # Extract runbook parameters
        runbook_entries = runbook.entries if hasattr(runbook, 'entries') else runbook
        runbook_params = self._extract_runbook_params(runbook_entries)
        
        # Get result directory
        result_dir = self.get_result_path(
            dataset_name=dataset_name,
            algorithm_name=algorithm_name,
            runbook_params=runbook_params,
            index_params=index_params,
            query_params=query_params
        )
        
        os.makedirs(result_dir, exist_ok=True)
        
        # Save main metrics
        metrics_file = os.path.join(result_dir, 'metrics.json')
        metrics = {
            'algorithm': algorithm_name,
            'dataset': dataset_name,
            'timestamp': datetime.now().isoformat(),
            'total_time': results.get('total_time', 0),
            'setup_time': results.get('setup_time', 0),
            'operation_counts': results.get('operation_counts', {}),
            'insert_stats': self._convert_numpy(results.get('insert_stats', {})),
            'query_stats': self._convert_numpy(results.get('query_stats', {})),
            'delete_stats': self._convert_numpy(results.get('delete_stats', {})),
        }
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Save detailed latencies
        latencies_file = os.path.join(result_dir, 'latencies.json')
        latencies = {
            'insert_latencies': self._convert_numpy(results.get('insert_latencies', [])),
            'query_latencies': self._convert_numpy(results.get('query_latencies', [])),
            'delete_latencies': self._convert_numpy(results.get('delete_latencies', [])),
            'continuous_query_latencies': self._convert_numpy(results.get('continuous_query_latencies', [])),
        }
        
        with open(latencies_file, 'w') as f:
            json.dump(latencies, f, indent=2)
        
        # Save query results if available
        continuous_query_results = results.get('continuous_query_results', [])
        if continuous_query_results:
            results_file = os.path.join(result_dir, 'continuous_query_results.npy')
            # Stack results into array
            try:
                results_array = np.array(continuous_query_results)
                np.save(results_file, results_array)
            except:
                # If can't stack, save as list in JSON
                results_json = os.path.join(result_dir, 'continuous_query_results.json')
                with open(results_json, 'w') as f:
                    json.dump(self._convert_numpy(continuous_query_results), f, indent=2)
        
        # Save throughput data
        if 'insert_throughputs' in results or 'batch_throughputs' in results:
            throughput_file = os.path.join(result_dir, 'throughput.json')
            throughput = {
                'insert_throughputs': self._convert_numpy(results.get('insert_throughputs', [])),
                'batch_throughputs': self._convert_numpy(results.get('batch_throughputs', [])),
            }
            with open(throughput_file, 'w') as f:
                json.dump(throughput, f, indent=2)
        
        # Save queue metrics if available
        if 'pending_queue_lengths' in results or 'drop_counts' in results:
            queue_file = os.path.join(result_dir, 'queue_metrics.json')
            queue_metrics = {
                'pending_queue_lengths': self._convert_numpy(results.get('pending_queue_lengths', [])),
                'drop_counts': self._convert_numpy(results.get('drop_counts', [])),
            }
            with open(queue_file, 'w') as f:
                json.dump(queue_metrics, f, indent=2)
        
        # Save metadata with full configuration
        metadata_file = os.path.join(result_dir, 'metadata.json')
        metadata = {
            'dataset_name': dataset_name,
            'algorithm_name': algorithm_name,
            'runbook_params': runbook_params,
            'index_params': self._convert_numpy(index_params),
            'query_params': self._convert_numpy(query_params),
            'timestamp': datetime.now().isoformat(),
            'full_config': self._convert_numpy(config) if config else None,
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Compute recall metrics if groundtruth directory is provided
        if groundtruth_dir and os.path.exists(groundtruth_dir):
            try:
                from . import metrics
                print(f"\nComputing recall metrics against groundtruth...")
                
                # Load continuous query results from the saved file
                results_for_recall = {
                    'continuous_query_results': continuous_query_results
                }
                
                recall_metrics = metrics.compute_metrics_with_groundtruth(
                    results=results_for_recall,
                    groundtruth_dir=groundtruth_dir,
                    k_values=[1, 10, 100]
                )
                
                if recall_metrics and recall_metrics.get('continuous_query_recalls'):
                    recall_file = os.path.join(result_dir, 'recall.json')
                    with open(recall_file, 'w') as f:
                        json.dump(recall_metrics, f, indent=2)
                    print(f"  - recall.json: Recall@k metrics")
                else:
                    print(f"  Warning: No recall metrics computed (no query results or groundtruth)")
            except Exception as e:
                print(f"  Warning: Error computing recall: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\nResults saved to: {result_dir}")
        print(f"  - metrics.json: Summary statistics")
        print(f"  - latencies.json: Detailed latency measurements")
        print(f"  - metadata.json: Configuration and parameters")
        
        return result_dir
    
    def _convert_numpy(self, obj):
        """Convert numpy types to Python types for JSON serialization"""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: self._convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy(item) for item in obj]
        return obj
    
    def load_results(self, result_path: str) -> Dict[str, Any]:
        """
        Load results from a directory.
        
        Args:
            result_path: Path to the results directory
        
        Returns:
            Dictionary with all loaded results
        """
        results = {}
        
        # Load metrics
        metrics_file = os.path.join(result_path, 'metrics.json')
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                results['metrics'] = json.load(f)
        
        # Load latencies
        latencies_file = os.path.join(result_path, 'latencies.json')
        if os.path.exists(latencies_file):
            with open(latencies_file, 'r') as f:
                results['latencies'] = json.load(f)
        
        # Load metadata
        metadata_file = os.path.join(result_path, 'metadata.json')
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                results['metadata'] = json.load(f)
        
        # Load query results if available
        results_npy = os.path.join(result_path, 'continuous_query_results.npy')
        if os.path.exists(results_npy):
            results['continuous_query_results'] = np.load(results_npy)
        
        return results
    
    def find_matching_results(self,
                            dataset_name: str = None,
                            algorithm_name: str = None,
                            runbook_params: Dict[str, int] = None) -> list:
        """
        Find all result directories matching the given criteria.
        
        Args:
            dataset_name: Filter by dataset name
            algorithm_name: Filter by algorithm name
            runbook_params: Filter by runbook parameters
        
        Returns:
            List of matching result directory paths
        """
        matching_paths = []
        
        # Start from dataset level
        if dataset_name:
            search_root = os.path.join(self.base_dir, dataset_name)
            if not os.path.exists(search_root):
                return []
        else:
            search_root = self.base_dir
        
        # Walk through directory structure
        for root, dirs, files in os.walk(search_root):
            if 'metadata.json' in files:
                # Load metadata to check if it matches criteria
                metadata_file = os.path.join(root, 'metadata.json')
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Check filters
                    if algorithm_name and metadata.get('algorithm_name') != algorithm_name:
                        continue
                    
                    if runbook_params:
                        meta_runbook = metadata.get('runbook_params', {})
                        if not all(meta_runbook.get(k) == v for k, v in runbook_params.items()):
                            continue
                    
                    matching_paths.append(root)
                except:
                    continue
        
        return matching_paths
