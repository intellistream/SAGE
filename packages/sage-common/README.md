# SAGE Common

> Core utilities and shared components for the SAGE framework

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)

## 📋 Overview

**SAGE Common** provides essential shared utilities and components used across all SAGE packages. This is the foundation layer that provides:

- **Configuration management** for YAML/TOML files
- **Logging framework** with custom formatters and handlers
- **Network utilities** for TCP/UDP communication
- **Serialization tools** with dill and pickle support
- **System utilities** for environment and process management
- **Embedding services** (sage_embedding, sage_vllm)

This package ensures consistency and reduces code duplication across the SAGE ecosystem.

## ✨ Key Features

- **Unified Configuration**: YAML/TOML configuration loading and validation
- **Advanced Logging**: Colored output, structured logging, and custom formatters
- **Network Utilities**: TCP client/server, network helpers
- **Flexible Serialization**: Multiple backends (dill, pickle, JSON)
- **System Management**: Environment detection, process control
- **LLM Integration**: Embedding and VLLM services

## Core Modules

- **utils.config**: Configuration management utilities
- **utils.logging**: Logging framework and formatters  
- **utils.network**: Network utilities and TCP clients/servers
- **utils.serialization**: Serialization utilities including dill support
- **utils.system**: System utilities for environment and process management
- **_version**: Version management

## 📦 Package Structure

```
sage-common/
├── src/
│   └── sage/
│       └── common/
│           ├── __init__.py
│           ├── _version.py
│           ├── utils/                  # Core utilities
│           │   ├── config/            # Configuration management
│           │   ├── logging/           # Logging framework
│           │   ├── network/           # Network utilities
│           │   ├── serialization/     # Serialization tools
│           │   └── system/            # System utilities
│           └── components/            # Shared components
│               ├── sage_embedding/    # Embedding service
│               └── sage_vllm/         # VLLM service
├── tests/
├── pyproject.toml
└── README.md
```

## 🚀 Installation

### Basic Installation

```bash
pip install sage-common
```

### Development Installation

```bash
cd packages/sage-common
pip install -e .
```

### With Optional Dependencies

```bash
# With embedding support
pip install sage-common[embedding]

# With VLLM support
pip install sage-common[vllm]

# Full installation
pip install sage-common[all]
```

## 📖 Quick Start

### Configuration Management

```python
from sage.common.utils.config.loader import ConfigLoader

# Load configuration
config = ConfigLoader("config.yaml")

# Access configuration
model_name = config.get("model.name", default="default-model")
```

### Logging

```python
from sage.common.utils.logging.custom_logger import get_logger

# Get logger
logger = get_logger(__name__)

# Use logger
logger.info("Application started")
logger.debug("Debug information")
logger.error("Error occurred", exc_info=True)
```

### Network Utilities

```python
from sage.common.utils.network import TCPClient, TCPServer

# Create TCP server
server = TCPServer(host="localhost", port=8080)
server.start()

# Create TCP client
client = TCPClient(host="localhost", port=8080)
client.connect()
client.send(b"Hello, Server!")
```

### Serialization

```python
from sage.common.utils.serialization import serialize, deserialize

# Serialize data
data = {"key": "value", "numbers": [1, 2, 3]}
serialized = serialize(data, format="dill")

# Deserialize data
restored = deserialize(serialized, format="dill")
```

## 🔧 Configuration

Configuration files are typically in YAML or TOML format:

```yaml
# config.yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

network:
  host: localhost
  port: 8080
  timeout: 30

embedding:
  model: sentence-transformers/all-MiniLM-L6-v2
  device: cuda
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run with coverage
pytest --cov=sage.common --cov-report=html
```

## 📚 Documentation

- **User Guide**: See [docs-public](https://intellistream.github.io/SAGE-Pub/guides/packages/sage-common/)
- **API Reference**: See package docstrings and type hints
- **Examples**: See `examples/` directory in each module

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## 🔗 Related Packages

- **sage-kernel**: Uses common utilities for runtime management
- **sage-libs**: Builds on common components for libraries
- **sage-middleware**: Uses network and serialization utilities
- **sage-tools**: Uses configuration and logging utilities

## 📮 Support

- **Documentation**: https://intellistream.github.io/SAGE-Pub/
- **Issues**: https://github.com/intellistream/SAGE/issues
- **Discussions**: https://github.com/intellistream/SAGE/discussions

---

**Part of the SAGE Framework** | [Main Repository](https://github.com/intellistream/SAGE)
