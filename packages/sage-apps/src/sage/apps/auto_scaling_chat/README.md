# Auto-Scaling Chat System

An intelligent auto-scaling chat system built on SAGE framework demonstrating elastic resource
management and load balancing capabilities.

## Features

- **Simulated User Traffic**: Variable load patterns (ramp up, peak, ramp down)
- **Automatic Scaling**: Dynamic server scaling based on load thresholds
- **Load Balancing**: Round-robin distribution across available servers
- **Resource Monitoring**: Real-time metrics and performance tracking
- **SAGE Integration**: Built with BatchFunction, MapFunction, SinkFunction
- **Configurable Policies**: Customizable scaling thresholds and limits

## Quick Start

```python
from sage.apps.auto_scaling_chat import run_auto_scaling_demo

# Run default simulation
run_auto_scaling_demo()

# Custom load profile
run_auto_scaling_demo(
    duration=60,        # seconds
    base_rate=5,        # min concurrent users
    peak_rate=80,       # max concurrent users
    verbose=True        # show scaling events
)
```

## Command Line Usage

```bash
# Default simulation (30s)
python -m sage.apps.auto_scaling_chat.pipeline

# Custom parameters
python -m sage.apps.auto_scaling_chat.pipeline \
    --duration 60 \
    --base-rate 10 \
    --peak-rate 80 \
    --verbose

# Quick test
python -m sage.apps.auto_scaling_chat.pipeline --duration 15 --peak-rate 40
```

## Pipeline Architecture

The system uses SAGE stream processing operators:

```
UserTrafficSource (BatchFunction)
    ↓
AutoScaler (MapFunction)
    ↓
LoadBalancer (MapFunction)
    ↓
RequestProcessor (MapFunction)
    ↓
MetricsCollector (SinkFunction)
    ↓
ScalingEventsSink (SinkFunction) [optional]
```

### Operators

- **UserTrafficSource**: Generates simulated user requests with varying load patterns
- **AutoScaler**: Makes scaling decisions based on load/server ratio
- **LoadBalancer**: Distributes requests across available servers (round-robin)
- **RequestProcessor**: Simulates request processing on servers
- **MetricsCollector**: Collects and displays performance metrics
- **ScalingEventsSink**: Logs all scaling events for analysis

## Scaling Policy

Default thresholds:

- **Scale UP**: When average load per server > 30 users
- **Scale DOWN**: When average load per server < 10 users
- **Min servers**: 2
- **Max servers**: 10
- **Cooldown**: 5 seconds between scaling actions

## Example Output

```
⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡
          SAGE Auto-Scaling Chat System Demo
⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡

======================================================================
📋 Configuration
======================================================================
   Simulation duration: 30s
   Base load: 5 concurrent users
   Peak load: 50 concurrent users
   Verbose logging: True
======================================================================

🚀 Starting auto-scaling simulation...

⚠️ Scaling Threshold Reached! Load: 35, Scaling up to 3 servers
📊 Load:  20 users | Servers:  2 | Requests:   10
📊 Load:  35 users | Servers:  3 | Requests:   20
⚠️ Scaling Threshold Reached! Load: 48, Scaling up to 4 servers
📊 Load:  50 users | Servers:  4 | Requests:   30

======================================================================
📊 Auto-Scaling System Metrics
======================================================================
   Total requests processed: 245
   Total duration: 30.15s
   Average throughput: 8.13 req/s
   Peak load: 50 concurrent users
   Peak servers: 4
   Scaling events: 5
   Average load: 28.3 users
   Average servers: 3.2
======================================================================

🔄 Scaling Events:
   1. 📈 SCALE_UP: 3 servers (load: 35)
   2. 📈 SCALE_UP: 4 servers (load: 48)
   3. 📉 SCALE_DOWN: 3 servers (load: 18)
   4. 📉 SCALE_DOWN: 2 servers (load: 8)
```

## Use Cases

- **Cloud Applications**: Elastic scaling for web applications
- **Chat Systems**: Handle variable user loads efficiently
- **API Gateways**: Auto-scale based on request rates
- **Gaming Servers**: Match-making and lobby systems
- **Streaming Services**: Handle peak viewing times

## Configuration Options

Customize scaling behavior:

```python
from sage.apps.auto_scaling_chat.operators import AutoScaler

# Custom scaler with different thresholds
scaler = AutoScaler(
    scale_up_threshold=25,    # Scale up earlier
    scale_down_threshold=5,   # Scale down more aggressively
    min_servers=1,            # Allow single server
    max_servers=20,           # Allow more servers
)
```

## Testing

Run the example script:

```bash
python examples/apps/run_auto_scaling_chat.py
```

Or run tests:

```bash
python -m pytest packages/sage-apps/tests/auto_scaling_chat/ -v
```

## Performance Metrics

The system tracks:

- Total requests processed
- Average throughput (requests/second)
- Peak concurrent load
- Server utilization
- Scaling event frequency
- Average response time

## Dependencies

- Python 3.8+
- SAGE framework (sage-common, sage-kernel)
- Standard library only

## Future Enhancements

- Integration with real cloud providers (AWS, GCP, Azure)
- Predictive scaling using machine learning
- Cost optimization algorithms
- Multi-region deployment
- Advanced load balancing (weighted, least-connections)
- Health checks and failure recovery
- Integration with monitoring systems (Prometheus, Grafana)
