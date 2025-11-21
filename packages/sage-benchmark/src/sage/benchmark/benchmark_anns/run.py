#!/usr/bin/env python3
"""
ANNS Benchmark Runner

A clean, user-friendly interface for running ANNS benchmarks with different tracks.

Usage:
    # Run congestion track
    python run.py --track congestion --algorithm faiss_hnsw --dataset sift \
                  --runbook runbooks/basic_test.yaml --output results/

    # Run with custom config file
    python run.py --config configs/faiss_hnsw_config.yaml

    # Compute groundtruth first
    python run.py --track groundtruth --config configs/faiss_hnsw_config.yaml

Tracks:
    - congestion: Test algorithm under high-throughput insertion/deletion workloads
    - streaming: Test algorithm with continuous data streams
    - groundtruth: Compute exact k-NN for evaluation
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark_anns.core import CongestionRunner, Runbook, ResultsManager
from benchmark_anns.datasets import SimpleDataset
import yaml
import numpy as np


def load_config(config_file):
    """Load configuration from YAML file"""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def create_algorithm(config):
    """
    Create algorithm instance from configuration using dynamic import.
    
    The algorithm class is imported dynamically based on config, so adding
    new algorithms doesn't require modifying this file.
    
    Config format:
        algorithm:
          name: "faiss_hnsw"
          module: "benchmark_anns.algorithms.faiss_hnsw"  # optional, auto-inferred if not provided
          class: "FaissHNSWCongestion"  # optional, auto-inferred if not provided
          metric: "euclidean"
          index_params: {...}
          parallel_workers: 1
    """
    algo_config = config.get('algorithm', {})
    algo_name = algo_config.get('name')
    
    if not algo_name:
        raise ValueError("Algorithm name must be specified in config: algorithm.name")
    
    # Get module path (auto-infer if not specified)
    module_path = algo_config.get('module')
    if not module_path:
        # Auto-infer: benchmark_anns.algorithms.{algo_name}
        module_path = f"benchmark_anns.algorithms.{algo_name}"
    
    # Get class name (auto-infer if not specified)
    class_name = algo_config.get('class')
    if not class_name:
        # Auto-infer: try to import module first and find matching class
        import importlib
        try:
            module = importlib.import_module(module_path)
            
            # Look for classes ending with "Congestion"
            congestion_classes = [
                name for name in dir(module)
                if name.endswith('Congestion') and not name.startswith('_')
            ]
            
            if len(congestion_classes) == 1:
                # Found exactly one Congestion class
                class_name = congestion_classes[0]
            elif len(congestion_classes) > 1:
                # Multiple candidates, try to match based on algo_name
                # Convert algo_name parts to uppercase for matching
                name_upper = algo_name.upper().replace('_', '')
                for candidate in congestion_classes:
                    if name_upper in candidate.upper().replace('_', ''):
                        class_name = candidate
                        break
                
                if not class_name:
                    # Fallback: use first one
                    class_name = congestion_classes[0]
            else:
                # No Congestion class found, fallback to simple conversion
                parts = algo_name.split('_')
                class_name = ''.join(word.capitalize() for word in parts) + 'Congestion'
        except ImportError:
            # Module doesn't exist yet, use simple conversion
            parts = algo_name.split('_')
            class_name = ''.join(word.capitalize() for word in parts) + 'Congestion'
    
    # Dynamic import
    if not class_name:
        # If still no class name after auto-inference, raise error
        raise ValueError(
            f"Cannot infer class name for algorithm '{algo_name}' "
            f"and no 'class' specified in config"
        )
    
    try:
        import importlib
        if 'module' not in locals():
            module = importlib.import_module(module_path)
        AlgoClass = getattr(module, class_name)
    except ImportError as e:
        raise ImportError(
            f"Cannot import algorithm module '{module_path}': {e}\n"
            f"Make sure the module exists and is in PYTHONPATH"
        )
    except AttributeError as e:
        raise AttributeError(
            f"Cannot find class '{class_name}' in module '{module_path}': {e}\n"
            f"Available classes: {[name for name in dir(module) if not name.startswith('_')]}"
        )
    
    # Prepare constructor arguments
    metric = algo_config.get('metric', 'euclidean')
    index_params = algo_config.get('index_params', {})
    parallel_workers = algo_config.get('parallel_workers', 1)
    
    # Instantiate algorithm
    # Try different constructor signatures
    try:
        # Try full signature first
        return AlgoClass(
            metric=metric,
            index_params=index_params,
            parallel_workers=parallel_workers
        )
    except TypeError:
        # Try without parallel_workers
        try:
            return AlgoClass(
                metric=metric,
                index_params=index_params
            )
        except TypeError:
            # Try minimal signature
            return AlgoClass(metric=metric)


def load_dataset(config):
    """Load dataset from configuration"""
    dataset_config = config.get('dataset', {})
    name = dataset_config.get('name', 'test')
    data_path = dataset_config.get('data_path', 'data')
    dtype = dataset_config.get('dtype', 'float32')
    metric = config.get('algorithm', {}).get('metric', 'euclidean')
    
    dataset = SimpleDataset(name, data_path, dtype=dtype, metric=metric)
    
    # Try to load .npy synthetic files first (for consistency with groundtruth)
    base_npy = os.path.join(data_path, f"{name}_synthetic_base.npy")
    query_npy = os.path.join(data_path, f"{name}_synthetic_query.npy")
    
    if os.path.exists(base_npy) and os.path.exists(query_npy):
        # Load existing synthetic data
        dataset._base_data = np.load(base_npy)
        dataset._query_data = np.load(query_npy)
        dataset.nb = len(dataset._base_data)
        dataset.nq = len(dataset._query_data)
        dataset.d = dataset._base_data.shape[1]
        print(f"Loaded dataset: {dataset.nb} base vectors, {dataset.nq} queries, dim={dataset.d}")
        print(f"  Base: {base_npy}")
        print(f"  Query: {query_npy}")
        return dataset
    
    # Try to load real dataset files
    try:
        dataset.load_base()
        dataset.load_queries()
        print(f"Loaded dataset: {dataset.nb} base vectors, {dataset.nq} queries, dim={dataset.d}")
        return dataset
    except FileNotFoundError:
        print(f"Error: Dataset not found at {data_path}")
        print(f"Expected files: {name}_base.fvecs, {name}_query.fvecs")
        print(f"Or synthetic files: {name}_synthetic_base.npy, {name}_synthetic_query.npy")
        print(f"\nPlease either:")
        print(f"  1. Download the real dataset")
        print(f"  2. Generate synthetic data using: python -c 'from benchmark_anns.tests.main import create_dataset; create_dataset(config)'")
        sys.exit(1)


def load_runbook(config, runbook_path=None):
    """Load runbook from file or configuration"""
    if runbook_path:
        if not os.path.exists(runbook_path):
            print(f"Error: Runbook file not found: {runbook_path}")
            sys.exit(1)
        print(f"Loading runbook from {runbook_path}")
        return Runbook.from_yaml(runbook_path)
    
    runbook_config = config.get('runbook', {})
    if 'file' in runbook_config:
        runbook_file = runbook_config['file']
        if not os.path.isabs(runbook_file):
            runbook_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                runbook_file
            )
        
        if os.path.exists(runbook_file):
            print(f"Loading runbook from {runbook_file}")
            return Runbook.from_yaml(runbook_file)
    
    print("Error: No runbook specified")
    print("Please specify runbook with --runbook or in config file")
    sys.exit(1)


def run_groundtruth(config, args):
    """Run groundtruth computation track"""
    print("\n" + "=" * 70)
    print("GROUNDTRUTH COMPUTATION TRACK")
    print("=" * 70)
    
    # Import groundtruth computation
    from benchmark_anns.core import compute_runbook_groundtruth
    
    # Load dataset
    print("\n=== Loading Dataset ===")
    dataset_config = config.get('dataset', {})
    dataset_name = dataset_config.get('name', 'test')
    dataset_path = dataset_config.get('data_path', 'data')
    
    # Load data
    from benchmark_anns.datasets.simple_dataset import SimpleDataset
    synthetic_base = os.path.join(dataset_path, f"{dataset_name}_synthetic_base.npy")
    
    if os.path.exists(synthetic_base):
        data = np.load(synthetic_base)
        print(f"Loaded synthetic dataset from {synthetic_base}")
        print(f"Dataset: {len(data)} vectors, dim={data.shape[1]}")
    else:
        print(f"Error: Dataset not found: {synthetic_base}")
        print("Please run a test first to generate synthetic data")
        sys.exit(1)
    
    class SyntheticDataset:
        def __init__(self, data):
            self._data = data
        def get_dataset(self):
            return self._data
    
    dataset = SyntheticDataset(data)
    
    # Load queries
    synthetic_query = os.path.join(dataset_path, f"{dataset_name}_synthetic_query.npy")
    if os.path.exists(synthetic_query):
        queries = np.load(synthetic_query)
        print(f"Loaded {len(queries)} queries from: {synthetic_query}")
    else:
        print(f"Error: Query file not found: {synthetic_query}")
        sys.exit(1)
    
    # Load runbook
    runbook = load_runbook(config, args.runbook)
    print(f"Runbook contains {len(runbook.entries)} operations")
    
    # Get parameters
    metric = config.get('algorithm', {}).get('metric', 'euclidean')
    k = args.k
    output_dir = args.output or 'results/groundtruth'
    
    print(f"\n=== Computing Groundtruth ===")
    print(f"Dataset: {dataset_name}")
    print(f"K: {k}")
    print(f"Metric: {metric}")
    print(f"Output: {output_dir}")
    print()
    
    # Compute groundtruth
    groundtruths = compute_runbook_groundtruth(
        dataset=dataset,
        runbook=runbook.entries,
        queries=queries,
        k=k,
        metric=metric,
        output_dir=output_dir,
        dataset_name=dataset_name,
        verbose=args.verbose
    )
    
    print(f"\n=== Groundtruth Complete ===")
    print(f"Computed groundtruth for {len(groundtruths)} search operations")
    print(f"Results saved to: {output_dir}")


def run_congestion(config, args):
    """Run congestion track"""
    print("\n" + "=" * 70)
    print("CONGESTION TRACK")
    print("=" * 70)
    
    # Create algorithm
    print("\n=== Creating Algorithm ===")
    algo = create_algorithm(config)
    print(f"Algorithm: {algo.name}")
    
    # Load dataset
    print("\n=== Loading Dataset ===")
    dataset = load_dataset(config)
    
    # Load runbook
    print("\n=== Loading Runbook ===")
    runbook = load_runbook(config, args.runbook)
    print(f"Runbook contains {len(runbook.entries)} operations")
    
    # Setup algorithm
    print("\n=== Setting Up Algorithm ===")
    test_config = config.get('test', {})
    max_pts = test_config.get('max_pts', args.max_pts or 100000)
    k = args.k or test_config.get('k', 10)
    
    setup_time = CongestionRunner.setup_algorithm(algo, dataset, max_pts)
    
    # Get algorithm parameters
    algo_config = config.get('algorithm', {})
    dataset_name = config.get('dataset', {}).get('name', 'unknown')
    algorithm_name = algo_config.get('name', 'unknown')
    index_params = algo_config.get('index_params', {})
    
    # Get query parameters
    query_params_list = algo_config.get('query_params_list', None)
    if query_params_list is None:
        query_params = algo_config.get('query_params', {})
        query_params_list = [{'name': 'default', **query_params}] if query_params else [{'name': 'default'}]
    
    # Initialize results manager
    output_dir = args.output or 'results'
    results_manager = ResultsManager(base_dir=output_dir)
    
    all_results = []
    
    # Run test for each parameter configuration
    for param_idx, query_params in enumerate(query_params_list):
        param_name = query_params.get('name', f'config_{param_idx}')
        print(f"\n{'=' * 70}")
        print(f"Testing Parameter Configuration: {param_name}")
        print(f"{'=' * 70}")
        print(f"Parameters: {query_params}")
        
        # Set query parameters
        params_to_set = {k: v for k, v in query_params.items() if k != 'name'}
        if params_to_set:
            algo.set_query_arguments(params_to_set)
        
        # Reset algorithm state for subsequent runs
        if param_idx > 0 and hasattr(algo, 'reset_index'):
            print(f"Resetting algorithm...")
            algo.reset_index()
            CongestionRunner.setup_algorithm(algo, dataset, max_pts)
        
        print(f"\n=== Running Test ===")
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
                runbook_entries = runbook.entries if hasattr(runbook, 'entries') else runbook
                runbook_params = results_manager._extract_runbook_params(runbook_entries)
                initial_size = runbook_params.get('initial_size', 0)
                batch_size = runbook_params.get('batch_size', 0)
                event_rate = runbook_params.get('event_rate', 0)
                
                groundtruth_dir = os.path.join(
                    output_dir,
                    'groundtruth',
                    dataset_name,
                    f"initial{initial_size}_batch{batch_size}_rate{event_rate}"
                )
            
            # Save results
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
            continue
    
    # Print summary
    print(f"\n{'=' * 70}")
    print(f"=== Test Complete ===")
    print(f"{'=' * 70}")
    
    if len(all_results) > 1:
        print(f"\nTested {len(all_results)} parameter configurations")
        print(f"Results saved to: {output_dir}/{dataset_name}/{algorithm_name}/")
    elif all_results:
        result = all_results[0]
        print(f"\nResults saved to: {output_dir}/{dataset_name}/{algorithm_name}/")
        print(f"\nSummary:")
        print(f"  Total time: {result['total_time']:.2f}s")
        print(f"  Operations: {result['operation_counts']}")


def main():
    parser = argparse.ArgumentParser(
        description='ANNS Benchmark Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run congestion track with config file
  python run.py --track congestion --config configs/faiss_hnsw_config.yaml

  # Run with specific parameters
  python run.py --track congestion --algorithm faiss_hnsw --dataset sift \\
                --runbook runbooks/basic_test.yaml --k 10 --output results/

  # Compute groundtruth
  python run.py --track groundtruth --config configs/faiss_hnsw_config.yaml \\
                --output results/groundtruth/ --k 100 --verbose

For more information, see README.md
        """
    )
    
    # Track selection
    parser.add_argument(
        '--track',
        type=str,
        choices=['congestion', 'streaming', 'groundtruth'],
        default='congestion',
        help='Benchmark track to run (default: congestion)'
    )
    
    # Configuration
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration YAML file'
    )
    
    parser.add_argument(
        '--algorithm',
        type=str,
        help='Algorithm name (overrides config)'
    )
    
    parser.add_argument(
        '--dataset',
        type=str,
        help='Dataset name (overrides config)'
    )
    
    parser.add_argument(
        '--runbook',
        type=str,
        help='Path to runbook YAML file (overrides config)'
    )
    
    # Test parameters
    parser.add_argument(
        '--k',
        type=int,
        help='Number of nearest neighbors (default: 10 for congestion, 100 for groundtruth)'
    )
    
    parser.add_argument(
        '--max-pts',
        type=int,
        help='Maximum number of points to support (default: 100000)'
    )
    
    # Output
    parser.add_argument(
        '--output',
        type=str,
        help='Output directory for results (default: results/ for congestion, results/groundtruth/ for groundtruth)'
    )
    
    parser.add_argument(
        '--groundtruth-dir',
        type=str,
        help='Path to precomputed groundtruth directory (for recall computation)'
    )
    
    # Verbosity
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed progress information'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.config:
        print("Error: --config is required")
        print("Example: python run.py --config configs/faiss_hnsw_config.yaml")
        sys.exit(1)
    
    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)
    
    # Load configuration
    print(f"Loading configuration from {args.config}")
    config = load_config(args.config)
    
    # Override config with command line arguments
    if args.algorithm:
        config.setdefault('algorithm', {})['name'] = args.algorithm
    if args.dataset:
        config.setdefault('dataset', {})['name'] = args.dataset
    
    # Set default k based on track
    if not args.k:
        if args.track == 'groundtruth':
            args.k = 100
        else:
            args.k = config.get('test', {}).get('k', 10)
    
    # Run the selected track
    if args.track == 'groundtruth':
        run_groundtruth(config, args)
    elif args.track == 'congestion':
        run_congestion(config, args)
    elif args.track == 'streaming':
        print("Streaming track is not yet implemented")
        sys.exit(1)
    else:
        print(f"Unknown track: {args.track}")
        sys.exit(1)


if __name__ == '__main__':
    main()
