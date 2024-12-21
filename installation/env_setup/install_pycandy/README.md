# High Performance Streaming ANNS Engine (Working)

[![GitHub stars](https://img.shields.io/github/stars/intellistream/CANDY)](https://github.com/intellistream/CANDY/stargazers)

[//]: # ([![GitHub license]&#40;https://img.shields.io/github/license/intellistream/CANDY&#41;]&#40;https://github.com/intellistream/CANDY/blob/main/LICENSE&#41;)

## Overview

The **High Performance Streaming Approximate Nearest Neighbor Search (ANNS) Engine**, also known as **CANDY**, is a
cutting-edge, streaming-capable engine designed to perform real-time, high-performance approximate nearest neighbor
search tasks on continuously evolving data streams. The engine leverages a vector database system optimized for
streaming environments, enabling fast and efficient ANNS over dynamically changing datasets.

## Features

- **Real-Time Streaming Support**: Efficiently handles high-throughput streaming data.
- **Scalability**: Designed to scale with both data size and query load.
- **Approximate Nearest Neighbor Search**: Supports ANNS for high-dimensional data using state-of-the-art techniques.
- **GPU Acceleration**: Leverages GPU for significant performance improvements on large datasets.
- **Modular and Extensible**: Built to be extensible with additional modules for custom workflows and integrations.

## Key Use Cases

- **Dynamic Data Retrieval**: Suitable for scenarios where data changes rapidly, such as recommendation systems,
  personalized search, and real-time anomaly detection.
- **Real-Time Analytics**: Designed to serve high-velocity streaming data analysis use cases.
- **Large-Scale Applications**: Ideal for billion-scale datasets with high throughput and low latency requirements.

## Installation

You need to have Docker, NVIDIA Container Toolkit, and CUDA installed. If any of them are not installed, follow the steps below for native Ubuntu:

```bash
git clone https://github.com/intellistream/CANDY.git
cd CANDY
```

### Prerequisites

Ensure you have the following dependencies installed:

- Python 3.8+
- NVIDIA CUDA (for GPU acceleration)

[//]: # (Install required dependencies using `pip`:)

[//]: # ()

[//]: # (```bash)

[//]: # (pip install -r requirements.txt)

[//]: # (```)

## Getting Started

To get started with the Streaming ANNS Engine, use the following script:

[//]: # (```python)

[//]: # (from candy_engine import CandyEngine)

[//]: # ()

[//]: # (# Initialize the engine with streaming data)

[//]: # (engine = CandyEngine&#40;&#41;)

[//]: # ()

[//]: # (# Add vectors and query for nearest neighbors)

[//]: # (engine.add_streaming_data&#40;data_stream&#41;)

[//]: # (results = engine.query&#40;vector&#41;)

[//]: # (```)

[//]: # ()

[//]: # (For detailed examples, please refer to the [examples]&#40;examples&#41; directory.)

## Documentation

For a complete guide on how to use and integrate the engine with your applications, visit the [documentation](docs).

[//]: # (## Performance Benchmark)

[//]: # ()

[//]: # (The ANNS engine has been benchmarked for high performance on large-scale datasets. Some highlights include:)

[//]: # ()

[//]: # (- **Latency**: < 10 ms for querying 1M vectors.)

[//]: # (- **Throughput**: Can handle up to 100K queries per second with GPU acceleration.)

[//]: # (- **Streaming**: Supports real-time updates with minimal latency.)

## Contributing

We welcome contributions from the community. To contribute, follow these steps:

1. Fork the repository.
2. Create a new branch with your feature or bug fix.
3. Submit a pull request with a detailed explanation.

Please see our [contributing guide](CONTRIBUTING.md) for more information.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have any questions, feel free to reach out via
our [Slack Channel](https://join.slack.com/t/intellistream/shared_invite/zt-2qayp8bs7-v4F71ge0RkO_rn34hBDWQg) or open an
issue on GitHub.

```