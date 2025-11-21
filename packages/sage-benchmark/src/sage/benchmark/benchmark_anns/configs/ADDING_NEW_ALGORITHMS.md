# Adding New Algorithms

This guide explains how to add new algorithms to the benchmark framework.

## Quick Start

The framework uses **dynamic imports**, so you don't need to modify `run.py` to add new algorithms. Just:

1. Implement your algorithm class
2. Create a config file
3. Run the benchmark

## Algorithm Implementation

### 1. Create Algorithm Module

Create your algorithm in `benchmark_anns/algorithms/your_algorithm/`:

```
benchmark_anns/algorithms/
└── your_algorithm/
    ├── __init__.py
    └── your_algorithm_congestion.py
```

### 2. Implement Algorithm Class

Your algorithm class should follow this pattern:

```python
# benchmark_anns/algorithms/your_algorithm/your_algorithm_congestion.py

from benchmark_anns.core import CongestionAlgorithm

class YourAlgorithmCongestion(CongestionAlgorithm):
    """Your algorithm implementation for congestion track"""
    
    def __init__(self, metric='euclidean', index_params=None, parallel_workers=1):
        """
        Initialize algorithm.
        
        Args:
            metric: Distance metric ('euclidean', 'angular', etc.)
            index_params: Dict of algorithm-specific parameters
            parallel_workers: Number of parallel workers
        """
        super().__init__(metric=metric)
        self.index_params = index_params or {}
        self.parallel_workers = parallel_workers
        self.name = "your_algorithm_congestion"
        # Initialize your index here
        self.index = None
    
    def fit(self, X):
        """Build index from training data"""
        # Implement index construction
        pass
    
    def insert(self, X, tags):
        """Insert vectors with tags"""
        # Implement insertion
        pass
    
    def delete(self, tags):
        """Delete vectors by tags"""
        # Implement deletion
        pass
    
    def search(self, queries, k):
        """Search for k nearest neighbors"""
        # Implement search
        # Should return: (tags, distances)
        pass
    
    def set_query_arguments(self, query_args):
        """Update query parameters"""
        # Implement parameter updates
        pass
```

### 3. Export in `__init__.py`

```python
# benchmark_anns/algorithms/your_algorithm/__init__.py

from .your_algorithm_congestion import YourAlgorithmCongestion

__all__ = ['YourAlgorithmCongestion']
```

## Configuration File

Create a config file in `benchmark_anns/configs/`:

```yaml
# configs/your_algorithm_config.yaml

algorithm:
  # Algorithm name (required)
  name: "your_algorithm"
  
  # Module path (optional - auto-inferred if not provided)
  # If not specified, will try: benchmark_anns.algorithms.{name}
  module: "benchmark_anns.algorithms.your_algorithm"
  
  # Class name (optional - auto-inferred if not provided)
  # If not specified, will convert name to CamelCase + "Congestion"
  # e.g., "your_algorithm" -> "YourAlgorithmCongestion"
  class: "YourAlgorithmCongestion"
  
  # Distance metric
  metric: "euclidean"
  
  # Algorithm-specific parameters
  index_params:
    param1: value1
    param2: value2
  
  # Parallel workers for congestion handling
  parallel_workers: 1
  
  # Query parameters
  query_params:
    search_param1: value1
    search_param2: value2

# Dataset configuration
dataset:
  name: "sift"
  data_path: "data/sift"
  dtype: "float32"

# Test configuration
test:
  k: 10
  max_pts: 100000

# Runbook
runbook:
  file: "runbooks/basic_test.yaml"
```

## Auto-Inference Examples

The framework can auto-infer module and class names:

### Example 1: Minimal Config (Auto-inference)

```yaml
algorithm:
  name: "faiss_hnsw"
  metric: "euclidean"
  index_params:
    indexkey: "HNSW32"
```

Auto-inferred:
- `module` → `benchmark_anns.algorithms.faiss_hnsw`
- `class` → `FaissHnswCongestion`

### Example 2: Custom Module Path

```yaml
algorithm:
  name: "my_custom_algo"
  module: "my_package.algorithms.custom"
  # class auto-inferred as "MyCustomAlgoCongestion"
  metric: "euclidean"
```

### Example 3: Fully Specified

```yaml
algorithm:
  name: "hnswlib"
  module: "benchmark_anns.algorithms.hnswlib"
  class: "HNSWLibCongestion"
  metric: "euclidean"
```

## Constructor Signature Compatibility

The framework tries multiple constructor signatures:

```python
# Try 1: Full signature
AlgoClass(metric=metric, index_params=params, parallel_workers=workers)

# Try 2: Without parallel_workers
AlgoClass(metric=metric, index_params=params)

# Try 3: Minimal
AlgoClass(metric=metric)
```

So your algorithm can have any of these signatures:

```python
# Option 1: Full
def __init__(self, metric='euclidean', index_params=None, parallel_workers=1):
    pass

# Option 2: Without parallel workers
def __init__(self, metric='euclidean', index_params=None):
    pass

# Option 3: Minimal
def __init__(self, metric='euclidean'):
    pass
```

## Running Your Algorithm

Once implemented:

```bash
# Run benchmark
python benchmark_anns/run.py \
    --track congestion \
    --config configs/your_algorithm_config.yaml

# Compute groundtruth
python benchmark_anns/run.py \
    --track groundtruth \
    --config configs/your_algorithm_config.yaml
```

## Parameter Sweep

Test multiple query parameter configurations:

```yaml
algorithm:
  name: "your_algorithm"
  metric: "euclidean"
  index_params:
    build_param: 100
  
  # List of query configurations
  query_params_list:
    - name: "low_accuracy"
      search_param: 10
    - name: "medium_accuracy"
      search_param: 50
    - name: "high_accuracy"
      search_param: 100
```

The benchmark will run once for each configuration and compare results.

## Example: Adding HNSWLib

Here's a complete example:

### 1. Implementation

```python
# benchmark_anns/algorithms/hnswlib/hnswlib_congestion.py

import hnswlib
from benchmark_anns.core import CongestionAlgorithm

class HNSWLibCongestion(CongestionAlgorithm):
    def __init__(self, metric='euclidean', index_params=None, parallel_workers=1):
        super().__init__(metric=metric)
        self.index_params = index_params or {}
        self.parallel_workers = parallel_workers
        self.name = "hnswlib_congestion"
        self.index = None
        self.dim = None
        self.max_elements = 0
    
    def fit(self, X):
        self.dim = X.shape[1]
        self.max_elements = self.index_params.get('max_elements', 100000)
        
        space = 'l2' if self.metric == 'euclidean' else 'ip'
        self.index = hnswlib.Index(space=space, dim=self.dim)
        
        M = self.index_params.get('M', 16)
        ef_construction = self.index_params.get('ef_construction', 200)
        
        self.index.init_index(
            max_elements=self.max_elements,
            M=M,
            ef_construction=ef_construction
        )
        
        self.index.add_items(X, ids=range(len(X)))
    
    def search(self, queries, k):
        ef = self.query_args.get('ef', 50)
        self.index.set_ef(ef)
        
        labels, distances = self.index.knn_query(queries, k=k)
        return labels, distances
```

### 2. Config

```yaml
# configs/hnswlib_config.yaml

algorithm:
  name: "hnswlib"
  metric: "euclidean"
  index_params:
    M: 16
    ef_construction: 200
    max_elements: 100000
  query_params:
    ef: 50

dataset:
  name: "sift"
  data_path: "data/sift"

test:
  k: 10
  max_pts: 100000

runbook:
  file: "runbooks/basic_test.yaml"
```

### 3. Run

```bash
python benchmark_anns/run.py --track congestion --config configs/hnswlib_config.yaml
```

## Troubleshooting

### Import Error

```
ImportError: Cannot import algorithm module 'benchmark_anns.algorithms.my_algo'
```

**Solution**: Check module path and ensure `__init__.py` exists.

### Class Not Found

```
AttributeError: Cannot find class 'MyAlgoCongestion' in module 'benchmark_anns.algorithms.my_algo'
```

**Solution**: 
1. Check class name spelling
2. Ensure class is imported in `__init__.py`
3. Verify class name matches config

### Constructor Error

```
TypeError: __init__() got an unexpected keyword argument 'parallel_workers'
```

**Solution**: Framework will auto-retry with simpler signatures. If still failing, check your `__init__` signature.

## See Also

- [Base Algorithm Interface](../core/base_algorithm.py)
- [Congestion Algorithm Base](../core/congestion_algorithm.py)
- [Example: Faiss HNSW](../algorithms/faiss_hnsw/)
