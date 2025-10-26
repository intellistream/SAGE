# SAGE CLI

> **Unified Command Line Interface for SAGE Platform**

SAGE CLI (`sage-cli`) is the unified command-line interface for the SAGE (Streaming-Augmented Generative Execution) platform. It provides a comprehensive set of commands for managing clusters, deploying applications, and developing with SAGE.

## 🚀 Installation

```bash
# From source
cd packages/sage-cli
pip install -e .

# Or install from PyPI (when published)
pip install sage-cli
```

## 📋 Command Structure

SAGE CLI organizes commands into three main categories:

### Platform Commands

Manage SAGE infrastructure and system components:

- `sage cluster` - Ray cluster management
- `sage head` - Head node management
- `sage worker` - Worker node management
- `sage job` - Job management
- `sage jobmanager` - JobManager service
- `sage config` - Configuration management
- `sage doctor` - System diagnostics
- `sage version` - Version information
- `sage extensions` - C++ extension management

### Application Commands

Application-level functionality:

- `sage llm` - LLM service management
- `sage chat` - Interactive chat interface
- `sage embedding` - Embedding service management
- `sage pipeline` - Pipeline builder
- `sage studio` - Visual pipeline editor

### Development Commands

Tools for SAGE developers:

- `sage dev quality` - Code quality checks
- `sage dev project` - Project management
- `sage dev maintain` - Maintenance tools
- `sage dev package` - Package management
- `sage dev resource` - Resource management
- `sage dev github` - GitHub utilities

## 🔧 Quick Start

```bash
# Check system status
sage doctor

# Start a cluster
sage cluster start

# View cluster status
sage cluster status

# Run development checks
sage dev quality check

# Get help
sage --help
sage <command> --help
```

## 📚 Documentation

For detailed documentation, see:
- [SAGE Documentation](https://intellistream.github.io/SAGE)
- [CLI Package Plan](../../docs/dev-notes/architecture/SAGE_CLI_PACKAGE_PLAN.md)

## 🏗️ Architecture

SAGE CLI is part of the L6 (Interface Layer) in the SAGE architecture:

```
L1: sage-common          (Foundation)
L2: sage-platform        (Platform Core)
L3: sage-kernel, sage-libs
L4: sage-middleware
L5: sage-apps, sage-benchmark
L6: sage-cli, sage-devtools, sage-studio  ← CLI is here
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## 📄 License

Apache License 2.0 - see [LICENSE](../../LICENSE) for details.

## 🔗 Related Packages

- `sage-devtools` - Development tools and utilities
- `sage-platform` - SAGE platform core
- `sage-apps` - SAGE applications
