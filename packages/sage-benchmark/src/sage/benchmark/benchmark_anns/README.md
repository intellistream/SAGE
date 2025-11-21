# Benchmark ANNS - Congestion Testing Framework

A streamlined benchmark framework for evaluating ANNS (Approximate Nearest Neighbor Search) algorithms under congestion scenarios with streaming workloads.

## Overview

This framework focuses on testing how ANNS algorithms handle:
- **Concurrent operations**: Insert, delete, and query operations happening simultaneously
- **Congestion scenarios**: Queue management, backpressure, and data dropping under high load
- **Streaming workloads**: Real-time data ingestion with timing constraints
- **Performance metrics**: Latency, throughput, and accuracy under various conditions

## Project Structure

```
benchmark_anns/
├── algorithms/          # Algorithm implementations
│   └── faiss_hnsw/     # Faiss HNSW implementation
├── configs/            # Algorithm configuration files
│   ├── faiss_hnsw_config.yaml
│   └── faiss_hnsw_multi_params.yaml
├── runbooks/           # Test scenario definitions
│   ├── basic_test.yaml
│   ├── light_workload.yaml
│   ├── heavy_workload.yaml
│   ├── congestion_stress.yaml
│   ├── query_intensive.yaml
│   └── README.md
├── core/               # Core framework components
│   ├── base_algorithm.py        # Base algorithm interfaces
│   ├── congestion_worker.py     # Worker for concurrent operations
│   ├── congestion_algorithm.py  # Multi-worker wrapper
│   ├── runbook.py              # Runbook loader
│   └── congestion_runner.py    # Test runner
├── datasets/           # Dataset loaders
│   └── simple_dataset.py
├── utils/              # Utility functions
│   ├── timestamp_utils.py
│   └── system_utils.py
├── main.py             # Main entry point
└── README.md           # This file
```

## Features

### Core Components

1. **Base Algorithm Interfaces**
   - `BaseANN`: Basic ANN interface
   - `BaseStreamingANN`: Streaming ANN with insert/delete support
   - `BaseCongestionANN`: Congestion-aware ANN with multi-worker support

2. **Congestion Worker**
   - Handles concurrent insert/delete/query operations
   - Queue-based congestion management
   - Support for data dropping and backpressure logic
   - Thread-safe operation processing

3. **Runbook System**
   - YAML-based test definition
   - Supports various operations: initial load, batch insert, delete, search, etc.
   - Flexible configuration for different test scenarios

4. **Performance Metrics**
   - Insert/delete/query latencies
   - Throughput measurements
   - Queue lengths and drop counts
   - Continuous query performance during ingestion

### Implemented Algorithms

- **Faiss HNSW**: Hierarchical Navigable Small World graphs using Faiss library

## Installation

### Prerequisites

- Python 3.8+
- PyCANDYAlgo (for Faiss bindings)
- NumPy, PyYAML, pandas

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run a test with the default configuration:

```bash
cd benchmark_anns
python main.py --config configs/faiss_hnsw_config.yaml
```

### Custom Configuration

Create your own configuration file:

```yaml
# Algorithm configuration (configs/my_algo_config.yaml)
algorithm:
  name: "faiss_hnsw"
  index_params:
    indexkey: "HNSW32"
  metric: "euclidean"
  parallel_workers: 1
  query_params:
    ef: 64

dataset:
  name: "sift"
  data_path: "data/sift"
  dtype: "float32"

test:
  k: 10
  max_pts: 100000

runbook:
  file: "runbooks/basic_test.yaml"  # Choose test scenario
```

### Using Different Workloads

The framework separates algorithm configuration from test scenarios:

- **configs/**: Algorithm parameters (index structure, search parameters)
- **runbooks/**: Test scenarios (workload patterns, operation sequences)

```bash
# Test with light workload
python main.py --config configs/faiss_hnsw_config.yaml

# Test same algorithm with heavy workload
# Just change the runbook reference in config or use different config file

# See runbooks/README.md for available scenarios:
# - basic_test.yaml: Standard balanced test
# - light_workload.yaml: Quick testing
# - heavy_workload.yaml: Stress test
# - congestion_stress.yaml: Drop handling test
# - query_intensive.yaml: Search performance focus
```

### Runbook Configuration

Define a sequence of operations in YAML (stored in `runbooks/` directory):

```yaml
# runbooks/custom_scenario.yaml
- operation: initial
  start: 0
  end: 10000

- operation: startHPC

- operation: batch_insert
  start: 10000
  end: 50000
  batchSize: 1000
  eventRate: 2000

- operation: search
  k: 10

- operation: waitPending

- operation: endHPC
```

See `runbooks/README.md` for detailed documentation on available runbooks and how to create custom scenarios.

### Command Line Options

```bash
python main.py --help

Options:
  --config CONFIG    Path to configuration file (default: configs/faiss_hnsw_config.yaml)
  --output OUTPUT    Path to output results file (default: results/test_results.json)
  --k K             Number of nearest neighbors (default: 10)
```

## Runbook Operations

### Supported Operations

- **initial**: Load initial dataset
  - `start`, `end`: Data range to load
  
- **startHPC**: Start background worker threads

- **endHPC**: Stop background worker threads

- **batch_insert**: Insert data in batches with timing
  - `start`, `end`: Data range
  - `batchSize`: Batch size
  - `eventRate`: Events per second

- **insert**: Single insert operation
  - `start`, `end`: Data range

- **delete**: Delete vectors
  - `start`, `end`: ID range to delete

- **search**: Perform search
  - `k`: Number of neighbors

- **waitPending**: Wait for pending operations to complete

- **enableScenario**: Enable special test scenarios
  - `randomDrop`: Enable random dropping
  - `randomDropProb`: Drop probability
  - `randomContamination`: Enable data contamination
  - `outOfOrder`: Enable out-of-order insertion

## Computing Groundtruth

The framework includes a pure Python groundtruth computation tool that tracks the active dataset through all operations and computes exact k-NN at each search step.

### Basic Usage

```bash
# Compute groundtruth based on config file
python compute_groundtruth.py --config configs/faiss_hnsw_config.yaml --output results/groundtruth/

# With custom parameters
python compute_groundtruth.py \
    --config configs/faiss_hnsw_config.yaml \
    --k 100 \
    --metric euclidean \
    --output results/groundtruth/ \
    --verbose
```

### Features

- **Pure Python**: No need to compile DiskANN or other tools
- **Efficient**: Uses NumPy optimized operations
- **Complete tracking**: Handles inserts, deletes, batch operations, and replacements
- **Multiple metrics**: Supports L2 (Euclidean) and inner product (MIPS)
- **Easy to use**: Automatically reads runbook and dataset from config

### Output Format

For each search operation in the runbook, three files are saved:

- `step{N}_tags.npy`: Tag IDs of nearest neighbors (shape: [num_queries, k])
- `step{N}_distances.npy`: Distances to neighbors (shape: [num_queries, k])
- `step{N}_meta.json`: Metadata including number of active points

### Using Groundtruth Programmatically

```python
from benchmark_anns.core import compute_runbook_groundtruth
from benchmark_anns.datasets import get_dataset
from benchmark_anns.core import Runbook

# Load data and runbook
dataset = get_dataset('random', n=10000, dim=128)
runbook = Runbook.from_yaml('runbooks/basic_test.yaml')
queries = ...  # Load your queries

# Compute groundtruth
groundtruths = compute_runbook_groundtruth(
    dataset=dataset,
    runbook=runbook.entries,
    queries=queries,
    k=10,
    metric='euclidean',
    output_dir='results/gt/',
    verbose=True
)

# Access results
for step, gt in groundtruths.items():
    print(f"Step {step}: {gt['num_active_points']} points")
    neighbor_tags = gt['tags']  # (nq, k) array
    distances = gt['distances']  # (nq, k) array
```

## Results

Test results are saved as JSON files containing:

- Algorithm and dataset configuration
- Total execution time
- Operation counts
- Latency statistics (mean, std, percentiles)
- Throughput measurements
- Queue metrics

Example output:

```json
{
  "name": "faiss_hnsw_congestion",
  "total_time": 45.23,
  "operation_counts": {
    "initial": 1,
    "batch_insert": 2,
    "search": 3
  },
  "insert_stats": {
    "mean": 1234.56,
    "p95": 2345.67,
    "p99": 3456.78
  }
}
```

## Extending the Framework

### Adding a New Algorithm

1. Create a new directory under `algorithms/`
2. Implement `BaseStreamingANN` for basic functionality
3. Wrap with `CongestionANN` for multi-worker support
4. Register in `algorithms/__init__.py`

Example:

```python
from benchmark_anns.core import BaseStreamingANN, CongestionANN

class MyAlgorithm(BaseStreamingANN):
    def setup(self, dtype, max_pts, ndims):
        # Initialize your index
        pass
    
    def insert(self, X, ids):
        # Insert vectors
        pass
    
    def delete(self, ids):
        # Delete vectors
        pass
    
    def query(self, X, k):
        # Query neighbors
        pass

class MyAlgorithmCongestion(CongestionANN):
    def __init__(self, metric, index_params, parallel_workers=1):
        algos = [MyAlgorithm(metric, index_params) for _ in range(parallel_workers)]
        super().__init__(algos, metric, index_params, parallel_workers)
```

## License

This project is part of the SAGE-DB-Bench / big-ann-benchmarks repository.

## Citation

If you use this benchmark in your research, please cite the original neurips23 congestion track.
