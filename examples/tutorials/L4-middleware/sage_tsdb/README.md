# SAGE TSDB Tutorial Examples

This directory contains comprehensive examples demonstrating SAGE TSDB integration with SAGE DAG
workflows.

## Examples Overview

### 1. Basic DAG Example (`basic_dag_example.py`)

Demonstrates fundamental SAGE TSDB operations in a DAG pipeline:

- **Time series data ingestion** through SAGE pipeline
- **Real-time querying** with sliding windows
- **Window-based aggregation** (tumbling windows)
- **Service integration** for simplified API access

```bash
python basic_dag_example.py
```

**Key Features:**

- `TimeSeriesDataSource`: Generate simulated sensor data
- `TSDBIngestNode`: Ingest data into TSDB
- `TSDBQueryNode`: Query and compute statistics
- `TSDBWindowAggregateNode`: Perform window aggregations
- `ResultPrinterSink`: Display results

### 2. Stream Join DAG Example (`stream_join_dag_example.py`)

Demonstrates out-of-order stream join capabilities:

- **Out-of-order data handling** with watermarking
- **Window-based stream join** between two data streams
- **Join statistics** and performance monitoring
- **DAG integration** for stream processing

```bash
python stream_join_dag_example.py
```

**Key Features:**

- `OutOfOrderStreamSource`: Generate streams with simulated delays
- `StreamJoinNode`: Join two streams with configurable windows
- `JoinResultSink`: Display join results and statistics
- Configurable disorder probability and max delay

### 3. Advanced DAG Example (`advanced_dag_example.py`)

Demonstrates advanced analytics and real-time processing:

- **Multi-sensor data processing**
- **Real-time anomaly detection** using statistical methods
- **Complex window aggregations** (multiple aggregation types)
- **Service-based analytics**

```bash
python advanced_dag_example.py
```

**Key Features:**

- `MultiSensorSource`: Generate data from multiple sensors
- `AnomalyDetector`: Detect anomalies using z-score
- `AggregationNode`: Apply multiple aggregation strategies
- `AnalyticsSink`: Display analytics and anomaly alerts

## Running the Examples

### Prerequisites

Ensure SAGE TSDB is installed (via quickstart or editable install):

```bash
# From SAGE root directory
./quickstart.sh --dev --yes   # or install middleware in editable mode
# pip install -e packages/sage-middleware
```

### Run Individual Examples

```bash
# From SAGE root directory
cd examples/tutorials/sage_tsdb

# Basic example
python basic_dag_example.py

# Stream join example
python stream_join_dag_example.py

# Advanced example
python advanced_dag_example.py
```

### Run All Examples

```bash
# Run all examples in sequence
for example in basic_dag_example.py stream_join_dag_example.py advanced_dag_example.py; do
    echo "Running $example..."
    python $example
    echo ""
done
```

## Example Architecture

### Basic Pipeline Flow

```
DataSource → IngestNode → QueryNode → AggregateNode → Sink
```

### Stream Join Flow

```
LeftStream ──┐
             ├─→ JoinNode → Sink
RightStream ─┘
```

### Advanced Analytics Flow

```
MultiSensorSource → Ingest → AnomalyDetector → Aggregation → AnalyticsSink
```

## Key Concepts Demonstrated

### 1. Time Series Data Management

- Efficient storage with timestamp-based indexing
- Tag-based filtering for multi-dimensional queries
- Window-based aggregations

### 2. Out-of-Order Processing

- Watermarking for late data handling
- Buffer management for stream join
- Configurable delay tolerance

### 3. DAG Integration

- Node-based data transformation
- Pipeline composition
- Source-to-sink data flow

### 4. Real-Time Analytics

- Anomaly detection using statistical methods
- Multi-window aggregations
- Performance monitoring and statistics

## Configuration Options

### TSDB Configuration

```python
from sage.middleware.components.sage_tsdb import SageTSDBServiceConfig

config = SageTSDBServiceConfig(
    enable_compression=False,
    max_memory_mb=1024,
    default_window_size=60000,  # 60 seconds
    default_aggregation="avg",
)
```

### Stream Join Configuration

```python
join_config = {
    "window_size": 5000,  # 5-second join window
    "max_delay": 3000,  # 3-second max delay
    "join_key": "sensor_id",  # Optional equi-join key
}
```

### Window Aggregation Configuration

```python
window_config = {
    "window_type": "tumbling",  # tumbling/sliding/session
    "window_size": 10000,  # 10 seconds
    "aggregation": "avg",  # sum/avg/min/max/count/stddev
}
```

## Performance Considerations

### Ingestion

- Use batch operations for higher throughput
- Balance between latency and batch size
- Consider memory limits for large datasets

### Queries

- Use tag filtering to reduce search space
- Limit result size for large time ranges
- Cache frequently accessed data

### Stream Join

- Adjust window size based on data arrival patterns
- Configure max_delay to match expected out-of-order delays
- Monitor buffer sizes to prevent memory issues

## Troubleshooting

### Issue: Module not found

```bash
# Ensure SAGE is in Python path
export PYTHONPATH=/home/shuhao/SAGE:$PYTHONPATH

# Or install SAGE in development mode
cd /home/shuhao/SAGE
pip install -e .
```

### Issue: C++ library not found

```bash
# Build sageTSDB C++ core
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
./build.sh
```

### Issue: Out of memory

- Reduce batch sizes
- Decrease window sizes
- Increase max_delay to allow earlier data release

## Next Steps

After exploring these examples:

1. **Customize Data Sources**: Adapt to your data format and sources
1. **Add Custom Algorithms**: Implement domain-specific processing
1. **Integrate with Other Components**: Combine with sage_db, sage_flow, etc.
1. **Deploy in Production**: Scale to handle real workloads

## Related Documentation

- [SAGE TSDB README](../../../packages/sage-middleware/src/sage/middleware/components/sage_tsdb/README.md)
- [Submodule Setup Guide](../../../packages/sage-middleware/src/sage/middleware/components/sage_tsdb/SUBMODULE_SETUP.md)
- [sage-developer Guide](../../../DEVELOPER.md)

## Support

For issues or questions:

- GitHub Issues: https://github.com/intellistream/SAGE/issues
- Email: shuhao_zhang@hust.edu.cn

______________________________________________________________________

**Happy coding with SAGE TSDB! 🚀**
