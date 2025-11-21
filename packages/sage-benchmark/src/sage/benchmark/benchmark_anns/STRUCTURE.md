# Benchmark ANNS Project Structure

## Overview
This is a streamlined project extracted from the neurips23/congestion track, focusing specifically on benchmarking ANNS algorithms under congestion scenarios with streaming workloads.

## Directory Structure

```
benchmark_anns/
│
├── algorithms/                    # Algorithm implementations
│   ├── __init__.py               # Algorithm registry
│   └── faiss_hnsw/               # Faiss HNSW implementation
│       ├── __init__.py
│       ├── faiss_hnsw_streaming.py    # Streaming version
│       └── faiss_hnsw_congestion.py   # Congestion-aware wrapper
│
├── configs/                      # Configuration files
│   ├── example_runbook.yaml      # Example test sequence
│   └── faiss_hnsw_config.yaml    # Algorithm configuration
│
├── core/                         # Core framework components
│   ├── __init__.py
│   ├── base_algorithm.py         # Base algorithm interfaces
│   ├── congestion_worker.py      # Worker for concurrent operations
│   ├── congestion_algorithm.py   # Multi-worker wrapper
│   ├── runbook.py               # Runbook loader and processor
│   └── congestion_runner.py     # Test execution engine
│
├── datasets/                     # Dataset loaders
│   ├── __init__.py
│   └── simple_dataset.py         # Simple dataset wrapper
│
├── utils/                        # Utility functions
│   ├── __init__.py
│   ├── timestamp_utils.py        # Timestamp generation, latency calc
│   └── system_utils.py           # CPU binding, system utilities
│
├── __init__.py                   # Package initialization
├── main.py                       # Main entry point
├── test_framework.py             # Quick test script
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

## Key Components

### 1. Core Module (`core/`)

#### Base Algorithms (`base_algorithm.py`)
- **BaseANN**: Basic ANN interface with query capability
- **BaseStreamingANN**: Extends BaseANN with insert/delete operations
- **BaseCongestionANN**: Extends BaseANN with multi-worker congestion handling

#### Congestion Worker (`congestion_worker.py`)
- **CongestionWorker**: Background thread processing insert/delete/query operations
- Features:
  - Queue-based operation management
  - Congestion detection and data dropping
  - Backpressure logic
  - Thread-safe operations

#### Congestion Algorithm (`congestion_algorithm.py`)
- **CongestionANN**: Wrapper managing multiple workers
- Features:
  - Load balancing across workers
  - Round-robin insertion
  - Aggregated metrics (drops, queue lengths)

#### Runbook System (`runbook.py`)
- **Runbook**: Defines test operation sequences
- **RunbookEntry**: Single operation with parameters
- Supports YAML configuration loading

#### Runner (`congestion_runner.py`)
- **CongestionRunner**: Executes tests based on runbooks
- Collects metrics: latency, throughput, queue stats
- Handles all operation types

### 2. Algorithms Module (`algorithms/`)

Currently implements:
- **Faiss HNSW**: 
  - `FaissHNSWStreaming`: Basic streaming implementation
  - `FaissHNSWCongestion`: Multi-worker congestion-aware version

Easy to extend with new algorithms following the same pattern.

### 3. Datasets Module (`datasets/`)

- **SimpleDataset**: Loads vectors from binary files
- Supports `.fvecs`, `.bvecs`, `.ivecs` formats
- Can create synthetic data for testing

### 4. Utils Module (`utils/`)

- **timestamp_utils.py**: Timestamp generation, latency percentiles, statistics
- **system_utils.py**: CPU core binding for performance tuning

## Operation Types

The framework supports these runbook operations:

1. **initial**: Load initial dataset
2. **startHPC**: Start background workers
3. **endHPC**: Stop background workers
4. **batch_insert**: Insert data in timed batches
5. **insert**: Single insert operation
6. **delete**: Delete vectors by ID range
7. **search**: Query k nearest neighbors
8. **waitPending**: Wait for queue to drain
9. **enableScenario**: Enable test scenarios (random drop, contamination, etc.)

## Congestion Features

### Queue Management
- Separate queues for insert/delete operations
- Configurable queue capacity
- Tracks queue lengths over time

### Drop Handling
- Automatic dropping when queues are full
- Random drop simulation
- Drop count tracking

### Backpressure Logic
- Queue capacity-based: Drop when queue is full
- Empty-only: Drop when queue is not empty
- Configurable per worker

### Performance Metrics
- Insert/delete/query latencies (mean, std, percentiles)
- Throughput measurements
- Continuous query performance during ingestion
- Queue lengths and drop counts
- Operation counts

## Usage Flow

1. **Configuration**: Define algorithm, dataset, and test parameters in YAML
2. **Runbook**: Specify operation sequence for the test
3. **Execution**: Run via `main.py` or programmatically
4. **Results**: JSON output with comprehensive metrics

## Differences from Original Project

### Simplified
- Removed tracks: streaming, sparse, filter, ood (kept only congestion)
- Single algorithm focus (faiss_hnsw as example)
- Minimal external dependencies
- Cleaner directory structure

### Retained
- Complete congestion testing logic
- Multi-worker architecture
- Queue-based congestion handling
- Runbook system
- All performance metrics
- Drop/backpressure logic

### Improved
- Better code organization
- Clear module separation
- Comprehensive documentation
- Easy to extend with new algorithms
- Standalone project structure

## Extension Points

### Adding New Algorithms

1. Implement `BaseStreamingANN`:
```python
class MyAlgo(BaseStreamingANN):
    def setup(self, dtype, max_pts, ndims): ...
    def insert(self, X, ids): ...
    def delete(self, ids): ...
    def query(self, X, k): ...
```

2. Wrap with `CongestionANN`:
```python
class MyAlgoCongestion(CongestionANN):
    def __init__(self, metric, index_params, parallel_workers=1):
        algos = [MyAlgo(metric, index_params) for _ in range(parallel_workers)]
        super().__init__(algos, metric, index_params, parallel_workers)
```

### Adding New Datasets

Extend `SimpleDataset` or create new loader following the same interface.

### Adding New Operations

Add handling in `CongestionRunner._execute_*()` methods.

## Testing

Run the quick test:
```bash
python test_framework.py
```

Run with configuration:
```bash
python main.py --config configs/faiss_hnsw_config.yaml
```

## Dependencies

- **Required**: numpy, pyyaml, pandas
- **Optional**: PyCANDYAlgo (for Faiss HNSW)

See `requirements.txt` for details.
