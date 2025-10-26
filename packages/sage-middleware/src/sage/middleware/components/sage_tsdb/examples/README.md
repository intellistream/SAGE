# SageTSDB Examples

This directory contains examples demonstrating various features of SageTSDB.

## Examples

### 1. Basic Usage (`basic_usage.py`)

Demonstrates fundamental operations:

- Creating a time series database
- Adding individual and batch data points
- Querying with time ranges and tags
- Window-based aggregations

```bash
python basic_usage.py
```

### 2. Stream Join (`stream_join_demo.py`)

Shows out-of-order stream join capabilities:

- Generating streams with out-of-order data
- Configuring join parameters (window size, max delay)
- Performing window-based joins
- Analyzing join results and statistics

```bash
python stream_join_demo.py
```

### 3. Service Integration (`service_demo.py`)

Illustrates using SageTSDB through the service interface:

- Creating and configuring service instances
- Service-based data operations
- Window aggregation through service API
- Stream join via service interface

```bash
python service_demo.py
```

## Running Examples

Make sure you have SageTSDB installed:

```bash
# From the SAGE root directory
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb
```

Then run any example:

```bash
python examples/basic_usage.py
python examples/stream_join_demo.py
python examples/service_demo.py
```

## Key Concepts Demonstrated

- **Time Series Storage**: Efficient storage with timestamp-based indexing
- **Out-of-Order Handling**: Automatic handling of late-arriving data
- **Window Operations**: Tumbling, sliding, and session windows
- **Stream Joins**: Window-based joins with configurable parameters
- **Service Integration**: Microservice-style API for SAGE workflows

## Next Steps

After running these examples, check out:

- [SageTSDB README](../README.md) for comprehensive documentation
- [Algorithm Guide](../docs/algorithms_guide.md) for implementing custom algorithms
- SAGE workflow integration examples in the main examples directory
