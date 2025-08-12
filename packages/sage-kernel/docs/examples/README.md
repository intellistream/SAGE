# SAGE Kernel Examples

This directory contains practical examples demonstrating how to use SAGE Kernel components and APIs.

## Example Categories

### Basic Usage
- [simple-streaming.py](basic/simple-streaming.py) - Basic streaming operations
- [environment-setup.py](basic/environment-setup.py) - Setting up local and remote environments
- [data-processing.py](basic/data-processing.py) - Simple data processing pipelines

### Advanced Streaming
- [connected-streams.py](advanced/connected-streams.py) - Multi-stream processing
- [windowing-operations.py](advanced/windowing-operations.py) - Time and count-based windows
- [complex-event-processing.py](advanced/complex-event-processing.py) - Pattern detection

### Integration Examples
- [middleware-integration.py](integration/middleware-integration.py) - Using with sage-middleware
- [custom-functions.py](integration/custom-functions.py) - Custom function development
- [plugin-development.py](integration/plugin-development.py) - Creating kernel plugins

### Real-World Use Cases
- [log-processing.py](use-cases/log-processing.py) - Log analysis pipeline
- [iot-data-streaming.py](use-cases/iot-data-streaming.py) - IoT sensor data processing
- [financial-trading.py](use-cases/financial-trading.py) - Real-time trading data analysis

## Running Examples

Each example can be run independently:

```bash
cd packages/sage-kernel
python examples/basic/simple-streaming.py
```

Or using the sage CLI:

```bash
sage run examples/basic/simple-streaming.py
```

## Example Requirements

Some examples may require additional dependencies:
- `pandas` for data manipulation examples
- `numpy` for numerical computation examples
- `matplotlib` for visualization examples

Install with:
```bash
pip install isage-kernel[examples]
```

## Contributing Examples

When adding new examples:
1. Place them in the appropriate category directory
2. Include clear documentation and comments
3. Add any required dependencies to the example header
4. Update this README with the new example
