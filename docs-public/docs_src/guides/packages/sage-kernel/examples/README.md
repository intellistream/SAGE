# SAGE Kernel Examples

This directory contains practical examples demonstrating how to use SAGE Kernel components and APIs.

## Example Categories

### Basic Usage

- <!-- [simple-streaming.py](basic/simple-streaming.py) -->

简单流处理示例 - Basic streaming operations

- <!-- [environment-setup.py](basic/environment-setup.py) -->

环境设置示例 - Setting up local and remote environments

- <!-- [data-processing.py](basic/data-processing.py) -->

数据处理示例 - Simple data processing pipelines

### Advanced Streaming

- <!-- [connected-streams.py](advanced/connected-streams.py) -->

连接流示例 - Multi-stream processing

- <!-- [windowing-operations.py](advanced/windowing-operations.py) -->

窗口操作示例 - Time and count-based windows

- <!-- [complex-event-processing.py](advanced/complex-event-processing.py) -->

复杂事件处理示例 - Pattern detection

### Integration Examples

- <!-- [middleware-integration.py](integration/middleware-integration.py) -->

中间件集成示例 - Using with sage-middleware

- <!-- [custom-functions.py](integration/custom-functions.py) -->

自定义函数示例 - Custom function development

- <!-- [plugin-development.py](integration/plugin-development.py) -->

插件开发示例 - Creating kernel plugins

### Real-World Use Cases

- <!-- [log-processing.py](use-cases/log-processing.py) -->

日志处理示例 - Log analysis pipeline

- <!-- [iot-data-streaming.py](use-cases/iot-data-streaming.py) -->

IoT数据流示例 - IoT sensor data processing

- <!-- [financial-trading.py](use-cases/financial-trading.py) -->

金融交易示例 - Real-time trading data analysis

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
pip install intsage-kernel[examples]
```

## Contributing Examples

When adding new examples:

1. Place them in the appropriate category directory
1. Include clear documentation and comments
1. Add any required dependencies to the example header
1. Update this README with the new example
