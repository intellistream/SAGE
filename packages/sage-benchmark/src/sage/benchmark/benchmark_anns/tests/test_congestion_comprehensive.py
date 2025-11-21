#!/usr/bin/env python3
"""
Main entry point for congestion benchmark tests.

Usage:
    python main.py --config configs/faiss_hnsw_config.yaml
    python main.py --algorithm faiss_hnsw --dataset sift --runbook configs/example_runbook.yaml
"""

import argparse
import yaml
import json
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark_anns.core import CongestionRunner, Runbook, create_simple_runbook, ResultsManager
from benchmark_anns.algorithms.faiss_hnsw import FaissHNSWCongestion
from benchmark_anns.datasets import SimpleDataset


def load_config(config_file):
    """Load configuration from YAML file"""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def create_algorithm(config):
    """Create algorithm instance from configuration"""
    algo_config = config.get('algorithm', {})
    algo_name = algo_config.get('name', 'faiss_hnsw')
    
    index_params = algo_config.get('index_params', {'indexkey': 'HNSW32'})
    metric = algo_config.get('metric', 'euclidean')
    parallel_workers = algo_config.get('parallel_workers', 1)
    
    if algo_name == 'faiss_hnsw':
        return FaissHNSWCongestion(
            metric=metric,
            index_params=index_params,
            parallel_workers=parallel_workers
        )
    else:
        raise ValueError(f"Unknown algorithm: {algo_name}")


def create_dataset(config):
    """Create dataset instance from configuration"""
    dataset_config = config.get('dataset', {})
    name = dataset_config.get('name', 'test')
    data_path = dataset_config.get('data_path', 'data')
    dtype = dataset_config.get('dtype', 'float32')
    metric = config.get('algorithm', {}).get('metric', 'euclidean')
    
    dataset = SimpleDataset(name, data_path, dtype=dtype, metric=metric)
    
    # Try to load .npy synthetic files first (for consistency with groundtruth)
    import numpy as np
    base_npy = os.path.join(data_path, f"{name}_synthetic_base.npy")
    query_npy = os.path.join(data_path, f"{name}_synthetic_query.npy")
    
    if os.path.exists(base_npy) and os.path.exists(query_npy):
        # Load existing synthetic data (ensures consistency)
        dataset._base_data = np.load(base_npy)
        dataset._query_data = np.load(query_npy)
        dataset.nb = len(dataset._base_data)
        dataset.nq = len(dataset._query_data)
        dataset.d = dataset._base_data.shape[1]
        print(f"Loaded synthetic dataset: {dataset.nb} base vectors, {dataset.nq} queries, "
              f"dimension {dataset.d}")
        print(f"  Base: {base_npy}")
        print(f"  Query: {query_npy}")
        return dataset
    
    # Try to load real dataset files (.fvecs format)
    try:
        dataset.load_base()
        dataset.load_queries()
        print(f"Loaded real dataset: {dataset.nb} base vectors, {dataset.nq} queries, "
              f"dimension {dataset.d}")
        return dataset
    except FileNotFoundError as e:
        print(f"Warning: Could not load dataset files: {e}")
        print(f"Creating new synthetic dataset...")
        
        # Use fixed seed for reproducibility (same as compute_groundtruth.py)
        np.random.seed(42)
        
        dataset.d = 128
        dataset.nb = 100000  # Match runbook expectations
        dataset.nq = 100
        dataset._base_data = np.random.randn(dataset.nb, dataset.d).astype(np.float32)
        
        # Generate queries from base data (same as compute_groundtruth.py)
        np.random.seed(43)  # Same seed!
        query_indices = np.random.choice(dataset.nb, dataset.nq, replace=False)
        dataset._query_data = dataset._base_data[query_indices]
        
        # Save synthetic data for groundtruth computation
        os.makedirs(data_path, exist_ok=True)
        np.save(base_npy, dataset._base_data)
        np.save(query_npy, dataset._query_data)
        
        print(f"Created synthetic dataset: {dataset.nb} vectors, {dataset.nq} queries")
        print(f"Saved to: {base_npy}, {query_npy}")
    
    return dataset


def load_runbook(config):
    """Load runbook from configuration"""
    runbook_config = config.get('runbook', {})
    
    if 'file' in runbook_config:
        runbook_file = runbook_config['file']
        if not os.path.isabs(runbook_file):
            # Make path relative to config file or current directory
            runbook_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                runbook_file
            )
        
        if os.path.exists(runbook_file):
            print(f"Loading runbook from {runbook_file}")
            return Runbook.from_yaml(runbook_file)
        else:
            print(f"Warning: Runbook file not found: {runbook_file}")
            print("Creating simple default runbook...")
            return create_simple_runbook()
    else:
        print("No runbook specified, creating simple default runbook...")
        return create_simple_runbook()


def main():
    parser = argparse.ArgumentParser(description='Run congestion benchmark tests')
    parser.add_argument('--config', type=str, required=True,
                      help='Path to configuration YAML file')
    parser.add_argument('--output-dir', type=str, default='results',
                      help='Base directory for output results (default: results/)')
    parser.add_argument('--groundtruth-dir', type=str, default=None,
                      help='Path to groundtruth directory for recall computation (default: auto-detect)')
    parser.add_argument('--output', type=str, default=None,
                      help='Legacy: specific output file path (optional)')
    parser.add_argument('--k', type=int, default=10,
                      help='Number of nearest neighbors (default: 10)')
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}")
        print(f"Please create a configuration file or use --config to specify a valid path")
        sys.exit(1)
    
    print(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    
    # Create algorithm
    print("\n=== Creating Algorithm ===")
    algo = create_algorithm(config)
    print(f"Algorithm: {algo.name}")
    
    # Load dataset
    print("\n=== Loading Dataset ===")
    dataset = create_dataset(config)
    
    # Load runbook
    print("\n=== Loading Runbook ===")
    runbook = load_runbook(config)
    print(f"Runbook contains {len(runbook)} operations")
    
    # Setup algorithm
    print("\n=== Setting Up Algorithm ===")
    test_config = config.get('test', {})
    max_pts = test_config.get('max_pts', 100000)
    k = test_config.get('k', args.k)
    
    setup_time = CongestionRunner.setup_algorithm(algo, dataset, max_pts)
    
    # Initialize results manager
    results_manager = ResultsManager(base_dir=args.output_dir)
    
    # Get configuration details
    algo_config = config.get('algorithm', {})
    dataset_name = config.get('dataset', {}).get('name', 'unknown')
    algorithm_name = algo_config.get('name', 'unknown')
    index_params = algo_config.get('index_params', {})
    
    # Check if we have multiple parameter configurations
    query_params_list = algo_config.get('query_params_list', None)
    
    # If no list provided, use single query_params
    if query_params_list is None:
        query_params = algo_config.get('query_params', {})
        query_params_list = [{'name': 'default', **query_params}] if query_params else [{'name': 'default'}]
    
    all_results = []
    
    # Run test for each parameter configuration
    for param_idx, query_params in enumerate(query_params_list):
        param_name = query_params.get('name', f'config_{param_idx}')
        print(f"\n{'=' * 70}")
        print(f"Testing Parameter Configuration: {param_name}")
        print(f"{'=' * 70}")
        print(f"Parameters: {query_params}")
        
        # Set query parameters (excluding 'name' key)
        params_to_set = {k: v for k, v in query_params.items() if k != 'name'}
        if params_to_set:
            algo.set_query_arguments(params_to_set)
        
        # Reset algorithm state before each run (except first)
        if param_idx > 0 and hasattr(algo, 'reset_index'):
            print(f"Resetting algorithm for next parameter set...")
            algo.reset_index()
            CongestionRunner.setup_algorithm(algo, dataset, max_pts)
        
        print(f"\n=== Running Congestion Test ===")
        print(f"k={k}, max_pts={max_pts}")
        print("-" * 70)
        
        try:
            results = CongestionRunner.run_test(
                algo=algo,
                dataset=dataset,
                runbook=runbook,
                query_args=params_to_set,
                k=k
            )
            
            results['setup_time'] = setup_time
            results['param_name'] = param_name
            results['param_config'] = params_to_set
            
            all_results.append(results)
            
            # Determine groundtruth directory
            groundtruth_dir = args.groundtruth_dir
            if groundtruth_dir is None:
                # Auto-detect groundtruth directory based on runbook parameters
                runbook_entries = runbook.entries if hasattr(runbook, 'entries') else runbook
                runbook_params = results_manager._extract_runbook_params(runbook_entries)
                initial_size = runbook_params.get('initial_size', 0)
                batch_size = runbook_params.get('batch_size', 0)
                event_rate = runbook_params.get('event_rate', 0)
                
                groundtruth_dir = os.path.join(
                    args.output_dir,
                    'groundtruth',
                    dataset_name,
                    f"initial{initial_size}_batch{batch_size}_rate{event_rate}"
                )
                print(f"\nAuto-detected groundtruth directory: {groundtruth_dir}")
            
            # Save results using ResultsManager
            result_path = results_manager.save_results(
                results=results,
                dataset_name=dataset_name,
                algorithm_name=algorithm_name,
                runbook=runbook,
                index_params=index_params,
                query_params=params_to_set,
                config=config,
                groundtruth_dir=groundtruth_dir
            )
            
            print(f"\n--- Results for {param_name} ---")
            print(f"Total time: {results['total_time']:.2f}s")
            print(f"Insert stats: mean={results['insert_stats']['mean']/1e3:.2f}ms, "
                  f"p95={results['insert_stats']['p95']/1e3:.2f}ms")
            if results['query_stats']['mean'] > 0:
                print(f"Query stats:  mean={results['query_stats']['mean']/1e3:.2f}ms, "
                      f"p95={results['query_stats']['p95']/1e3:.2f}ms")
            
        except Exception as e:
            print(f"\n!!! Test failed for {param_name} !!!")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            # Continue with next parameter set
            continue
    
    # Optional: Save legacy combined JSON file if --output specified
    if args.output:
        output_file = args.output
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        
        def convert_numpy(obj):
            import numpy as np
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj
        
        if len(all_results) > 1:
            results_serializable = convert_numpy(all_results)
            output_data = {
                'multi_param_test': True,
                'num_configurations': len(all_results),
                'results': results_serializable
            }
        else:
            results_serializable = convert_numpy(all_results[0]) if all_results else {}
            output_data = results_serializable
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nLegacy JSON also saved to: {output_file}")
    
    # Print final summary
    print(f"\n{'=' * 70}")
    print(f"=== All Tests Completed ===")
    print(f"{'=' * 70}")
    
    if len(all_results) > 1:
        print(f"\nTested {len(all_results)} parameter configurations")
        print(f"Results organized in: {args.output_dir}/{dataset_name}/{algorithm_name}/")
        print(f"\nParameter configurations tested:")
        for idx, result in enumerate(all_results):
            param_name = result.get('param_name', f'config_{idx}')
            print(f"  {idx+1}. {param_name}")
            print(f"     Total time: {result['total_time']:.2f}s")
            if result['query_stats']['mean'] > 0:
                print(f"     Query p95:  {result['query_stats']['p95']/1e3:.2f}ms")
    elif all_results:
        result = all_results[0]
        print(f"\nResults saved to: {args.output_dir}/{dataset_name}/{algorithm_name}/")
        print(f"\nSummary:")
        print(f"  Total time: {result['total_time']:.2f}s")
        print(f"  Operations: {result['operation_counts']}")
        if result['insert_stats']['mean'] > 0:
            print(f"  Insert stats: mean={result['insert_stats']['mean']/1e3:.2f}ms, "
                  f"p95={result['insert_stats']['p95']/1e3:.2f}ms")
        if result['query_stats']['mean'] > 0:
            print(f"  Query stats:  mean={result['query_stats']['mean']/1e3:.2f}ms, "
                  f"p95={result['query_stats']['p95']/1e3:.2f}ms")
    else:
        print("\nNo results generated.")
        sys.exit(1)


if __name__ == '__main__':
    main()
