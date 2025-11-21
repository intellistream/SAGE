# Runbooks - Test Scenarios

This directory contains runbook files that define different test scenarios and workloads for benchmarking ANNS algorithms.

## What is a Runbook?

A **runbook** defines a sequence of operations (initial load, insert, delete, search, etc.) that simulate a specific workload scenario. Runbooks are independent of algorithm configurations, making them reusable across different algorithms.

## Available Runbooks

### 1. basic_test.yaml
**Purpose**: Standard test with balanced operations  
**Characteristics**:
- Initial load: 10K vectors
- Two batch inserts: 40K + 10K vectors
- Multiple search operations
- Single delete operation (1K vectors)
- Event rate: 2000-1500 events/sec

**Use case**: General performance evaluation, regression testing

### 2. light_workload.yaml
**Purpose**: Quick testing and development  
**Characteristics**:
- Initial load: 5K vectors
- Single insert: 10K vectors
- Minimal searches
- Event rate: 1000 events/sec

**Use case**: Fast iteration during development, CI/CD tests

### 3. heavy_workload.yaml
**Purpose**: Stress test with large data volumes  
**Characteristics**:
- Initial load: 50K vectors
- Multiple large inserts: 300K total vectors
- Heavy deletion: 20K vectors
- Multiple search phases
- Event rate: 3000-5000 events/sec

**Use case**: Performance limits testing, capacity planning

### 4. congestion_stress.yaml
**Purpose**: Test congestion handling and drop logic  
**Characteristics**:
- Enables random drop (5% probability)
- High event rate: 10K events/sec
- Large batches to trigger queue congestion
- Tests recovery after congestion

**Use case**: Evaluating robustness under overload, queue management testing

### 5. query_intensive.yaml
**Purpose**: Focus on search performance  
**Characteristics**:
- Large initial load: 100K vectors
- Many search operations (15+ queries)
- Minimal inserts during search phase
- Low event rate: 1000 events/sec

**Use case**: Query latency optimization, search throughput testing

## Runbook Structure

Each runbook is a YAML file with a list of operations:

```yaml
# Operation 1
- operation: initial
  start: 0
  end: 10000
  description: "Load initial data"

# Operation 2
- operation: startHPC
  description: "Start workers"

# Operation 3
- operation: batch_insert
  start: 10000
  end: 50000
  batchSize: 1000
  eventRate: 2000
  description: "Insert data in batches"

# ... more operations
```

## Operation Types

- **initial**: Load initial dataset before streaming
- **startHPC**: Start background worker threads
- **endHPC**: Stop background worker threads
- **batch_insert**: Insert data in batches with timing control
- **insert**: Single insert operation
- **delete**: Delete vectors by ID range
- **search**: Perform k-NN search queries
- **waitPending**: Wait for all pending operations to complete
- **enableScenario**: Enable special test scenarios (drop, contamination, etc.)

## Creating Custom Runbooks

1. **Start from template**: Copy an existing runbook
2. **Define your scenario**: Think about what you want to test
3. **Adjust parameters**:
   - Data volumes (start/end)
   - Batch sizes
   - Event rates (controls timing)
   - Number of operations
4. **Add descriptions**: Help others understand your test
5. **Save to runbooks/**: Name it clearly (e.g., `my_scenario.yaml`)

### Example: Custom Runbook

```yaml
# custom_scenario.yaml
# Testing incremental updates with frequent queries

- operation: initial
  start: 0
  end: 20000

- operation: startHPC

# Simulate continuous updates
- operation: batch_insert
  start: 20000
  end: 30000
  batchSize: 100
  eventRate: 500

- operation: search
  k: 10

- operation: batch_insert
  start: 30000
  end: 40000
  batchSize: 100
  eventRate: 500

- operation: search
  k: 10

# Continue pattern...

- operation: waitPending
- operation: endHPC
```

## Using Runbooks

### In Configuration File

```yaml
# configs/my_config.yaml
algorithm:
  name: "faiss_hnsw"
  # ... algorithm params

dataset:
  name: "sift"
  # ... dataset params

runbook:
  file: "runbooks/light_workload.yaml"  # Choose runbook
```

### Command Line Override

```bash
# Use default runbook from config
python main.py --config configs/faiss_hnsw_config.yaml

# Override with different runbook
python main.py --config configs/faiss_hnsw_config.yaml --runbook runbooks/heavy_workload.yaml
```

## Runbook Comparison Matrix

| Runbook | Vectors | Inserts | Deletes | Queries | Event Rate | Duration | Use Case |
|---------|---------|---------|---------|---------|------------|----------|----------|
| light_workload | 15K | 1 phase | 0 | 2 | Low | Short | Development |
| basic_test | 60K | 2 phases | 1K | 3+ | Medium | Medium | Standard test |
| heavy_workload | 300K | 3 phases | 20K | 5+ | High | Long | Stress test |
| congestion_stress | 120K | 2 phases | 0 | 3 | Very High | Medium | Drop testing |
| query_intensive | 110K | 2 phases | 0 | 15+ | Low | Medium | Query perf |

## Best Practices

1. **Descriptive names**: Use clear, intention-revealing names
2. **Add descriptions**: Document each operation's purpose
3. **Start small**: Test with light workload first
4. **Gradual scaling**: Increase load progressively
5. **Realistic scenarios**: Model real-world use cases
6. **Version control**: Keep runbooks in git
7. **Share and reuse**: One runbook for multiple algorithms

## Tips

- **Event rate** controls timing: higher = faster, more congestion
- **Batch size** affects queue behavior: larger = more bursty
- **waitPending** helps stabilize between phases
- Use **enableScenario** to test special conditions
- Chain operations to test state transitions

## Contributing

When adding new runbooks:
1. Document the purpose and characteristics
2. Update this README
3. Test with at least one algorithm
4. Consider edge cases (empty dataset, etc.)
