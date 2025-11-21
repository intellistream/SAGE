"""
Compute groundtruth for runbook operations

This script computes exact k-nearest neighbors at each search step in a runbook,
tracking the active dataset as inserts and deletes are performed.

Usage:
    python compute_groundtruth.py --config configs/faiss_hnsw_config.yaml --output results/groundtruth/
"""
import argparse
import os
import sys
import yaml
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark_anns.core import Runbook, compute_runbook_groundtruth
from benchmark_anns.datasets import get_dataset


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description='Compute groundtruth for runbook operations',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to algorithm configuration YAML file'
    )
    
    parser.add_argument(
        '--runbook',
        type=str,
        default=None,
        help='Path to runbook YAML file (overrides config file)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='results/groundtruth/',
        help='Output directory for groundtruth files'
    )
    
    parser.add_argument(
        '--k',
        type=int,
        default=10,
        help='Number of nearest neighbors to compute'
    )
    
    parser.add_argument(
        '--dataset-path',
        type=str,
        default=None,
        help='Path to dataset file (e.g., data.fvecs)'
    )
    
    parser.add_argument(
        '--query-path',
        type=str,
        default=None,
        help='Path to query file (e.g., query.fvecs)'
    )
    
    parser.add_argument(
        '--metric',
        type=str,
        choices=['euclidean', 'l2', 'ip', 'angular'],
        default='euclidean',
        help='Distance metric to use'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed progress'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    print(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    
    # Get dataset configuration
    dataset_config = config.get('dataset', {})
    dataset_name = dataset_config.get('name', 'random')
    dataset_path = dataset_config.get('data_path', None)
    
    # Override with command line args if provided
    if args.dataset_path:
        dataset_path = args.dataset_path
    
    # Load dataset
    print("\n=== Loading Dataset ===")
    from benchmark_anns.datasets.simple_dataset import SimpleDataset
    
    # Try to load .npy synthetic data first (ensures consistency)
    synthetic_base = os.path.join(dataset_path, f"{dataset_name}_synthetic_base.npy") if dataset_path else None
    
    if synthetic_base and os.path.exists(synthetic_base):
        # Load existing synthetic data
        data = np.load(synthetic_base)
        print(f"Loaded synthetic dataset from {synthetic_base}")
        print(f"Dataset: {len(data)} vectors, dim={data.shape[1]}")
    else:
        # Try to load real dataset files (.fvecs format)
        try:
            dataset = get_dataset(dataset_name)
            data = dataset.get_dataset()
            print(f"Loaded real dataset: {dataset_name}")
            print(f"Dataset: {len(data)} vectors, dim={data.shape[1]}")
        except:
            # Generate new synthetic data with fixed seed
            print(f"No existing data found. Creating synthetic dataset...")
            np.random.seed(42)  # Fixed seed for reproducibility
            
            n = dataset_config.get('n', 100000)  # Default to 100K to match typical runbooks
            dim = dataset_config.get('dim', 128)
            dtype = dataset_config.get('dtype', 'float32')
            
            data = np.random.randn(n, dim).astype(dtype)
            
            # Save for future use
            if dataset_path:
                os.makedirs(dataset_path, exist_ok=True)
                save_path = os.path.join(dataset_path, f"{dataset_name}_synthetic_base.npy")
                np.save(save_path, data)
                print(f"Saved synthetic dataset to {save_path}")
            print(f"Dataset: {len(data)} vectors, dim={data.shape[1]}")
    
    class SyntheticDataset:
        def __init__(self, data):
            self._data = data
        def get_dataset(self):
            return self._data
    
    dataset = SyntheticDataset(data)
    
    # Load queries - must use same file as main.py
    query_path = args.query_path if args.query_path else dataset_config.get('query_path', None)
    
    # Try synthetic query file first (ensures consistency with main.py)
    synthetic_query = os.path.join(dataset_path, f"{dataset_name}_synthetic_query.npy") if dataset_path else None
    
    if synthetic_query and os.path.exists(synthetic_query):
        queries = np.load(synthetic_query)
        print(f"Loaded {len(queries)} queries from: {synthetic_query}")
    elif query_path and os.path.exists(query_path):
        # Try to load query file
        try:
            if query_path.endswith('.npy'):
                queries = np.load(query_path)
            else:
                # Assume .fvecs format
                from benchmark_anns.datasets.simple_dataset import load_fvecs
                queries = load_fvecs(query_path)
            print(f"Loaded {len(queries)} queries from: {query_path}")
        except Exception as e:
            print(f"Warning: Failed to load queries from {query_path}: {e}")
            queries = None
    else:
        queries = None
    
    if queries is None:
        # Generate random queries with fixed seed (same as main.py)
        print(f"No query file found. Generating queries from base data...")
        np.random.seed(43)  # Same seed as main.py!
        data = dataset.get_dataset()
        num_queries = dataset_config.get('num_queries', 100)
        query_indices = np.random.choice(len(data), min(num_queries, len(data)), replace=False)
        queries = data[query_indices]
        print(f"Generated {len(queries)} random queries from base data")
        
        # Save for future use
        if dataset_path:
            query_save_path = os.path.join(dataset_path, f"{dataset_name}_synthetic_query.npy")
            np.save(query_save_path, queries)
            print(f"Saved queries to: {query_save_path}")
    
    # Get metric
    metric = args.metric
    if 'index_params' in config.get('algorithm', {}):
        config_metric = config['algorithm'].get('metric', '')
        if not config_metric:
            config_metric = config['algorithm']['index_params'].get('metric', '')
        if config_metric:
            metric = config_metric
            print(f"Using metric from config: {metric}")
    
    # Load runbook - try multiple possible locations in config
    runbook_path = args.runbook
    if not runbook_path:
        # Try different config keys
        runbook_path = config.get('runbook_path', '')
        if not runbook_path:
            runbook_path = config.get('runbook', {}).get('file', '')
    
    if not runbook_path:
        print("Error: No runbook specified in config or command line")
        print("Expected: --runbook option, or 'runbook_path' or 'runbook.file' in config")
        sys.exit(1)
    
    # Resolve relative path - relative to benchmark_anns directory, not config directory
    if not os.path.isabs(runbook_path):
        # Get the benchmark_anns root directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        runbook_path = os.path.join(script_dir, runbook_path)
    
    print(f"\n=== Loading Runbook ===")
    print(f"Loading runbook from {runbook_path}")
    runbook = Runbook.from_yaml(runbook_path)
    print(f"Runbook contains {len(runbook.entries)} operations")
    
    # Compute groundtruth
    print(f"\n=== Computing Groundtruth ===")
    print(f"Dataset: {dataset_name}")
    print(f"K = {args.k}")
    print(f"Metric = {metric}")
    print(f"Output directory = {args.output}")
    print()
    
    groundtruths = compute_runbook_groundtruth(
        dataset=dataset,
        runbook=runbook.entries,
        queries=queries,
        k=args.k,
        metric=metric,
        output_dir=args.output,
        dataset_name=dataset_name,
        verbose=args.verbose
    )
    
    # Summary
    print(f"\n=== Groundtruth Computation Complete ===")
    print(f"Computed groundtruth for {len(groundtruths)} search operations")
    print(f"Results saved to {args.output}")
    
    # Print summary of each step - separate normal and continuous queries
    print("\nSummary:")
    
    # Normal search operations
    normal_steps = sorted([k for k in groundtruths.keys() if isinstance(k, int)])
    if normal_steps:
        print("  Normal search operations:")
        for step in normal_steps:
            gt = groundtruths[step]
            print(f"    Step {step}: {gt['num_active_points']} active points, "
                  f"{gt['tags'].shape[0]} queries, k={gt['tags'].shape[1]}")
    
    # Continuous queries
    continuous_keys = sorted([k for k in groundtruths.keys() if isinstance(k, str)])
    if continuous_keys:
        print(f"  Continuous queries during batch_insert: {len(continuous_keys)}")
        # Print first and last few
        for key in continuous_keys[:3]:
            gt = groundtruths[key]
            print(f"    {key}: {gt['num_active_points']} active points, "
                  f"{gt['tags'].shape[0]} queries, k={gt['tags'].shape[1]}")
        if len(continuous_keys) > 6:
            print(f"    ... ({len(continuous_keys) - 6} more) ...")
        for key in continuous_keys[-3:]:
            if key not in continuous_keys[:3]:
                gt = groundtruths[key]
                print(f"    {key}: {gt['num_active_points']} active points, "
                      f"{gt['tags'].shape[0]} queries, k={gt['tags'].shape[1]}")


if __name__ == '__main__':
    main()
